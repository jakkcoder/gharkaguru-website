"""FastAPI routes for parent leads inbox: admin agent management + agent portal."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.parent_leads import agents_db, db, gcs_db
from app.parent_leads.admin_report import admin_dashboard
from app.parent_leads.assign import assign_unassigned_leads
from app.parent_leads.auth import (
    admin_session,
    agent_session,
    clear_admin_cookie,
    clear_agent_cookie,
    optional_admin,
    optional_agent_id,
    set_admin_cookie,
    set_agent_cookie,
    verify_admin_password,
)
from app.parent_leads.agents_db import authenticate_agent
from app.parent_leads.config import (
    NEXT_STAGE,
    PORTAL_TABS,
    PREV_STAGE,
    STAGE_ASSIGNED,
    STAGE_LABELS,
    TAB_JUNK,
)
from app.parent_leads.pull import run_pull

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/parent_leads", tags=["parent_leads"])


def _refresh_db() -> None:
    """Load latest SQLite from GCS before reads (multi-instance safe)."""
    try:
        gcs_db.pull_db()
        db.init_db()
    except Exception:
        db.init_db()
        try:
            from app.parent_leads.agent_secrets import apply_secrets_to_db

            apply_secrets_to_db()
        except Exception:
            pass


def _persist() -> None:
    """Push SQLite to GCS after writes; fail loudly if sync fails."""
    gcs_db.push_db()


# --- Admin ---


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    if optional_admin(request.cookies.get("pli_admin")):
        return RedirectResponse("/parent_leads/admin/dashboard", status_code=303)
    error = request.query_params.get("error")
    return templates.TemplateResponse(request, "admin_login.html", {"error": error})


@router.post("/admin/login")
def admin_login_post(password: str = Form(...)):
    if not verify_admin_password(password):
        return RedirectResponse("/parent_leads/admin/login?error=Invalid+password", status_code=303)
    response = RedirectResponse("/parent_leads/admin/dashboard", status_code=303)
    set_admin_cookie(response)
    return response


@router.post("/admin/logout")
def admin_logout():
    response = RedirectResponse("/parent_leads/admin/login", status_code=303)
    clear_admin_cookie(response)
    return response


@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard_page(
    request: Request,
    _: None = Depends(admin_session),
):
    _refresh_db()
    data = admin_dashboard()
    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        data,
    )


@router.get("/admin/agents", response_class=HTMLResponse)
def admin_agents_page(
    request: Request,
    _: None = Depends(admin_session),
):
    _refresh_db()
    msg = request.query_params.get("msg")
    error = request.query_params.get("error")
    agents = agents_db.list_agents()
    traffic = agents_db.normalized_traffic_summary()
    lead_counts = agents_db.agent_lead_counts()
    inbox = db.counts()
    return templates.TemplateResponse(
        request,
        "admin_agents.html",
        {
            "agents": agents,
            "traffic": traffic,
            "lead_counts": lead_counts,
            "inbox": inbox,
            "msg": msg,
            "error": error,
        },
    )


@router.post("/admin/agents")
def admin_create_agent(
    _: None = Depends(admin_session),
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    traffic_percent: int = Form(0),
):
    try:
        _refresh_db()
        agents_db.create_agent(
            name=name,
            email=email,
            password=password,
            traffic_percent=traffic_percent,
        )
        _persist()
    except Exception as exc:
        return RedirectResponse(f"/parent_leads/admin/agents?error={exc}", status_code=303)
    return RedirectResponse("/parent_leads/admin/agents?msg=Agent+created", status_code=303)


@router.post("/admin/agents/{agent_id}/update")
def admin_update_agent(
    agent_id: str,
    _: None = Depends(admin_session),
    name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    traffic_percent: int = Form(-1),
    is_active: str = Form("1"),
):
    _refresh_db()
    updated = agents_db.update_agent(
        agent_id,
        name=name or None,
        email=email or None,
        password=password or None,
        traffic_percent=traffic_percent if traffic_percent >= 0 else None,
        is_active=is_active == "1",
    )
    if not updated:
        return RedirectResponse("/parent_leads/admin/agents?error=Agent+not+found", status_code=303)
    _persist()
    return RedirectResponse("/parent_leads/admin/agents?msg=Agent+updated", status_code=303)


@router.get("/admin/reassign", response_class=HTMLResponse)
def admin_reassign_page(
    request: Request,
    _: None = Depends(admin_session),
    agent_id: str | None = Query(None),
):
    _refresh_db()
    agents = agents_db.list_agents()
    filter_agent = agent_id or None
    leads = db.admin_list_leads(from_agent_id=filter_agent)
    stage_labels = dict(STAGE_LABELS)
    stage_labels[TAB_JUNK] = "Junk"
    return templates.TemplateResponse(
        request,
        "admin_reassign.html",
        {
            "agents": [a for a in agents if a.get("is_active")],
            "leads": leads,
            "filter_agent": filter_agent or "",
            "stage_labels": stage_labels,
            "msg": request.query_params.get("msg"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/admin/leads/{lead_id}/reassign")
def admin_reassign_lead_post(
    lead_id: str,
    _: None = Depends(admin_session),
    to_agent_id: str = Form(...),
):
    try:
        _refresh_db()
        updated = db.admin_reassign_lead(lead_id, to_agent_id)
        if not updated:
            return RedirectResponse(
                "/parent_leads/admin/reassign?error=Could+not+move+lead",
                status_code=303,
            )
        _persist()
    except Exception as exc:
        return RedirectResponse(
            f"/parent_leads/admin/reassign?error={exc}",
            status_code=303,
        )
    return RedirectResponse(
        "/parent_leads/admin/reassign?msg=Lead+moved+and+saved+to+GCS",
        status_code=303,
    )


@router.post("/admin/reassign/bulk")
def admin_reassign_bulk_post(
    _: None = Depends(admin_session),
    from_agent_id: str = Form(...),
    to_agent_id: str = Form(...),
):
    try:
        _refresh_db()
        moved = db.admin_bulk_reassign(from_agent_id, to_agent_id)
        if moved <= 0:
            return RedirectResponse(
                "/parent_leads/admin/reassign?error=No+leads+moved",
                status_code=303,
            )
        _persist()
    except Exception as exc:
        return RedirectResponse(
            f"/parent_leads/admin/reassign?error={exc}",
            status_code=303,
        )
    return RedirectResponse(
        f"/parent_leads/admin/reassign?msg=Moved+{moved}+leads+to+GCS",
        status_code=303,
    )


@router.post("/admin/pull")
def admin_pull(
    _: None = Depends(admin_session),
    assign_existing: str = Form("0"),
):
    try:
        _refresh_db()
        removed = db.purge_leads_before_start_date()
        result = run_pull(
            push=False,
            pull_db_first=False,
            assign_new=True,
            assign_existing=assign_existing == "1",
        )
        _persist()
        assigned = result.get("assignment", {}).get("assigned", 0)
        inserted = result.get("inserted", 0)
        refreshed = result.get("contact_fields_refreshed", 0)
        return RedirectResponse(
            f"/parent_leads/admin/agents?msg=Pulled+{inserted}+new%2C+refreshed+{refreshed}%2C+assigned+{assigned}%2C+purged+{removed}",
            status_code=303,
        )
    except Exception as exc:
        return RedirectResponse(f"/parent_leads/admin/agents?error={exc}", status_code=303)


# --- Agent auth ---


@router.get("/login", response_class=HTMLResponse)
def agent_login_page(request: Request):
    if optional_agent_id(request.cookies.get("pli_agent")):
        return RedirectResponse("/parent_leads/portal", status_code=303)
    error = request.query_params.get("error")
    return templates.TemplateResponse(request, "agent_login.html", {"error": error})


@router.post("/login")
def agent_login_post(email: str = Form(...), password: str = Form(...)):
    _refresh_db()
    agent = authenticate_agent(email, password)
    if not agent:
        return RedirectResponse("/parent_leads/login?error=Invalid+email+or+password", status_code=303)
    response = RedirectResponse("/parent_leads/portal", status_code=303)
    set_agent_cookie(response, agent["id"])
    return response


@router.post("/logout")
def agent_logout():
    response = RedirectResponse("/parent_leads/login", status_code=303)
    clear_agent_cookie(response)
    return response


# --- Agent portal ---


@router.get("/portal", response_class=HTMLResponse)
def agent_portal(
    request: Request,
    tab: str = Query(STAGE_ASSIGNED),
    agent_id: str = Depends(agent_session),
):
    _refresh_db()
    msg = request.query_params.get("msg")
    if tab not in PORTAL_TABS:
        tab = STAGE_ASSIGNED
    agent = agents_db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    counts = db.stage_counts_for_agent(agent_id)
    leads = db.list_leads_for_agent(agent_id, tab)
    next_labels = {s: STAGE_LABELS.get(NEXT_STAGE[s], "") for s in PORTAL_TABS if s in NEXT_STAGE}
    prev_labels = {s: STAGE_LABELS.get(PREV_STAGE[s], "") for s in PORTAL_TABS if s in PREV_STAGE}
    return templates.TemplateResponse(
        request,
        "portal.html",
        {
            "agent": agent,
            "tab": tab,
            "stages": PORTAL_TABS,
            "stage_labels": STAGE_LABELS,
            "counts": counts,
            "leads": leads,
            "next_labels": next_labels,
            "prev_labels": prev_labels,
            "msg": msg,
        },
    )


@router.post("/portal/leads/{lead_id}/advance")
def portal_advance_lead(
    lead_id: str,
    tab: str = Form(STAGE_ASSIGNED),
    agent_id: str = Depends(agent_session),
):
    try:
        updated = db.advance_lead_stage(lead_id, agent_id)
        if not updated:
            return RedirectResponse("/parent_leads/portal?tab=" + tab + "&msg=Could+not+advance+lead", status_code=303)
        _persist()
    except Exception as exc:
        return RedirectResponse(f"/parent_leads/portal?tab={tab}&error={exc}", status_code=303)
    new_tab = updated.get("pipeline_stage") or tab
    return RedirectResponse(f"/parent_leads/portal?tab={new_tab}&msg=Lead+updated", status_code=303)


@router.post("/portal/leads/{lead_id}/move-back")
def portal_move_back_lead(
    lead_id: str,
    tab: str = Form(STAGE_ASSIGNED),
    agent_id: str = Depends(agent_session),
):
    try:
        updated = db.move_back_lead_stage(lead_id, agent_id)
        if not updated:
            return RedirectResponse(
                f"/parent_leads/portal?tab={tab}&msg=Could+not+move+lead+back",
                status_code=303,
            )
        _persist()
    except Exception as exc:
        return RedirectResponse(f"/parent_leads/portal?tab={tab}&error={exc}", status_code=303)
    new_tab = updated.get("pipeline_stage") or tab
    return RedirectResponse(f"/parent_leads/portal?tab={new_tab}&msg=Moved+back", status_code=303)


@router.post("/portal/leads/{lead_id}/fill")
def portal_fill_lead(
    lead_id: str,
    tab: str = Form(STAGE_ASSIGNED),
    agent_id: str = Depends(agent_session),
    parent_name: str = Form(""),
    student_name: str = Form(""),
    student_class: str = Form(""),
    subject: str = Form(""),
    location: str = Form(""),
    mode: str = Form(""),
    budget: str = Form(""),
    note: str = Form(""),
):
    try:
        updated = db.update_lead_fill(
            lead_id,
            agent_id,
            parent_name=parent_name,
            student_name=student_name,
            student_class=student_class,
            subject=subject,
            location=location,
            mode=mode,
            budget=budget,
            note=note,
        )
        if not updated:
            return RedirectResponse(f"/parent_leads/portal?tab={tab}&msg=Could+not+save+lead", status_code=303)
        _persist()
    except Exception as exc:
        return RedirectResponse(f"/parent_leads/portal?tab={tab}&error={exc}", status_code=303)
    return RedirectResponse(f"/parent_leads/portal?tab={tab}&msg=Lead+saved+to+GCS", status_code=303)


@router.post("/portal/leads/{lead_id}/junk")
def portal_junk_lead(
    lead_id: str,
    tab: str = Form(STAGE_ASSIGNED),
    agent_id: str = Depends(agent_session),
):
    try:
        updated = db.mark_lead_junk(lead_id, agent_id)
        if not updated:
            return RedirectResponse(f"/parent_leads/portal?tab={tab}&msg=Could+not+mark+junk", status_code=303)
        _persist()
    except Exception as exc:
        return RedirectResponse(f"/parent_leads/portal?tab={tab}&error={exc}", status_code=303)
    return RedirectResponse(f"/parent_leads/portal?tab={TAB_JUNK}&msg=Moved+to+junk", status_code=303)


@router.post("/portal/leads/{lead_id}/promote")
def portal_promote_lead(
    lead_id: str,
    tab: str = Form(STAGE_ASSIGNED),
    agent_id: str = Depends(agent_session),
    teacher_phone: str = Form(...),
):
    try:
        updated = db.promote_lead_with_teacher(lead_id, agent_id, teacher_phone)
        if not updated:
            return RedirectResponse(f"/parent_leads/portal?tab={tab}&msg=Enter+teacher+phone", status_code=303)
        _persist()
    except Exception as exc:
        return RedirectResponse(f"/parent_leads/portal?tab={tab}&error={exc}", status_code=303)
    return RedirectResponse(
        f"/parent_leads/portal?tab={updated.get('pipeline_stage', tab)}&msg=Promoted+with+teacher",
        status_code=303,
    )


@router.get("/")
def root():
    return RedirectResponse("/parent_leads/login", status_code=303)
