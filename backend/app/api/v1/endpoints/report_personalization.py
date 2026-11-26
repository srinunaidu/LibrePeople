"""Saved views and scheduled reporting over the read-only reports.

Part E (saved views) and Part F (scheduled reporting) for the existing
reports (joiners/leavers/attrition/payroll-summary). Views and schedules
require REPORTS_ROLES; publishing a shared view requires HR/SuperAdmin.
Execution runs-as-owner through the existing JobWorker as REPORT_RUN jobs —
there is no new scheduler or cron process here, only an admin ``tick``
trigger that enqueues due work on the existing queue.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, REPORTS_ROLES, get_db, require_roles
from app.core.errors import forbidden
from app.core.tenancy import tenant_column_criterion, tenant_id_for
from app.models.report_personalization import (
    ReportRun,
    ReportSavedView,
    ReportSchedule,
)
from app.models.user import User
from app.services import report_personalization as svc

views_router = APIRouter()
schedules_router = APIRouter()


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------

def _tenant_or_401(db: Session) -> str:
    tenant_id = tenant_id_for(db)
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="No tenant resolved for this request")
    return tenant_id


def _view_to_out(view: ReportSavedView) -> dict:
    return {
        "id": view.id,
        "owner_id": view.owner_id,
        "name": view.name,
        "report_key": view.report_key,
        "filters": svc.parse_filters(view.filters_json),
        "visibility": view.visibility,
        "created_at": view.created_at.isoformat() if view.created_at else None,
    }


def _schedule_to_out(schedule: ReportSchedule) -> dict:
    try:
        recipient_ids = json.loads(schedule.recipient_ids_json or "[]")
    except ValueError:
        recipient_ids = []
    return {
        "id": schedule.id,
        "owner_id": schedule.owner_id,
        "report_key": schedule.report_key,
        "filters": svc.parse_filters(schedule.filters_json),
        "frequency": schedule.frequency,
        "timezone": schedule.timezone,
        "recipient_user_ids": recipient_ids,
        "output_format": schedule.output_format,
        "next_due_at": schedule.next_due_at.isoformat() if schedule.next_due_at else None,
        "active": bool(schedule.active),
        "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
    }


def _get_view_or_404(db: Session, tenant_id: str, view_id: int) -> ReportSavedView:
    view = (
        db.query(ReportSavedView)
        .filter(ReportSavedView.id == view_id)
        .filter(tenant_column_criterion(ReportSavedView.tenant_id, tenant_id))
        .first()
    )
    if view is None:
        # Cross-tenant ids read 404: a foreign row is indistinguishable
        # from a missing one.
        raise HTTPException(status_code=404, detail="Saved view not found")
    return view


def _get_schedule_or_404(db: Session, tenant_id: str, schedule_id: int) -> ReportSchedule:
    schedule = (
        db.query(ReportSchedule)
        .filter(ReportSchedule.id == schedule_id)
        .filter(tenant_column_criterion(ReportSchedule.tenant_id, tenant_id))
        .first()
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    return schedule


def _refuse_unless_owner_or_admin(view_owner_id: int, current_user: User) -> None:
    if view_owner_id != current_user.id and current_user.role not in ADMIN_ROLES:
        raise forbidden("Only the owner or an HR administrator may change this")


# --------------------------------------------------------------------------
# Part E — saved views
# --------------------------------------------------------------------------

@views_router.post("", status_code=201, operation_id="reportViewsCreate")
def create_view(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    name = (payload.get("name") or "").strip() if isinstance(payload.get("name"), str) else ""
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    try:
        report_key = svc.validate_report_key(payload.get("report_key"))
        filters = svc.parse_filters(payload.get("filters", {}))
        visibility = svc.validate_visibility(payload.get("visibility", "personal"))
    except svc.ReportPersonalizationError as exc:
        # Unknown keys refuse with 422 and no row is written.
        raise HTTPException(status_code=422, detail=str(exc))
    if visibility == "shared" and current_user.role not in svc.SHARE_ROLES:
        raise forbidden("Publishing a shared view requires the HR or SuperAdmin role")
    view = ReportSavedView(
        tenant_id=tenant_id,
        owner_id=current_user.id,
        name=name[:120],
        report_key=report_key,
        filters_json=json.dumps(filters),
        visibility=visibility,
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    return _view_to_out(view)


@views_router.get("", operation_id="reportViewsList")
def list_views(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    rows = (
        db.query(ReportSavedView)
        .filter(tenant_column_criterion(ReportSavedView.tenant_id, tenant_id))
        .order_by(ReportSavedView.id.asc())
        .all()
    )
    visible = [
        v for v in rows
        if v.owner_id == current_user.id
        or (v.visibility == "shared" and svc.role_may_view_report(current_user.role, v.report_key))
    ]
    return {"views": [_view_to_out(v) for v in visible], "count": len(visible)}


@views_router.get("/{view_id}", operation_id="reportViewsGet")
def get_view(
    view_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    view = _get_view_or_404(db, tenant_id, view_id)
    if view.owner_id != current_user.id and not (
        view.visibility == "shared"
        and svc.role_may_view_report(current_user.role, view.report_key)
    ):
        raise HTTPException(status_code=404, detail="Saved view not found")
    return _view_to_out(view)


@views_router.patch("/{view_id}", operation_id="reportViewsPatch")
def patch_view(
    view_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    view = _get_view_or_404(db, tenant_id, view_id)
    _refuse_unless_owner_or_admin(view.owner_id, current_user)
    if "report_key" in payload:
        try:
            view.report_key = svc.validate_report_key(payload.get("report_key"))
        except svc.ReportPersonalizationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    if "filters" in payload:
        try:
            filters = svc.parse_filters(payload.get("filters"))
        except svc.ReportPersonalizationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        view.filters_json = json.dumps(filters)
    if "name" in payload:
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=422, detail="name is required")
        view.name = name.strip()[:120]
    if "visibility" in payload:
        try:
            visibility = svc.validate_visibility(payload.get("visibility"))
        except svc.ReportPersonalizationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        if visibility == "shared" and current_user.role not in svc.SHARE_ROLES:
            raise forbidden("Publishing a shared view requires the HR or SuperAdmin role")
        view.visibility = visibility
    db.add(view)
    db.commit()
    db.refresh(view)
    return _view_to_out(view)


@views_router.delete("/{view_id}", status_code=204, operation_id="reportViewsDelete")
def delete_view(
    view_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Response:
    tenant_id = _tenant_or_401(db)
    view = _get_view_or_404(db, tenant_id, view_id)
    _refuse_unless_owner_or_admin(view.owner_id, current_user)
    db.delete(view)
    db.commit()
    return Response(status_code=204)


# --------------------------------------------------------------------------
# Part F — scheduled reporting
# --------------------------------------------------------------------------

def _validate_schedule_payload(payload: dict[str, Any], db: Session) -> dict:
    """Validate creation input; raises 422/403, enqueues nothing."""
    try:
        report_key = svc.validate_report_key(payload.get("report_key"))
        filters = svc.parse_filters(payload.get("filters", {}))
        frequency = svc.validate_frequency(payload.get("frequency", "daily"))
        tz_name = (
            svc.validate_timezone(payload["timezone"])
            if payload.get("timezone") not in (None, "")
            else svc.default_timezone()
        )
        output_format = svc.validate_output_format(payload.get("output_format", "csv"))
    except svc.ReportPersonalizationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    recipient_ids = payload.get("recipient_user_ids", [])
    if not isinstance(recipient_ids, list) or any(
        isinstance(r, bool) or not isinstance(r, int) for r in recipient_ids
    ):
        raise HTTPException(status_code=422, detail="recipient_user_ids must be a list of user ids")
    for rid in recipient_ids:
        if db.query(User).filter(User.id == rid).first() is None:
            raise HTTPException(status_code=422, detail=f"recipient user {rid} does not exist")
    return {
        "report_key": report_key,
        "filters": filters,
        "frequency": frequency,
        "timezone": tz_name,
        "recipient_ids": list(recipient_ids),
        "output_format": output_format,
    }


@schedules_router.post("", status_code=201, operation_id="reportSchedulesCreate")
def create_schedule(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    cleaned = _validate_schedule_payload(payload, db)
    # Schedule creation enqueues nothing synchronously: the due tick does.
    schedule = ReportSchedule(
        tenant_id=tenant_id,
        owner_id=current_user.id,
        report_key=cleaned["report_key"],
        filters_json=json.dumps(cleaned["filters"]),
        frequency=cleaned["frequency"],
        timezone=cleaned["timezone"],
        recipient_ids_json=json.dumps(cleaned["recipient_ids"]),
        output_format=cleaned["output_format"],
        next_due_at=svc.compute_next_due(cleaned["frequency"], cleaned["timezone"]),
        active=True,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _schedule_to_out(schedule)


@schedules_router.get("", operation_id="reportSchedulesList")
def list_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    q = db.query(ReportSchedule).filter(
        tenant_column_criterion(ReportSchedule.tenant_id, tenant_id)
    )
    if current_user.role not in ADMIN_ROLES:
        q = q.filter(ReportSchedule.owner_id == current_user.id)
    rows = q.order_by(ReportSchedule.id.asc()).all()
    return {"schedules": [_schedule_to_out(s) for s in rows], "count": len(rows)}


@schedules_router.get("/runs", operation_id="reportSchedulesListRuns")
def list_runs(
    schedule_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    q = db.query(ReportSchedule).filter(
        tenant_column_criterion(ReportSchedule.tenant_id, tenant_id)
    )
    if current_user.role not in ADMIN_ROLES:
        q = q.filter(ReportSchedule.owner_id == current_user.id)
    owned_ids = [s.id for s in q.all()]
    runs_q = db.query(ReportRun).filter(ReportRun.schedule_id.in_(owned_ids)) if owned_ids else db.query(ReportRun).filter(False)
    if schedule_id is not None:
        _get_schedule_or_404(db, tenant_id, schedule_id)
        runs_q = runs_q.filter(ReportRun.schedule_id == schedule_id)
    rows = runs_q.order_by(ReportRun.id.desc()).limit(100).all()
    return {
        "runs": [
            {
                "id": r.id,
                "schedule_id": r.schedule_id,
                "job_id": r.job_id,
                "status": r.status,
                "recipient_count": r.recipient_count,
                "payload_format": r.payload_format,
                "has_payload": r.payload is not None,
                "error": r.error,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@schedules_router.get("/{schedule_id}", operation_id="reportSchedulesGet")
def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    schedule = _get_schedule_or_404(db, tenant_id, schedule_id)
    _refuse_unless_owner_or_admin(schedule.owner_id, current_user)
    return _schedule_to_out(schedule)


@schedules_router.patch("/{schedule_id}", operation_id="reportSchedulesPatch")
def patch_schedule(
    schedule_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    schedule = _get_schedule_or_404(db, tenant_id, schedule_id)
    _refuse_unless_owner_or_admin(schedule.owner_id, current_user)
    try:
        if "report_key" in payload:
            schedule.report_key = svc.validate_report_key(payload.get("report_key"))
        if "filters" in payload:
            schedule.filters_json = json.dumps(svc.parse_filters(payload.get("filters")))
        if "frequency" in payload:
            schedule.frequency = svc.validate_frequency(payload.get("frequency"))
        if "timezone" in payload:
            schedule.timezone = svc.validate_timezone(payload.get("timezone"))
        if "output_format" in payload:
            schedule.output_format = svc.validate_output_format(payload.get("output_format"))
    except svc.ReportPersonalizationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if "recipient_user_ids" in payload:
        recipient_ids = payload.get("recipient_user_ids")
        if not isinstance(recipient_ids, list) or any(
            isinstance(r, bool) or not isinstance(r, int) for r in recipient_ids
        ):
            raise HTTPException(status_code=422, detail="recipient_user_ids must be a list of user ids")
        for rid in recipient_ids:
            if db.query(User).filter(User.id == rid).first() is None:
                raise HTTPException(status_code=422, detail=f"recipient user {rid} does not exist")
        schedule.recipient_ids_json = json.dumps(list(recipient_ids))
    if "active" in payload:
        schedule.active = bool(payload.get("active"))
    if "frequency" in payload or "timezone" in payload:
        schedule.next_due_at = svc.compute_next_due(schedule.frequency, schedule.timezone or "UTC")
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _schedule_to_out(schedule)


@schedules_router.delete("/{schedule_id}", status_code=204, operation_id="reportSchedulesDelete")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Response:
    tenant_id = _tenant_or_401(db)
    schedule = _get_schedule_or_404(db, tenant_id, schedule_id)
    _refuse_unless_owner_or_admin(schedule.owner_id, current_user)
    db.delete(schedule)
    db.commit()
    return Response(status_code=204)


@schedules_router.post("/{schedule_id}/run-now", operation_id="reportSchedulesRunNow")
def run_now(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    tenant_id = _tenant_or_401(db)
    schedule = _get_schedule_or_404(db, tenant_id, schedule_id)
    _refuse_unless_owner_or_admin(schedule.owner_id, current_user)
    job, deduped = svc.enqueue_schedule_job(db, schedule.id)
    db.commit()
    return {"schedule_id": schedule.id, "job_id": job.id, "deduped": deduped}


@schedules_router.post("/tick", operation_id="reportSchedulesTick")
def tick(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Enqueue every due active schedule as a REPORT_RUN job.

    The tick is an explicit admin trigger, not a cron daemon and not a new
    queue: it reuses ``JobQueueService.enqueue`` (dedupe on pending) and the
    existing JobWorker executes the registered handler.
    """
    _tenant_or_401(db)
    outcomes = svc.enqueue_due_schedules(db)
    return {"enqueued": outcomes, "count": len(outcomes)}


