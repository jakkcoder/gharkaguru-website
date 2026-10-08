from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import create_session, get_session, normalize_phone
from app.config import CORS_ORIGINS, PULL_ON_STARTUP
from app.finalized_deals_gcs import ensure_local_finalized_deals_db, pull_finalized_deals_db
from app.finalized_deals_routes import router as finalized_deals_router
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
from app.gold_replica import start_background_refresh
from app.gcs_io import GcsBusyError, ensure_local_db, pull_db_from_gcs, push_db_to_gcs
from app.parent_enquiries import note_website_teacher, router as parent_enquiry_router
from app.public_teachers import get_teacher, search_teachers
from app.website_tutors import append_website_tutor

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
    stop_replica = start_background_refresh()
    yield
    if stop_replica is not None:
        stop_replica.set()


app = FastAPI(title="GharKaGuru Website API", lifespan=lifespan)

app.include_router(finalized_deals_router)
app.include_router(parent_enquiry_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sync_to_gcs() -> None:
    if os.getenv("SKIP_GCS_SYNC", "").lower() in {"1", "true", "yes"}:
        return
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


@app.post("/api/teacher/register")
@app.post("/v1/api/teacher/register")
def teacher_register(
    phone: str = Form(...),
    fullName: str = Form(...),
    location: str = Form(...),
    pin: str = Form(...),
    subject: str = Form(...),
    classCanTeach: str = Form(...),
    education: str = Form(...),
    medium: str = Form(...),
    teachingMode: str = Form(...),
) -> dict[str, Any]:
    phone = normalize_phone(phone)
    answers = {
        "full_name": fullName.strip(),
        "location": location.strip(),
        "pin": pin.strip(),
        "subject": subject.strip(),
        "class_can_teach": classCanTeach.strip(),
        "education": education.strip(),
        "medium": medium.strip(),
        "teaching_mode": teachingMode.strip(),
    }
    missing = [name for name, value in answers.items() if not value]
    if missing or len(answers["pin"]) != 6 or not answers["pin"].isdigit():
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID", "message": "Fill every tutor field. PIN must be 6 digits."}},
        )
    lead = append_website_tutor(phone, answers)

    with connect() as conn:
        note_website_teacher(conn, phone, answers["full_name"])
        conn.commit()

    sync_to_gcs()
    return {"referenceId": lead["id"]}


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


@app.get("/api/tutors")
@app.get("/v1/api/tutors")
def list_public_tutors(
    location: str = "",
    subject: str = "",
    subjects: str = "",
    mode: str = "",
    ids: str = "",
    page: int = 1,
    pageSize: int = 20,
) -> dict[str, Any]:
    return search_teachers(
        location=location,
        subject=subject,
        subjects=[item.strip() for item in subjects.split(",") if item.strip()],
        mode=mode,
        ids=[item.strip() for item in ids.split(",") if item.strip()],
        page=page,
        page_size=pageSize,
    )


@app.get("/api/tutor/{tutor_id}")
@app.get("/v1/api/tutor/{tutor_id}")
def public_tutor(tutor_id: str) -> dict[str, Any]:
    teacher = get_teacher(tutor_id)
    if not teacher:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Tutor not found."}})
    return teacher


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
