from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, ALL_ROLES, MANAGER_ROLES, WORKFORCE_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.visibility import (
    apply_visibility,
    ensure_can_view_employee,
    ensure_can_view_employee_or_403,
    is_global_reader,
)
from app.crud import crud_scheduling as crud
from app.crud.crud_employee import get_employee
from app.models.scheduling import RosterEntry, RosterVersion, ShiftSwap
from app.models.time_attendance import TimeEntry, WorkingTimeViolation
from app.models.user import User
from app.schemas.scheduling import (
    AdjustmentAction,
    AdjustmentResponse,
    AutoCreateAttendanceRequest,
    AutoCreateAttendanceResponse,
    CreateDraftFromVersionRequest,
    CreateDraftFromVersionResponse,
    DeviationsResponse,
    RosterAttendanceResponse,
    RosterDraftOut,
    RosterEntryCreate,
    RosterEntryOut,
    RosterEntryUpdate,
    AvailabilityResponse,
    RosterGenerate,
    RosterGenerateRequest,
    RosterGenerateResponse,
    RosterPublishRequest,
    RosterVersionDetailOut,
    RosterVersionOut,
    ShiftTemplateCreate,
    ShiftTemplateOut,
    ShiftTemplateUpdate,
    SwapCreate,
    SwapOut,
    VersionCompareResponse,
)
from app.services.scheduling import (
    adjust_assignment,
    apply_leave_to_problem,
    auto_create_attendance,
    create_draft_from_version,
    detect_deviations,
    generate_draft_roster,
    get_availability,
    get_draft_roster,
    get_roster_attendance,
    list_roster_versions,
    get_roster_version,
    compare_versions,
    publish_roster,
)

router = APIRouter()


def _require_template(db: Session, template_id: int):
    template = crud.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Shift template not found")
    return template


# --- Shift templates -------------------------------------------------------- #

