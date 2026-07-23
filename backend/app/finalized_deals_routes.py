from __future__ import annotations

from pathlib import Path
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.finalized_deals_auth import (
    clear_session_cookie,
    is_authenticated,
    require_finalized_deals_session,
    set_session_cookie,
    verify_password,
)
from app.finalized_deals_db import (
    get_deal,
    insert_deal,
    list_deals,
    soft_delete_deal,
    update_deal,
)
from app.finalized_deals_gcs import GcsBusyError, pull_finalized_deals_db, push_finalized_deals_db

router = APIRouter(tags=["finalized-deals"])
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _sync_pull() -> None:
    pull_finalized_deals_db()


def _sync_push() -> None:
    push_finalized_deals_db()


def _form_fields(
    *,
    parent_name: str = "",
    parent_phone: str = "",
    parent_class: str = "",
    parent_location: str = "",
    parent_mode: str = "",
    teacher_name: str = "",
    teacher_phone: str = "",
    teacher_subject: str = "",
    teacher_notes: str = "",
    finalized_amount: str = "",
    class_start_date: str = "",
) -> dict[str, Any]:
    return {
        "parent_name": parent_name,
        "parent_phone": parent_phone,
        "parent_class": parent_class,
        "parent_location": parent_location,
        "parent_mode": parent_mode,
        "teacher_name": teacher_name,
        "teacher_phone": teacher_phone,
        "teacher_subject": teacher_subject,
        "teacher_notes": teacher_notes,
        "finalized_amount": finalized_amount,
        "class_start_date": class_start_date,
    }


@router.get("/finilized_deals", response_class=HTMLResponse)
def finalized_deals_home(request: Request, error: str | None = None, msg: str | None = None):
    if not is_authenticated(request):
        return templates.TemplateResponse(
            request,
            "finalized_deals_login.html",
            {"error": error},
        )
    try:
        _sync_pull()
        deals = list_deals()
    except GcsBusyError as exc:
        return templates.TemplateResponse(
            request,
            "finalized_deals.html",
            {"deals": [], "error": str(exc), "msg": msg, "form": _form_fields()},
        )
    return templates.TemplateResponse(
        request,
        "finalized_deals.html",
        {"deals": deals, "error": error, "msg": msg, "form": _form_fields()},
    )


@router.post("/finilized_deals/login")
def finalized_deals_login(password: str = Form(...)):
    if not verify_password(password):
        return RedirectResponse(url="/finilized_deals?error=Invalid+password", status_code=303)
    response = RedirectResponse(url="/finilized_deals", status_code=303)
    set_session_cookie(response)
    return response


@router.post("/finilized_deals/logout")
def finalized_deals_logout():
    response = RedirectResponse(url="/finilized_deals", status_code=303)
    clear_session_cookie(response)
    return response


@router.post("/finilized_deals/submit")
def finalized_deals_submit(
    _: Annotated[None, Depends(require_finalized_deals_session)],
    parent_name: str = Form(""),
    parent_phone: str = Form(""),
    parent_class: str = Form(""),
    parent_location: str = Form(""),
    parent_mode: str = Form(""),
    teacher_name: str = Form(""),
    teacher_phone: str = Form(""),
    teacher_subject: str = Form(""),
    teacher_notes: str = Form(""),
    finalized_amount: str = Form(""),
    class_start_date: str = Form(...),
):
    if not class_start_date.strip():
        return RedirectResponse(url="/finilized_deals?error=Start+date+is+required", status_code=303)
    fields = _form_fields(
        parent_name=parent_name,
        parent_phone=parent_phone,
        parent_class=parent_class,
        parent_location=parent_location,
        parent_mode=parent_mode,
        teacher_name=teacher_name,
        teacher_phone=teacher_phone,
        teacher_subject=teacher_subject,
        teacher_notes=teacher_notes,
        finalized_amount=finalized_amount,
        class_start_date=class_start_date,
    )
    try:
        _sync_pull()
        insert_deal(fields)
        _sync_push()
    except GcsBusyError:
        return RedirectResponse(url="/finilized_deals?error=Database+busy", status_code=303)
    return RedirectResponse(url="/finilized_deals?msg=Deal+saved", status_code=303)


@router.get("/finilized_deals/edit/{deal_id}", response_class=HTMLResponse)
def finalized_deals_edit_page(deal_id: str, request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/finilized_deals", status_code=303)
    try:
        _sync_pull()
        deal = get_deal(deal_id)
    except GcsBusyError as exc:
        return RedirectResponse(url=f"/finilized_deals?error={exc}", status_code=303)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    form = _form_fields(
        parent_name=deal.get("parent_name") or "",
        parent_phone=deal.get("parent_phone") or "",
        parent_class=deal.get("parent_class") or "",
        parent_location=deal.get("parent_location") or "",
        parent_mode=deal.get("parent_mode") or "",
        teacher_name=deal.get("teacher_name") or "",
        teacher_phone=deal.get("teacher_phone") or "",
        teacher_subject=deal.get("teacher_subject") or "",
        teacher_notes=deal.get("teacher_notes") or "",
        finalized_amount=str(deal.get("finalized_amount") or ""),
        class_start_date=(deal.get("class_start_date") or "")[:10],
    )
    return templates.TemplateResponse(
        request,
        "finalized_deals_edit.html",
        {"deal_id": deal_id, "form": form, "deal": deal},
    )


@router.post("/finilized_deals/edit/{deal_id}")
def finalized_deals_edit_save(
    deal_id: str,
    _: Annotated[None, Depends(require_finalized_deals_session)],
    parent_name: str = Form(""),
    parent_phone: str = Form(""),
    parent_class: str = Form(""),
    parent_location: str = Form(""),
    parent_mode: str = Form(""),
    teacher_name: str = Form(""),
    teacher_phone: str = Form(""),
    teacher_subject: str = Form(""),
    teacher_notes: str = Form(""),
    finalized_amount: str = Form(""),
    class_start_date: str = Form(...),
):
    fields = _form_fields(
        parent_name=parent_name,
        parent_phone=parent_phone,
        parent_class=parent_class,
        parent_location=parent_location,
        parent_mode=parent_mode,
        teacher_name=teacher_name,
        teacher_phone=teacher_phone,
        teacher_subject=teacher_subject,
        teacher_notes=teacher_notes,
        finalized_amount=finalized_amount,
        class_start_date=class_start_date,
    )
    try:
        _sync_pull()
        updated = update_deal(deal_id, fields)
        if not updated:
            return RedirectResponse(url="/finilized_deals?error=Deal+not+found", status_code=303)
        _sync_push()
    except GcsBusyError:
        return RedirectResponse(url="/finilized_deals?error=Database+busy", status_code=303)
    return RedirectResponse(url="/finilized_deals?msg=Deal+updated", status_code=303)


@router.post("/finilized_deals/delete/{deal_id}")
def finalized_deals_delete(deal_id: str, _: Annotated[None, Depends(require_finalized_deals_session)]):
    try:
        _sync_pull()
        if not soft_delete_deal(deal_id):
            return RedirectResponse(url="/finilized_deals?error=Deal+not+found", status_code=303)
        _sync_push()
    except GcsBusyError:
        return RedirectResponse(url="/finilized_deals?error=Database+busy", status_code=303)
    return RedirectResponse(url="/finilized_deals?msg=Deal+deleted", status_code=303)
