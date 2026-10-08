"""Public parent enquiries, teacher interest, and contact-access payments."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_session
from app.db import connect, now_iso

POLICY_VERSION = "2026-10-01"
FIRST_FEE_RUPEES = 100
NEXT_FEE_RUPEES = 500
POLICY_TEXT = """GharKaGuru parent enquiry terms

You confirm that you are a tutor and want to be considered for this parent enquiry.

The parent phone number is shared only after the access fee is received.
The first parent number you unlock costs Rs 100.
Each later parent number costs Rs 500.
No refund is provided if the demo fails.
Once you receive your first tuition payment for a student, you must submit 25% of that first payment to GharKaGuru.

A future payment gateway will collect this fee online. Until then, GharKaGuru confirms the payment manually.
"""

router = APIRouter()


class EnquirySync(BaseModel):
    metaLeadId: str
    status: str = "open"
    parentPhone: str = ""
    parentName: str = ""
    studentName: str = ""
    classLevel: str = ""
    subject: str = ""
    board: str = ""
    medium: str = ""
    tutorMode: str = ""
    teacherPreference: str = ""
    address: str = ""
    locality: str = ""
    pin: str = ""
    budget: str = ""
    notes: str = ""
    schedule: str = ""
    convertedTeacherPhone: str = ""
    sourceRevision: str = ""


class TeacherSync(BaseModel):
    teachers: list[dict[str, Any]] = Field(default_factory=list)


class ApplyBody(BaseModel):
    isTutor: bool = False
    acceptNoRefund: bool = False
    acceptCommission: bool = False
    policyVersion: str = ""


class ManualPaymentGateway:
    """Phase-one payment boundary. A provider gateway can replace mark_paid later."""

    name = "manual"

    def prepare(self, payment_id: str, amount_rupees: int) -> dict[str, Any]:
        return {"provider": None, "providerOrderId": None, "paymentId": payment_id, "amountRupees": amount_rupees}

    def mark_paid(self, payment: dict[str, Any], provider_reference: str = "") -> dict[str, Any]:
        payment["status"] = "paid"
        payment["provider"] = payment.get("provider") or self.name
        payment["providerReference"] = provider_reference or payment.get("providerReference") or ""
        return payment


def policy_hash(text: str = POLICY_TEXT) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def policy_document() -> dict[str, Any]:
    return {
        "version": POLICY_VERSION,
        "text": POLICY_TEXT,
        "hash": policy_hash(),
        "firstFeeRupees": FIRST_FEE_RUPEES,
        "nextFeeRupees": NEXT_FEE_RUPEES,
        "commissionPercent": 25,
    }


def fee_rupees(conn: Any, teacher_phone: str) -> int:
    paid = conn.execute(
        "SELECT COUNT(*) FROM access_payments WHERE teacher_phone = ? AND status = 'paid'",
        (teacher_phone,),
    ).fetchone()[0]
    return FIRST_FEE_RUPEES if int(paid or 0) == 0 else NEXT_FEE_RUPEES


# Eight or more digits with at most one space, dot or dash between them read as a phone number.
# "5000 - 10000" is a range, not a phone, because of the spaced dash.
_PHONE_RE = re.compile(r"\+?\d(?:[\s.-]?\d){7,}")


def scrub_text(text: str, names: list[str]) -> str:
    """Remove phone numbers and the parent's or child's names from free text."""
    cleaned = _PHONE_RE.sub("[hidden]", text or "")
    for name in names:
        for part in {name.strip(), *name.split()}:
            if len(part.strip()) >= 2:
                cleaned = re.sub(rf"\b{re.escape(part.strip())}\b", "[hidden]", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def public_enquiry(row: Any) -> dict[str, Any]:
    """Enquiry fields safe to show anyone: no parent phone, names or street address."""
    names = [str(row["parent_name"] or ""), str(row["student_name"] or "")]
    return {
        "id": row["meta_lead_id"],
        "status": row["status"],
        "classLevel": row["class_level"],
        "subject": row["subject"],
        "board": row["board"],
        "medium": row["medium"],
        "tutorMode": row["tutor_mode"],
        "teacherPreference": row["teacher_preference"],
        "locality": scrub_text(row["locality"], names),
        "pin": row["pin"],
        "budget": row["budget"],
        "notes": scrub_text(row["notes"], names),
        "schedule": scrub_text(row["schedule"], names),
        "updatedAt": row["updated_at"],
    }


def _require_sync_key(supplied: str | None) -> None:
    expected = os.environ.get("WEBSITE_SYNC_SECRET", "").strip()
    if not expected or (supplied or "").strip() != expected:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Sync key required."}},
        )


def upsert_enquiry(conn: Any, body: EnquirySync) -> dict[str, Any]:
    lead_id = body.metaLeadId.strip()
    if not lead_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID", "message": "Lead id is required."}})
    status = "converted" if body.status == "converted" else "open"
    ts = now_iso()
    existing = conn.execute(
        "SELECT created_at FROM parent_enquiries WHERE meta_lead_id = ?",
        (lead_id,),
    ).fetchone()
    values = (
        status,
        body.parentPhone.strip(),
        body.parentName.strip(),
        body.studentName.strip(),
        body.classLevel.strip(),
        body.subject.strip(),
        body.board.strip(),
        body.medium.strip(),
        body.tutorMode.strip(),
        body.teacherPreference.strip(),
        body.address.strip(),
        body.locality.strip(),
        body.pin.strip(),
        body.budget.strip(),
        body.notes.strip(),
        body.schedule.strip(),
        body.convertedTeacherPhone.strip(),
        body.sourceRevision.strip(),
        ts,
        lead_id,
    )
    if existing:
        conn.execute(
            """
            UPDATE parent_enquiries
            SET status = ?, parent_phone = ?, parent_name = ?, student_name = ?, class_level = ?,
                subject = ?, board = ?, medium = ?, tutor_mode = ?, teacher_preference = ?,
                address = ?, locality = ?, pin = ?, budget = ?, notes = ?, schedule = ?,
                converted_teacher_phone = ?, source_revision = ?, updated_at = ?
            WHERE meta_lead_id = ?
            """,
            values,
        )
    else:
        conn.execute(
            """
            INSERT INTO parent_enquiries (
                meta_lead_id, status, parent_phone, parent_name, student_name, class_level,
                subject, board, medium, tutor_mode, teacher_preference, address, locality, pin, budget,
                notes, schedule, converted_teacher_phone, source_revision, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (lead_id, *values[:-1], ts),
        )
    return {"id": lead_id, "status": status}