@router.get("/shift-templates", response_model=list[ShiftTemplateOut], operation_id="schedulingListShiftTemplates")
def list_templates(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    return crud.get_templates(db, active_only=active_only)


@router.post("/shift-templates", response_model=ShiftTemplateOut, status_code=201, operation_id="schedulingCreateShiftTemplate")
def create_template(
    payload: ShiftTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if crud.get_template_by_code(db, payload.code):
        raise HTTPException(status_code=400, detail="Shift template code already exists")
    template = crud.create_template(db, payload)
    record_audit(db, current_user, "create_shift_template", "ShiftTemplate", template.id)
    db.commit()
    return template


@router.put("/shift-templates/{template_id}", response_model=ShiftTemplateOut, operation_id="schedulingUpdateSchedulingshifttemplates")
def update_template(
    template_id: int,
    payload: ShiftTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    template = _require_template(db, template_id)
    template = crud.update_template(db, template, payload)
    record_audit(db, current_user, "update_shift_template", "ShiftTemplate", template.id)
    db.commit()
    return template


# --- Roster ----------------------------------------------------------------- #

@router.get("/roster", response_model=list[RosterEntryOut], operation_id="schedulingGetRoster")
def list_roster(
    employee_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    q = db.query(RosterEntry)
    q = apply_visibility(q, RosterEntry.employee_id, current_user, db)
    if employee_id:
        ensure_can_view_employee(db, current_user, employee_id)
        q = q.filter(RosterEntry.employee_id == employee_id)
    if start:
        q = q.filter(RosterEntry.work_date >= start)
    if end:
        q = q.filter(RosterEntry.work_date <= end)
    return q.all()


@router.get("/roster/{entry_id}", response_model=RosterEntryOut, operation_id="schedulingGetSchedulingroster")
def get_roster_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    entry = crud.get_roster_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Roster entry not found")
    ensure_can_view_employee(db, current_user, entry.employee_id)
    return entry


@router.post("/roster", response_model=RosterEntryOut, status_code=201, operation_id="schedulingCreateSchedulingroster")
def create_roster_entry(
    payload: RosterEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if not get_employee(db, payload.employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    entry = crud.create_roster_entry(db, payload)
    record_audit(db, current_user, "create_roster_entry", "RosterEntry", entry.id)
    db.commit()
    return entry


@router.post("/roster/generate", response_model=list[RosterEntryOut], status_code=201, operation_id="schedulingGenerateRoster")
def generate_roster(
    payload: RosterGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    if not get_employee(db, payload.employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    _require_template(db, payload.shift_template_id)
    entries = crud.generate_roster(db, payload)
    record_audit(
        db,
        current_user,
        "generate_roster",
        "RosterEntry",
        payload.shift_template_id,
        details=f"{len(entries)} entries for employee {payload.employee_id}",
    )
    db.commit()
    return entries


@router.put("/roster/{entry_id}", response_model=RosterEntryOut, operation_id="schedulingUpdateSchedulingroster")
def update_roster_entry(
    entry_id: int,
    payload: RosterEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    entry = crud.get_roster_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Roster entry not found")
    entry = crud.update_roster_entry(db, entry, payload)
    record_audit(db, current_user, "update_roster_entry", "RosterEntry", entry.id)
    db.commit()
    return entry


# --- Solver-based roster generation (draft workflow) ------------------------ #

@router.post("/rosters/generate", response_model=RosterGenerateResponse, status_code=201, operation_id="schedulingGenerateDraftRoster")
def generate_draft_roster_endpoint(
    payload: RosterGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    """Run the solver and create a draft roster version.

    Returns the draft ID and full solver output including assignments,
    unfilled slots, weight breakdown, and constraint violations.
    """
    # Convert Pydantic models to dict for the solver
    problem = {
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat(),
        "location_code": payload.location_code,
        "employees": [e.model_dump() for e in payload.employees],
        "slots": [s.model_dump() for s in payload.slots],
        "constraints": payload.constraints.model_dump() if payload.constraints else {},
        "weights": payload.weights,
        "time_limit_seconds": payload.time_limit_seconds,
    }

    # Merge constraints into problem
    if payload.constraints:
        problem.update(payload.constraints.model_dump())

    # Leave closes days the problem's snapshot may not know about: an
    # employee on approved leave inside the window is not available, and the
    # solver input says so before the solve, not after.
    problem = apply_leave_to_problem(db, problem)

    try:
        result = generate_draft_roster(db, problem, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solver error: {str(e)}")

    # Map solver status to HTTP status
    solver_status = result.get("solver_status", "FEASIBLE")
    if solver_status == "INFEASIBLE":
        raise HTTPException(
            status_code=422,
            detail={
                "error": "solver_infeasible",
                "message": "No feasible roster could be generated with the given constraints",
                "unfilled_slots": result.get("unfilled_slots", []),
                "draft_id": result.get("draft_id"),
            },
        )
    elif result.get("timed_out"):
        # Timeout returns 200 with partial result but includes warning
        pass

    return result


@router.get("/availability", response_model=AvailabilityResponse, operation_id="schedulingGetAvailability")
def availability_endpoint(
    start_date: date | None = None,
    end_date: date | None = None,
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Per-employee availability over a window, approved leave subtracted.

    Every unavailable day carries the leave request and leave type that
    closed it, so a manager planning a roster reads the why, not just the
    no. `start_date` and `end_date` default to the two weeks from today;
    `employee_id` narrows the response to one employee subject to the
    employee-object visibility rule.
    """
    try:
        return get_availability(
            db,
            start_date or date.today(),
            end_date or (date.today() + timedelta(days=13)),
            employee_id=employee_id,
            current_user=current_user,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rosters/draft/{draft_id}", response_model=RosterDraftOut, operation_id="schedulingGetDraftRoster")
def get_draft_roster_endpoint(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    """Get a draft roster with full solver output for manager review.

    Returns assignments, unfilled slots, weight breakdown, and per-slot
    constraint information so a manager can review before publishing.
    """
    draft = get_draft_roster(db, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft roster not found")

    # Check visibility for the location
    # (For now, allow all workforce roles to view drafts)

    return draft


@router.post("/rosters/draft/{draft_id}/adjust", response_model=AdjustmentResponse, operation_id="schedulingAdjustDraftRoster")
def adjust_draft_roster_endpoint(
    draft_id: int,
    payload: AdjustmentAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    """Apply a manual assignment change to a draft and re-validate hard constraints.

    The backend re-validates all hard constraints before accepting the change.
    Returns the updated assignments, any violations, and whether the change is valid.
    """
    try:
        result = adjust_assignment(db, draft_id, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Adjustment error: {str(e)}")

    # Record audit for the manual adjustment
    record_audit(
        db,
        current_user,
        "adjust_draft_roster",
        "RosterVersion",
        draft_id,
        details=f"Manual adjustment: {payload.action} slot {payload.slot_instance_id} -> employee {payload.employee_id}",
    )
    db.commit()

    return result


@router.post("/rosters/publish", response_model=RosterVersionOut, operation_id="schedulingPublishDraftRoster")
def publish_roster_endpoint(
    payload: RosterPublishRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    """Publish a draft roster as an immutable version.

    Re-validates all hard constraints before publishing. Emits shift.published event.
    Idempotency key support for safe retries.
    """
    # Check idempotency
    if idempotency_key:
        # Check if we've already processed this key
        existing = db.query(RosterVersion).filter(
            RosterVersion.notes.like(f'%"{idempotency_key}"%')
        ).first()
        if existing:
            # Return the existing published version
            _attach_version_counts(db, existing)
            return existing

    try:
        published = publish_roster(
            db,
            payload.draft_id,
            current_user,
            publish_at=payload.publish_at,
            notify=payload.notify,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publish error: {str(e)}")

    # Store idempotency key in notes if provided
    if idempotency_key:
        try:
            import json
            notes = json.loads(published.notes) if published.notes else {}
            notes["idempotency_key"] = idempotency_key
            published.notes = json.dumps(notes)
            db.add(published)
            db.commit()
            db.refresh(published)
        except Exception:
            pass

    # The row carries no count columns; the contract's RosterVersion
    # promises entry_count/unfilled_count, so report what the publish
    # wrote, counted the way the list/detail reads count them.
    _attach_version_counts(db, published)

    return published


def _attach_version_counts(db: Session, version: RosterVersion) -> None:
    """Report the entries and unfilled slots of a published version.

    The counts are window-scoped the way the list and detail reads count
    them: entries whose work date falls in the version's period.
    """
    import json

    version.entry_count = (
        db.query(RosterEntry)
        .filter(
            RosterEntry.work_date >= version.period_start,
            RosterEntry.work_date <= version.period_end,
        )
        .count()
    )
    try:
        stored = json.loads(version.notes) if version.notes else {}
        version.unfilled_count = len(
            stored.get("result", {}).get("unfilled_slots", [])
        )
    except (ValueError, AttributeError):
        version.unfilled_count = 0


# --- Roster Versioning ------------------------------------------------------ #

@router.get("/rosters/versions", response_model=dict, operation_id="schedulingListRosterVersions")
def list_roster_versions_endpoint(
    location_code: str | None = None,
    status: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """List roster versions with filters and pagination.

    Filters:
    - location_code: Filter by location
    - status: Filter by status (draft, published, superseded)
    - period_start: Filter versions with period_start >= this date
    - period_end: Filter versions with period_end <= this date
    - page, page_size: Pagination
    """
    result = list_roster_versions(
        db,
        location_code=location_code,
        status=status,
        period_start=period_start,
        period_end=period_end,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/rosters/versions/{version_id}", response_model=RosterVersionDetailOut, operation_id="schedulingGetRosterVersion")
def get_roster_version_endpoint(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Get a roster version with all entries and solver data."""
    version = get_roster_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Roster version not found")

    # Check visibility
    if version.get("location_code"):
        # Could add visibility check here
        pass

    return version


@router.get("/rosters/versions/{version_id}/compare", response_model=VersionCompareResponse, operation_id="schedulingCompareRosterVersions")
def compare_roster_versions_endpoint(
    version_id: int,
    base_version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Compare two roster versions and return diffs.

    Query params:
    - base_version_id: The version to compare against (required)
    """
    try:
        result = compare_versions(db, version_id, base_version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison error: {str(e)}")

    return result


@router.post("/rosters/versions/{version_id}/draft", response_model=CreateDraftFromVersionResponse, operation_id="schedulingCreateDraftFromVersion")
def create_draft_from_version_endpoint(
    version_id: int,
    payload: CreateDraftFromVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    """Create a new draft roster from a published version.

    The new draft copies the problem from the published version and allows
    optional new period dates. This enables rolling forward a published roster
    to a new period with the same constraints and demand.
    """
    if version_id <= 0:
        raise HTTPException(status_code=422, detail="Invalid version_id")

    version = db.query(RosterVersion).filter(RosterVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Roster version not found")
    if version.status != "published":
        raise HTTPException(status_code=409, detail=f"Can only create draft from published version (current: {version.status})")

    try:
        result = create_draft_from_version(
            db,
            version_id,
            current_user,
            new_period_start=payload.new_period_start,
            new_period_end=payload.new_period_end,
            notes=payload.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Draft creation error: {str(e)}")

    return result


# --- Shift swaps ------------------------------------------------------------ #

@router.get("/swaps", response_model=list[SwapOut], operation_id="schedulingListSchedulingswaps")
def list_swaps(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    q = db.query(ShiftSwap)
    # ShiftSwap has requester_id and target_id; filter by either for visibility
    # A user can see swaps where they are the requester or target (if linked to an employee)
    if current_user.employee_id:
        q = q.filter(
            (ShiftSwap.requester_id == current_user.employee_id)
            | (ShiftSwap.target_id == current_user.employee_id)
        )
    else:
        # No employee link: only a global reader can see all
        if not is_global_reader(current_user):
            q = q.filter(ShiftSwap.id == -1)  # empty result
    if status:
        q = q.filter(ShiftSwap.status == status)
    return q.order_by(ShiftSwap.id.desc()).all()


@router.post("/swaps", response_model=SwapOut, status_code=201, operation_id="schedulingCreateSwap")
def create_swap(
    payload: SwapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    entry = crud.get_roster_entry(db, payload.roster_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Roster entry not found")
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="User is not linked to an employee")
    swap = crud.create_swap(db, current_user.employee_id, payload)
    record_audit(db, current_user, "request_shift_swap", "ShiftSwap", swap.id)
    db.commit()
    return swap


@router.post("/swaps/{swap_id}/approve", response_model=SwapOut, operation_id="schedulingApproveSwap")
def approve_swap(
    swap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    swap = crud.get_swap(db, swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="Shift swap not found")
    # A manager decides the swaps raised by their own reporting line and
    # nothing else.
    ensure_can_view_employee_or_403(db, current_user, swap.requester_id)
    swap = crud.decide_swap(db, swap, approved=True, decided_by=current_user.id)
    record_audit(db, current_user, "approve_shift_swap", "ShiftSwap", swap.id)
    db.commit()
    return swap


@router.post("/swaps/{swap_id}/reject", response_model=SwapOut, operation_id="schedulingCreateSchedulingswapsreject")
def reject_swap(
    swap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    swap = crud.get_swap(db, swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="Shift swap not found")
    # The same reporting-line scope as the approval above.
    ensure_can_view_employee_or_403(db, current_user, swap.requester_id)
    swap = crud.decide_swap(db, swap, approved=False, decided_by=current_user.id)
    record_audit(db, current_user, "reject_shift_swap", "ShiftSwap", swap.id)
    db.commit()
    return swap


# --- Attendance Integration --------------------------------------------------- #

from app.models.time_attendance import TimeEntry, WorkingTimeViolation
from app.schemas.scheduling import (
    RosterAttendanceResponse,
    AutoCreateAttendanceRequest,
    AutoCreateAttendanceResponse,
    DeviationsResponse,
)
from app.services.scheduling import (
    get_roster_attendance,
    auto_create_attendance,
    detect_deviations,
)


@router.get("/rosters/{version_id}/attendance", response_model=RosterAttendanceResponse, operation_id="schedulingGetRosterAttendance")
def get_roster_attendance_endpoint(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Get attendance for a published roster version.

    Returns all roster entries with their linked time entries (if any),
    plus a summary of matched/missing/extra entries.
    """
    try:
        result = get_roster_attendance(db, version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Attendance error: {str(e)}")

    return result


@router.post("/rosters/{version_id}/attendance/auto-create", response_model=AutoCreateAttendanceResponse, operation_id="schedulingAutoCreateAttendance")
def auto_create_attendance_endpoint(
    version_id: int,
    payload: AutoCreateAttendanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    """Auto-create time entries from published roster (kiosk mode).

    Creates clock-in/clock-out records for all roster entries in the version
    based on their scheduled start/end times. Skips entries that already
    have a time entry for the same employee/date.
    """
    version = db.query(RosterVersion).filter(RosterVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Roster version not found")
    if version.status != "published":
        raise HTTPException(status_code=409, detail=f"Can only auto-create attendance for published version (current: {version.status})")

    try:
        tz = payload.tz or "UTC"
        try:
            ZoneInfo(tz)
        except ZoneInfoNotFoundError:
            raise HTTPException(status_code=422, detail=f"Unknown time zone: {tz!r}")
        result = auto_create_attendance(db, version_id, current_user, source=payload.source, tz=tz)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-create error: {str(e)}")

    return result


@router.get("/rosters/{version_id}/attendance/deviations", response_model=DeviationsResponse, operation_id="schedulingGetRosterDeviations")
def get_roster_deviations_endpoint(
    version_id: int,
    grace_minutes: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Get deviations (working time violations) for a published roster version.

    Compares actual time entries against scheduled roster entries and returns:
    - Early arrival (clock_in < roster.start_time - grace)
    - Late arrival (clock_in > roster.start_time + grace)
    - Early departure (clock_out < roster.end_time - grace)
    - Late departure (clock_out > roster.end_time + grace)
    - Missing entry (no time entry for roster entry)
    - Extra entry (time entry without matching roster entry)

    Query params:
    - grace_minutes: Grace period in minutes (default: 5)
    """
    try:
        result = detect_deviations(db, version_id, grace_minutes=grace_minutes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deviations error: {str(e)}")

    return result
