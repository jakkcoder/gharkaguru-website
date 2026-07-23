from __future__ import annotations

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import create_session, get_session, normalize_phone
from app.config import CORS_ORIGINS, PULL_ON_STARTUP
from app.finalized_deals_gcs import ensure_local_finalized_deals_db, pull_finalized_deals_db
from app.finalized_deals_routes import router as finalized_deals_router
from app.parent_leads import db as parent_leads_db
from app.parent_leads.gcs_db import ensure_local_db as ensure_local_parent_leads_db, pull_db as pull_parent_leads_db
from app.parent_leads.routes import router as parent_leads_router
from app.db import (
    connect,
    dumps,
    estimate_completion,
    init_db,
    loads,
    new_enquiry_id,
    new_inquiry_id,
    new_reference_id,
    now_iso,
    row_to_dict,
)
from app.gcs_io import GcsBusyError, ensure_local_db, pull_db_from_gcs, push_db_to_gcs, upload_bytes

logger = logging.getLogger("website-api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_local_db()
    if PULL_ON_STARTUP:
        try:
            pull_db_from_gcs()
            logger.info("Pulled website.db from GCS")
        except Exception as exc:
            logger.warning("GCS pull failed, using local DB: %s", exc)
            init_db()
    else:
        init_db()
    ensure_local_finalized_deals_db()
    if PULL_ON_STARTUP:
        try:
            pull_finalized_deals_db()
            logger.info("Pulled finalized_deals.db from GCS")
        except Exception as exc:
            logger.warning("Finalized deals GCS pull failed, using local DB: %s", exc)
    ensure_local_parent_leads_db()
    parent_leads_db.init_db()
    if PULL_ON_STARTUP:
        try:
            pull_parent_leads_db()
            logger.info("Pulled parent_leads.db from GCS")
        except Exception as exc:
            logger.warning("Parent leads GCS pull failed, using local DB: %s", exc)
    yield


app = FastAPI(title="GharKaGuru Website API", lifespan=lifespan)


@app.exception_handler(StarletteHTTPException)
async def parent_leads_unauth_redirect(request: Request, exc: StarletteHTTPException):
    """Browser-friendly redirects for parent leads portal (matches standalone inbox app)."""
    if exc.status_code == 401 and request.url.path.startswith("/parent_leads"):
        detail = str(exc.detail).lower()
        if "admin" in detail:
            return RedirectResponse("/parent_leads/admin/login", status_code=303)
        return RedirectResponse("/parent_leads/login", status_code=303)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(finalized_deals_router)
app.include_router(parent_leads_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sync_to_gcs() -> None:
    try:
        push_db_to_gcs()
    except GcsBusyError as exc:
        raise HTTPException(status_code=409, detail={"error": {"code": "GCS_BUSY", "message": str(exc)}}) from exc
    except Exception as exc:
        logger.exception("Failed to sync website.db to GCS")
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "GCS_SYNC_FAILED", "message": str(exc)}},
        ) from exc


class OtpSendRequest(BaseModel):
    phone: str
    role: str = "student"


class DraftRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class InquiryRequest(BaseModel):
    tutorId: str
    contactPhone: str
    message: str | None = None


class LeadInquiryRequest(BaseModel):
    contactPhone: str
    classLevel: str
    subject: str


@app.get("/healthz")
@app.get("/api/health")
@app.get("/v1/api/health")
def health() -> dict[str, Any]:
    return {"ok": True}


@app.post("/api/auth/otp/send")
@app.post("/v1/api/auth/otp/send")
def otp_send(body: OtpSendRequest) -> dict[str, Any]:
    session = create_session(body.phone, body.role)
    sync_to_gcs()
    return {"token": session["token"], "role": session["role"]}