def sync_teachers(conn: Any, teachers: list[dict[str, Any]]) -> int:
    ts = now_iso()
    count = 0
    for teacher in teachers:
        digits = "".join(ch for ch in str(teacher.get("phone") or "") if ch.isdigit())
        phone = digits[-10:] if len(digits) >= 10 else ""
        if len(phone) != 10:
            continue
        name = str(teacher.get("fullName") or teacher.get("full_name") or "").strip()
        current = conn.execute(
            "SELECT source, status, full_name FROM teacher_registry WHERE phone = ?",
            (phone,),
        ).fetchone()
        if current and current["source"] == "website" and current["status"] == "submitted":
            if name and not str(current["full_name"] or "").strip():
                conn.execute(
                    "UPDATE teacher_registry SET full_name = ?, updated_at = ? WHERE phone = ?",
                    (name, ts, phone),
                )
            count += 1
            continue
        conn.execute(
            """
            INSERT INTO teacher_registry (phone, full_name, source, status, updated_at)
            VALUES (?, ?, 'gold', 'imported', ?)
            ON CONFLICT(phone) DO UPDATE SET
              full_name = excluded.full_name,
              source = 'gold',
              status = 'imported',
              updated_at = excluded.updated_at
            """,
            (phone, name, ts),
        )
        count += 1
    return count


def note_website_teacher(conn: Any, phone: str, full_name: str) -> None:
    ts = now_iso()
    conn.execute(
        """
        INSERT INTO teacher_registry (phone, full_name, source, status, updated_at)
        VALUES (?, ?, 'website', 'submitted', ?)
        ON CONFLICT(phone) DO UPDATE SET
          full_name = excluded.full_name,
          source = 'website',
          status = 'submitted',
          updated_at = excluded.updated_at
        """,
        (phone, full_name.strip(), ts),
    )


def registration_source(conn: Any, phone: str) -> str:
    application = conn.execute(
        "SELECT status FROM teacher_applications WHERE phone = ?",
        (phone,),
    ).fetchone()
    if application and application["status"] == "Submitted":
        return "website"
    registered = conn.execute(
        "SELECT source, status FROM teacher_registry WHERE phone = ?",
        (phone,),
    ).fetchone()
    if registered and registered["status"] in {"submitted", "imported"}:
        return str(registered["source"] or "gold")
    return ""