@schedules_router.get("/runs/{run_id}/download", operation_id="reportSchedulesDownload")
def download_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    import base64 as _b64

    tenant_id = _tenant_or_401(db)
    run = db.query(ReportRun).filter(ReportRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Report run not found")
    schedule = _get_schedule_or_404(db, tenant_id, run.schedule_id)
    try:
        recipient_ids = json.loads(schedule.recipient_ids_json or "[]")
    except ValueError:
        recipient_ids = []
    is_owner_or_admin = (
        schedule.owner_id == current_user.id or current_user.role in ADMIN_ROLES
    )
    is_eligible_recipient = (
        current_user.id in recipient_ids
        and svc.role_may_view_report(current_user.role, schedule.report_key)
    )
    if not (is_owner_or_admin or is_eligible_recipient):
        # A recipient outside the report's role set gets no data — the
        # notice they received states it is not available for their role.
        raise forbidden("This report is not available for your role")
    if not run.payload:
        raise HTTPException(status_code=404, detail="Report run has no file yet")
    fmt = run.payload_format or schedule.output_format or "csv"
    filename = f"{schedule.report_key}-run-{run.id}.{fmt}"
    if fmt == "xlsx":
        return Response(
            content=_b64.b64decode(run.payload),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return Response(
        content=run.payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