@app.post("/api/teacher/application/draft")
@app.post("/v1/api/teacher/application/draft")
def teacher_draft(body: DraftRequest, session: dict[str, Any] = Depends(get_session)) -> dict[str, Any]:
    phone = session["phone"]
    data = body.data or {}
    # Never persist large photo payloads in draft JSON.
    data.pop("photoDataUrl", None)
    data.pop("photo", None)
    completion = estimate_completion(data)
    ts = now_iso()

    with connect() as conn:
        existing = conn.execute(
            "SELECT reference_id, status FROM teacher_applications WHERE phone = ?",
            (phone,),
        ).fetchone()
        if existing:
            reference_id = existing["reference_id"]
            status = existing["status"] if existing["status"] != "Submitted" else "Submitted"
            if status != "Submitted":
                status = "Draft"
            conn.execute(
                """
                UPDATE teacher_applications
                SET data_json = ?, profile_completion_percent = ?, status = ?, updated_at = ?
                WHERE phone = ?
                """,
                (dumps(data), completion, status, ts, phone),
            )
        else:
            reference_id = new_reference_id()
            status = "Draft"
            conn.execute(
                """
                INSERT INTO teacher_applications
                  (reference_id, phone, status, profile_completion_percent, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (reference_id, phone, status, completion, dumps(data), ts, ts),
            )
        conn.commit()

    sync_to_gcs()
    return {
        "referenceId": reference_id,
        "status": status,
        "profileCompletionPercent": completion,
    }


@app.get("/api/teacher/application")
@app.get("/v1/api/teacher/application")
def teacher_application(session: dict[str, Any] = Depends(get_session)) -> dict[str, Any]:
    phone = session["phone"]
    with connect(read_only=True) as conn:
        row = conn.execute(
            """
            SELECT reference_id, status, profile_completion_percent
            FROM teacher_applications WHERE phone = ?
            """,
            (phone,),
        ).fetchone()
    if not row:
        return {"referenceId": None, "status": "NotStarted", "profileCompletionPercent": 0}
    return {
        "referenceId": row["reference_id"],
        "status": row["status"],
        "profileCompletionPercent": int(row["profile_completion_percent"] or 0),
    }


async def _read_upload(file: UploadFile | None) -> tuple[bytes, str, str] | None:
    if file is None:
        return None
    data = await file.read()
    if not data:
        return None
    content_type = file.content_type or "application/octet-stream"
    name = file.filename or "upload.bin"
    return data, content_type, name


@app.post("/api/teacher/register")
@app.post("/v1/api/teacher/register")
async def teacher_register(
    session: dict[str, Any] = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    fullName: str = Form(...),
    email: str = Form(""),
    gender: str = Form(""),
    dob: str = Form(""),
    location: str = Form(""),
    feeMin: str = Form("0"),
    feeMax: str = Form("0"),
    tenthPercent: str = Form("0"),
    twelfthPercent: str = Form("0"),
    degrees: str = Form("[]"),
    certifications: str = Form("[]"),
    yearsTeaching: str = Form("0"),
    subjectsTaught: str = Form("[]"),
    boards: str = Form("[]"),
    classes: str = Form("[]"),
    studentsTaught: str = Form("0"),
    bio: str = Form(""),
    teachingMode: str = Form(""),
    idDocType: str = Form(""),
    consent: str = Form("false"),
    availability: str = Form("[]"),
    photo: UploadFile | None = File(None),
    idDocs: list[UploadFile] | None = File(None),
    certFiles: list[UploadFile] | None = File(None),
) -> dict[str, Any]:
    phone = session["phone"]
    key = (idempotency_key or "").strip() or None

    with connect() as conn:
        if key:
            existing = conn.execute(
                "SELECT reference_id FROM teacher_applications WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if existing:
                return {"referenceId": existing["reference_id"]}

    profile: dict[str, Any] = {
        "fullName": fullName,
        "email": email,
        "gender": gender,
        "dob": dob,
        "location": location,
        "feeMin": feeMin,
        "feeMax": feeMax,
        "tenthPercent": tenthPercent,
        "twelfthPercent": twelfthPercent,
        "degrees": _parse_json_field(degrees),
        "certifications": _parse_json_field(certifications),
        "yearsTeaching": yearsTeaching,
        "subjectsTaught": _parse_json_field(subjectsTaught),
        "boards": _parse_json_field(boards),
        "classes": _parse_json_field(classes),
        "studentsTaught": studentsTaught,
        "bio": bio,
        "teachingMode": teachingMode,
        "idDocType": idDocType,
        "consent": consent.lower() in {"1", "true", "yes"},
        "availability": _parse_json_field(availability),
        "phone": phone,
        "role": "teacher",
    }

    uploads: dict[str, Any] = {}
    photo_data = await _read_upload(photo)
    if photo_data:
        data, content_type, name = photo_data
        uploads["photo"] = upload_bytes(
            data,
            object_name=f"teachers/{phone}/photo-{uuid.uuid4().hex}-{name}",
            content_type=content_type,
        )

    id_uris = []
    for item in idDocs or []:
        parsed = await _read_upload(item)
        if not parsed:
            continue
        data, content_type, name = parsed
        id_uris.append(
            upload_bytes(
                data,
                object_name=f"teachers/{phone}/id-{uuid.uuid4().hex}-{name}",
                content_type=content_type,
            )
        )
    if id_uris:
        uploads["idDocs"] = id_uris

    cert_uris = []
    for item in certFiles or []:
        parsed = await _read_upload(item)
        if not parsed:
            continue
        data, content_type, name = parsed
        cert_uris.append(
            upload_bytes(
                data,
                object_name=f"teachers/{phone}/cert-{uuid.uuid4().hex}-{name}",
                content_type=content_type,
            )
        )
    if cert_uris:
        uploads["certFiles"] = cert_uris

    if uploads:
        profile["uploads"] = uploads

    completion = 100
    ts = now_iso()

    with connect() as conn:
        existing = conn.execute(
            "SELECT reference_id FROM teacher_applications WHERE phone = ?",
            (phone,),
        ).fetchone()
        if existing:
            reference_id = existing["reference_id"]
            conn.execute(
                """
                UPDATE teacher_applications
                SET status = ?, profile_completion_percent = ?, data_json = ?,
                    idempotency_key = COALESCE(?, idempotency_key), updated_at = ?
                WHERE phone = ?
                """,
                ("Submitted", completion, dumps(profile), key, ts, phone),
            )
        else:
            reference_id = new_reference_id()
            conn.execute(
                """
                INSERT INTO teacher_applications
                  (reference_id, phone, status, profile_completion_percent, data_json,
                   idempotency_key, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (reference_id, phone, "Submitted", completion, dumps(profile), key, ts, ts),
            )
        conn.commit()

    sync_to_gcs()
    return {"referenceId": reference_id}


@app.post("/api/inquiry")
@app.post("/v1/api/inquiry")
def create_inquiry(body: InquiryRequest) -> dict[str, Any]:
    phone = normalize_phone(body.contactPhone)
    inquiry_id = new_inquiry_id()
    ts = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO inquiries
              (inquiry_id, kind, contact_phone, tutor_id, message, created_at)
            VALUES (?, 'tutor', ?, ?, ?, ?)
            """,
            (inquiry_id, phone, body.tutorId, body.message or "", ts),
        )
        conn.commit()
    sync_to_gcs()
    return {"inquiryId": inquiry_id}


@app.post("/api/lead-inquiry")
@app.post("/v1/api/lead-inquiry")
def create_lead_inquiry(body: LeadInquiryRequest) -> dict[str, Any]:
    phone = normalize_phone(body.contactPhone)
    inquiry_id = new_inquiry_id()
    ts = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO inquiries
              (inquiry_id, kind, contact_phone, class_level, subject, created_at)
            VALUES (?, 'lead', ?, ?, ?, ?)
            """,
            (inquiry_id, phone, body.classLevel, body.subject, ts),
        )
        # Also create a parent/student user shell so registrations show up.
        conn.execute(
            """
            INSERT INTO users (phone, role, created_at, last_login_at)
            VALUES (?, 'student', ?, ?)
            ON CONFLICT(phone) DO UPDATE SET last_login_at = excluded.last_login_at
            """,
            (phone, ts, ts),
        )
        conn.commit()
    sync_to_gcs()
    return {"inquiryId": inquiry_id}