def list_open(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM parent_enquiries
        WHERE status = 'open'
        ORDER BY updated_at DESC, meta_lead_id DESC
        """
    ).fetchall()
    return [public_enquiry(row) for row in rows]


def get_open(conn: Any, meta_lead_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM parent_enquiries WHERE meta_lead_id = ? AND status = 'open'",
        (meta_lead_id,),
    ).fetchone()
    if row is None:
        return None
    return public_enquiry(row)


def _interest_view(conn: Any, interest: Any, payment: Any) -> dict[str, Any]:
    teacher = conn.execute(
        "SELECT full_name FROM teacher_registry WHERE phone = ?",
        (interest["teacher_phone"],),
    ).fetchone()
    return {
        "interestId": interest["id"],
        "teacherPhone": interest["teacher_phone"],
        "fullName": teacher["full_name"] if teacher else "",
        "paymentId": payment["id"] if payment else "",
        "paymentStatus": payment["status"] if payment else "pending",
        "amountRupees": payment["amount_rupees"] if payment else 0,
        "createdAt": interest["created_at"],
    }


def list_interests(conn: Any, meta_lead_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM teacher_enquiry_interests
        WHERE meta_lead_id = ?
        ORDER BY created_at
        """,
        (meta_lead_id,),
    ).fetchall()
    people = []
    for interest in rows:
        payment = conn.execute(
            "SELECT * FROM access_payments WHERE interest_id = ?",
            (interest["id"],),
        ).fetchone()
        people.append(_interest_view(conn, interest, payment))
    return people