@app.get("/api/enquiries")
@app.get("/v1/api/enquiries")
def list_enquiries(session: dict[str, Any] = Depends(get_session)) -> dict[str, Any]:
    phone = session["phone"]
    with connect(read_only=True) as conn:
        rows = conn.execute(
            """
            SELECT id, tutor_id, tutor_name, subject, message, status, created_at
            FROM enquiries
            WHERE phone = ?
            ORDER BY created_at DESC
            """,
            (phone,),
        ).fetchall()
        inquiry_rows = conn.execute(
            """
            SELECT inquiry_id, tutor_id, subject, message, created_at, kind, class_level
            FROM inquiries
            WHERE contact_phone = ?
            ORDER BY created_at DESC
            """,
            (phone,),
        ).fetchall()

    items = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "tutorId": row["tutor_id"],
                "tutorName": row["tutor_name"],
                "subject": row["subject"],
                "createdAtISO": row["created_at"],
                "status": row["status"],
                "message": row["message"] or "",
            }
        )
    for row in inquiry_rows:
        items.append(
            {
                "id": row["inquiry_id"],
                "tutorId": row["tutor_id"],
                "tutorName": row["tutor_id"] or "Lead",
                "subject": row["subject"] or row["class_level"] or "Inquiry",
                "createdAtISO": row["created_at"],
                "status": "Pending",
                "message": row["message"] or "",
            }
        )
    return {"items": items}


@app.get("/api/admin/stats")
@app.get("/v1/api/admin/stats")
def admin_stats() -> dict[str, Any]:
    with connect(read_only=True) as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        teachers = conn.execute(
            "SELECT COUNT(*) FROM teacher_applications WHERE status = 'Submitted'"
        ).fetchone()[0]
        drafts = conn.execute(
            "SELECT COUNT(*) FROM teacher_applications WHERE status = 'Draft'"
        ).fetchone()[0]
        inquiries = conn.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0]
    return {
        "users": users,
        "teacherSubmitted": teachers,
        "teacherDrafts": drafts,
        "inquiries": inquiries,
    }


def _parse_json_field(raw: str) -> Any:
    try:
        return json.loads(raw or "null")
    except json.JSONDecodeError:
        return raw