def apply_for_enquiry(conn: Any, meta_lead_id: str, teacher_phone: str, body: ApplyBody) -> dict[str, Any]:
    if not (body.isTutor and body.acceptNoRefund and body.acceptCommission):
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "POLICY_REQUIRED", "message": "Acknowledge the tutor policy before continuing."}},
        )
    if body.policyVersion != POLICY_VERSION:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "POLICY_CHANGED", "message": "Review the current policy and accept it again."}},
        )
    if not registration_source(conn, teacher_phone):
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "PROFILE_REQUIRED", "message": "Complete teacher registration before applying."}},
        )
    enquiry = conn.execute(
        "SELECT status FROM parent_enquiries WHERE meta_lead_id = ?",
        (meta_lead_id,),
    ).fetchone()
    if enquiry is None or enquiry["status"] != "open":
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "CLOSED", "message": "This enquiry is no longer open."}},
        )
    existing = conn.execute(
        """
        SELECT * FROM teacher_enquiry_interests
        WHERE meta_lead_id = ? AND teacher_phone = ?
        """,
        (meta_lead_id, teacher_phone),
    ).fetchone()
    if existing:
        payment = conn.execute(
            "SELECT * FROM access_payments WHERE interest_id = ?",
            (existing["id"],),
        ).fetchone()
        return {"interestId": existing["id"], "payment": _payment_public(payment), "created": False}
    ts = now_iso()
    interest_id = f"int_{uuid.uuid4().hex}"
    payment_id = f"pay_{uuid.uuid4().hex}"
    amount = fee_rupees(conn, teacher_phone)
    conn.execute(
        """
        INSERT INTO policy_acceptances (
            id, teacher_phone, meta_lead_id, policy_version, policy_hash, accepted_text, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (f"pol_{uuid.uuid4().hex}", teacher_phone, meta_lead_id, POLICY_VERSION, policy_hash(), POLICY_TEXT, ts),
    )
    conn.execute(
        """
        INSERT INTO teacher_enquiry_interests (
            id, meta_lead_id, teacher_phone, policy_version, policy_hash, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (interest_id, meta_lead_id, teacher_phone, POLICY_VERSION, policy_hash(), ts),
    )
    prepared = ManualPaymentGateway().prepare(payment_id, amount)
    conn.execute(
        """
        INSERT INTO access_payments (
            id, interest_id, meta_lead_id, teacher_phone, amount_rupees, amount_paise,
            currency, status, provider, provider_order_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'INR', 'pending', ?, ?, ?, ?)
        """,
        (
            payment_id,
            interest_id,
            meta_lead_id,
            teacher_phone,
            amount,
            amount * 100,
            prepared["provider"],
            prepared["providerOrderId"],
            ts,
            ts,
        ),
    )
    payment = conn.execute("SELECT * FROM access_payments WHERE id = ?", (payment_id,)).fetchone()
    return {"interestId": interest_id, "payment": _payment_public(payment), "created": True}


def _payment_public(payment: Any) -> dict[str, Any] | None:
    if payment is None:
        return None
    return {
        "id": payment["id"],
        "status": payment["status"],
        "amountRupees": payment["amount_rupees"],
        "amountPaise": payment["amount_paise"],
        "currency": payment["currency"],
        "provider": payment["provider"],
        "providerOrderId": payment["provider_order_id"],
        "providerReference": payment["provider_reference"],
    }


def mark_payment_paid(conn: Any, meta_lead_id: str, payment_id: str, provider_reference: str = "") -> dict[str, Any]:
    payment = conn.execute(
        "SELECT * FROM access_payments WHERE id = ? AND meta_lead_id = ?",
        (payment_id, meta_lead_id),
    ).fetchone()
    if payment is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Payment was not found."}})
    if payment["status"] == "paid":
        return _payment_public(payment) or {}
    updated = ManualPaymentGateway().mark_paid(
        {
            "status": payment["status"],
            "provider": payment["provider"],
            "providerReference": payment["provider_reference"] or "",
        },
        provider_reference,
    )
    ts = now_iso()
    conn.execute(
        """
        UPDATE access_payments
        SET status = 'paid', provider = ?, provider_reference = ?, paid_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (updated["provider"], updated["providerReference"], ts, ts, payment_id),
    )
    saved = conn.execute("SELECT * FROM access_payments WHERE id = ?", (payment_id,)).fetchone()
    return _payment_public(saved) or {}


def parent_contact(conn: Any, meta_lead_id: str, teacher_phone: str) -> dict[str, Any]:
    enquiry = conn.execute(
        "SELECT * FROM parent_enquiries WHERE meta_lead_id = ?",
        (meta_lead_id,),
    ).fetchone()
    if enquiry is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Enquiry was not found."}})
    payment = conn.execute(
        """
        SELECT status FROM access_payments
        WHERE meta_lead_id = ? AND teacher_phone = ?
        """,
        (meta_lead_id, teacher_phone),
    ).fetchone()
    if payment is None:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Apply for this enquiry before requesting the parent number."}},
        )
    if payment["status"] != "paid":
        raise HTTPException(
            status_code=402,
            detail={"error": {"code": "PAYMENT_PENDING", "message": "The parent number stays hidden until the access fee is confirmed."}},
        )
    return {
        "parentPhone": enquiry["parent_phone"],
        "parentName": enquiry["parent_name"],
    }


def my_applications(conn: Any, teacher_phone: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT i.meta_lead_id, i.created_at, e.status AS enquiry_status, e.student_name, e.subject, e.class_level,
               p.id AS payment_id, p.status AS payment_status, p.amount_rupees, e.parent_phone, e.parent_name
        FROM teacher_enquiry_interests i
        JOIN parent_enquiries e ON e.meta_lead_id = i.meta_lead_id
        LEFT JOIN access_payments p ON p.interest_id = i.id
        WHERE i.teacher_phone = ?
        ORDER BY i.created_at DESC
        """,
        (teacher_phone,),
    ).fetchall()
    items = []
    for row in rows:
        paid = row["payment_status"] == "paid"
        items.append(
            {
                "enquiryId": row["meta_lead_id"],
                "studentName": row["student_name"] if paid else "",
                "subject": row["subject"],
                "classLevel": row["class_level"],
                "enquiryStatus": row["enquiry_status"],
                "paymentId": row["payment_id"],
                "paymentStatus": row["payment_status"] or "pending",
                "amountRupees": row["amount_rupees"] or 0,
                "createdAt": row["created_at"],
                "parentPhone": row["parent_phone"] if paid else "",
                "parentName": row["parent_name"] if paid else "",
            }
        )
    return items


def _sync_and_commit() -> None:
    from app.main import sync_to_gcs

    sync_to_gcs()


def _teacher_session(session: dict[str, Any]) -> str:
    if session.get("role") != "teacher":
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Log in as a teacher to continue."}},
        )
    return str(session["phone"])


@router.get("/api/parent-enquiries/policy")
@router.get("/v1/api/parent-enquiries/policy")
def read_policy() -> dict[str, Any]:
    return policy_document()


@router.get("/api/parent-enquiries")
@router.get("/v1/api/parent-enquiries")
def read_enquiries() -> dict[str, Any]:
    with connect(read_only=True) as conn:
        return {"items": list_open(conn)}


@router.get("/api/parent-enquiries/{meta_lead_id}")
@router.get("/v1/api/parent-enquiries/{meta_lead_id}")
def read_enquiry(meta_lead_id: str) -> dict[str, Any]:
    with connect(read_only=True) as conn:
        item = get_open(conn, meta_lead_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Enquiry was not found."}})
    return item


@router.get("/api/teacher/enquiry-eligibility")
@router.get("/v1/api/teacher/enquiry-eligibility")
def enquiry_eligibility(session: dict[str, Any] = Depends(get_session)) -> dict[str, Any]:
    phone = _teacher_session(session)
    with connect(read_only=True) as conn:
        source = registration_source(conn, phone)
        amount = fee_rupees(conn, phone)
    return {"registered": bool(source), "source": source or "none", "nextFeeRupees": amount}


@router.get("/api/teacher/parent-enquiries")
@router.get("/v1/api/teacher/parent-enquiries")
def teacher_parent_enquiries(session: dict[str, Any] = Depends(get_session)) -> dict[str, Any]:
    phone = _teacher_session(session)
    with connect(read_only=True) as conn:
        return {"items": my_applications(conn, phone)}


@router.post("/api/parent-enquiries/{meta_lead_id}/apply")
@router.post("/v1/api/parent-enquiries/{meta_lead_id}/apply")
def apply(meta_lead_id: str, body: ApplyBody, session: dict[str, Any] = Depends(get_session)) -> dict[str, Any]:
    phone = _teacher_session(session)
    with connect() as conn:
        result = apply_for_enquiry(conn, meta_lead_id, phone, body)
        conn.commit()
    _sync_and_commit()
    return result


@router.get("/api/parent-enquiries/{meta_lead_id}/contact")
@router.get("/v1/api/parent-enquiries/{meta_lead_id}/contact")
def contact(meta_lead_id: str, session: dict[str, Any] = Depends(get_session)) -> dict[str, Any]:
    phone = _teacher_session(session)
    with connect(read_only=True) as conn:
        return parent_contact(conn, meta_lead_id, phone)


@router.post("/api/internal/parent-enquiries")
@router.post("/v1/api/internal/parent-enquiries")
def internal_upsert(
    body: EnquirySync,
    x_website_sync_key: str | None = Header(default=None, alias="X-Website-Sync-Key"),
) -> dict[str, Any]:
    _require_sync_key(x_website_sync_key)
    with connect() as conn:
        saved = upsert_enquiry(conn, body)
        conn.commit()
    _sync_and_commit()
    return saved


@router.post("/api/internal/parent-enquiries/close")
@router.post("/v1/api/internal/parent-enquiries/close")
def internal_close(
    body: EnquirySync,
    x_website_sync_key: str | None = Header(default=None, alias="X-Website-Sync-Key"),
) -> dict[str, Any]:
    _require_sync_key(x_website_sync_key)
    closed = body.model_copy(update={"status": "converted"})
    with connect() as conn:
        saved = upsert_enquiry(conn, closed)
        conn.commit()
    _sync_and_commit()
    return saved


@router.post("/api/internal/teachers")
@router.post("/v1/api/internal/teachers")
def internal_teachers(
    body: TeacherSync,
    x_website_sync_key: str | None = Header(default=None, alias="X-Website-Sync-Key"),
) -> dict[str, Any]:
    _require_sync_key(x_website_sync_key)
    with connect() as conn:
        count = sync_teachers(conn, body.teachers)
        conn.commit()
    _sync_and_commit()
    return {"imported": count}


@router.get("/api/internal/parent-enquiries/{meta_lead_id}/interests")
@router.get("/v1/api/internal/parent-enquiries/{meta_lead_id}/interests")
def internal_interests(
    meta_lead_id: str,
    x_website_sync_key: str | None = Header(default=None, alias="X-Website-Sync-Key"),
) -> dict[str, Any]:
    _require_sync_key(x_website_sync_key)
    with connect(read_only=True) as conn:
        return {"applicants": list_interests(conn, meta_lead_id)}


@router.post("/api/internal/parent-enquiries/{meta_lead_id}/payments/{payment_id}/paid")
@router.post("/v1/api/internal/parent-enquiries/{meta_lead_id}/payments/{payment_id}/paid")
def internal_mark_paid(
    meta_lead_id: str,
    payment_id: str,
    x_website_sync_key: str | None = Header(default=None, alias="X-Website-Sync-Key"),
) -> dict[str, Any]:
    _require_sync_key(x_website_sync_key)
    with connect() as conn:
        saved = mark_payment_paid(conn, meta_lead_id, payment_id, "manual")
        conn.commit()
    _sync_and_commit()
    return saved
