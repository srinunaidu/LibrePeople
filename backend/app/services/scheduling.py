"""Scheduling service: solver orchestration, persistence and publish flow."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.core.dst import wall_to_utc
from app.models.employee import Employee
from app.models.leave import LeaveRequest, LeaveType
from app.models.scheduling import RosterEntry, RosterVersion, ShiftTemplate, ShiftSwap
from app.models.user import User
from app.services.solver import RosterSolver, solve as solve_roster_problem, validate_solution, _to_date as solver_to_date, _shift_minutes, _shift_end_abs

PUBLISHED_EVENTS: List[Dict[str, Any]] = []


def _to_date(v):
    return solver_to_date(v)


def _json_serializable(obj: Any) -> Any:
    """Convert an object to a JSON-serializable form."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_serializable(v) for v in obj]
    return obj


# --- Leave-to-roster handoff ------------------------------------------------- #

APPROVED_LEAVE_STATUS = "Approved"


def approved_leave_blocks(
    db: Session,
    start_date,
    end_date,
    employee_ids: Optional[List[int]] = None,
) -> Dict[int, List[Dict[str, Any]]]:
    """The approved leave that overlaps the window, one entry per blocked day.

    Only ``Approved`` requests block availability: a pending request is not
    leave yet, and a rejected or cancelled request never was. Every blocked
    day carries the leave reference so the solver input, the draft problem
    and the availability endpoint all show *why* a day is not available.

    ``employee_ids`` narrows the read; ``None`` means every employee.
    """
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    query = (
        db.query(LeaveRequest, LeaveType.code)
        .join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)
        .filter(LeaveRequest.status == APPROVED_LEAVE_STATUS)
        .filter(LeaveRequest.start_date <= end_date)
        .filter(LeaveRequest.end_date >= start_date)
    )
    if employee_ids is not None:
        if not employee_ids:
            return {}
        query = query.filter(LeaveRequest.employee_id.in_(employee_ids))

    blocks: Dict[int, List[Dict[str, Any]]] = {}
    for request, leave_type_code in query.all():
        window_start = max(request.start_date, start_date)
        window_end = min(request.end_date, end_date)
        day = window_start
        while day <= window_end:
            blocks.setdefault(request.employee_id, []).append({
                "date": day.isoformat(),
                "leave_request_id": request.id,
                "leave_type_id": request.leave_type_id,
                "leave_type_code": leave_type_code,
            })
            day = day + timedelta(days=1)
    return blocks


def apply_leave_to_problem(db: Session, problem: Dict[str, Any]) -> Dict[str, Any]:
    """Subtract approved leave from a solver problem for the problem's window.

    The call is the one place leave reaches the solver: an employee on
    approved leave is added to ``unavailable_dates`` for every day of the
    leave inside the problem's window, whatever the caller's own
    unavailability asked for, and the leave references are recorded on the
    employee as ``leave_blocks`` so a draft problem shows why a day closed.

    Mutates and returns ``problem``.
    """
    start_date = problem.get("start_date")
    end_date = problem.get("end_date")
    if not start_date or not end_date:
        return problem

    employees = problem.get("employees") or []
    employee_ids = []
    for e in employees:
        if isinstance(e, dict):
            eid = e.get("id")
        else:
            eid = getattr(e, "id", None)
            if eid is not None and hasattr(e, "model_dump"):
                e = e.model_dump()
            e = dict(e)
        if eid is not None:
            employee_ids.append(eid)

    blocks = approved_leave_blocks(db, start_date, end_date, employee_ids=employee_ids)
    for e in employees:
        if not isinstance(e, dict):
            continue
        mine = blocks.get(e.get("id"), [])
        if not mine:
            continue
        existing = {d.isoformat() if hasattr(d, "isoformat") else str(d)
                    for d in (e.get("unavailable_dates") or [])}
        leave_days = [b["date"] for b in mine]
        e["unavailable_dates"] = sorted(existing | set(leave_days))
        e["leave_blocks"] = sorted(
            mine + [b for b in (e.get("leave_blocks") or []) if b not in mine],
            key=lambda b: (b["date"], b["leave_request_id"]),
        )
    return problem


def leave_violations(db: Session, assignments: List[Dict[str, Any]]) -> List[str]:
    """Assignments that fall on an employee's approved leave.

    The solver excludes leave days before it solves, and a manual adjustment
    re-checks the problem's ``unavailable_dates``, but the database is the
    last word: a leave approved between generation and publish is caught
    here, on the way to a published roster.
    """
    if not assignments:
        return []
    dates = {date.fromisoformat(a["date"]) if isinstance(a["date"], str) else a["date"]
             for a in assignments}
    window_start, window_end = min(dates), max(dates)
    employee_ids = [a["employee_id"] for a in assignments]
    blocks = approved_leave_blocks(db, window_start, window_end, employee_ids=employee_ids)
    violations: List[str] = []
    for a in assignments:
        d = date.fromisoformat(a["date"]) if isinstance(a["date"], str) else a["date"]
        for b in blocks.get(a["employee_id"], []):
            if b["date"] == d.isoformat():
                violations.append(
                    f"availability: employee {a['employee_id']} is on approved "
                    f"leave request {b['leave_request_id']} on {d.isoformat()}"
                )
    return violations


def build_problem_from_db(
    db: Session,
    start_date,
    end_date,
    location_id=None,
    employees=None,
) -> Dict[str, Any]:
    """Build a solver problem dict from DB data for the window.

    The employees come from the caller when the roster builder has already
    chosen them, and from the active employee directory otherwise. Either
    way the approved leave between ``start_date`` and ``end_date`` is
    subtracted: an employee on approved leave is not available, whatever the
    caller's snapshot said. The demand (slots) stays the caller's: the
    coverage the roster has to meet is not stored on the employee table.
    """
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    if employees is not None:
        problem_employees = []
        for e in employees:
            if hasattr(e, "model_dump"):
                e = e.model_dump()
            problem_employees.append(dict(e))
    else:
        problem_employees = [
            {
                "id": emp.id,
                "skills": [],
                "max_hours_per_day": 8.0,
                "max_hours_per_week": 40.0,
                "locations": [location_id] if location_id else [],
                "unavailable_dates": [],
                "preferences": {},
                "cost_per_slot": 0.0,
                "night_ok": True,
            }
            for emp in db.query(Employee).filter(Employee.status == "Active").all()
        ]

    problem = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "location_code": location_id,
        "employees": problem_employees,
        "slots": [],
    }
    return apply_leave_to_problem(db, problem)


def get_availability(
    db: Session,
    start_date,
    end_date,
    *,
    employee_id: Optional[int] = None,
    current_user: User,
) -> Dict[str, Any]:
    """Per-employee availability over a window, leave subtracted.

    A day is ``unavailable`` when an approved leave request covers it, always
    with the leave reference so the caller can follow the why. Pending and
    rejected leave blocks nothing. Visibility is the employee-object rule the
    rest of the platform runs on: a manager sees their reporting line, an
    associate sees themselves, HR sees everyone.
    """
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    if employee_id is not None:
        ensure_can_view_employee(db, current_user, employee_id)
        row = db.query(Employee.id).filter(Employee.id == employee_id).first()
        if not row:
            raise ValueError("Employee not found")
        employee_ids = [employee_id]
    else:
        query = db.query(Employee.id).filter(Employee.status == "Active")
        query = apply_visibility(query, Employee.id, current_user, db)
        employee_ids = [row[0] for row in query.order_by(Employee.id).all()]

    blocks = approved_leave_blocks(db, start_date, end_date, employee_ids=employee_ids)

    # The references each employee's blocks point at, for the record.
    leave_ids = sorted({
        b["leave_request_id"]
        for b in (block for bs in blocks.values() for block in bs)
    })
    refs: Dict[int, Dict[str, Any]] = {}
    if leave_ids:
        for request in db.query(LeaveRequest).filter(LeaveRequest.id.in_(leave_ids)).all():
            refs[request.id] = {
                "leave_request_id": request.id,
                "leave_type_id": request.leave_type_id,
                "start_date": max(request.start_date, start_date),
                "end_date": min(request.end_date, end_date),
            }
        type_ids = sorted({r["leave_type_id"] for r in refs.values()})
        for type_id, code in (
            db.query(LeaveType.id, LeaveType.code).filter(LeaveType.id.in_(type_ids)).all()
        ):
            for r in refs.values():
                if r["leave_type_id"] == type_id:
                    r["leave_type_code"] = code

    window_days: List[str] = []
    day = start_date
    while day <= end_date:
        window_days.append(day.isoformat())
        day = day + timedelta(days=1)

    items = []
    for eid in employee_ids:
        mine = blocks.get(eid, [])
        blocked_days = {b["date"] for b in mine}
        refs_for_emp = []
        for rid in sorted({b["leave_request_id"] for b in mine}):
            r = refs.get(rid, {})
            refs_for_emp.append({
                "leave_request_id": rid,
                "leave_type_id": r.get("leave_type_id"),
                "leave_type_code": r.get("leave_type_code"),
                "start_date": r.get("start_date"),
                "end_date": r.get("end_date"),
                "days": sum(1 for b in mine if b["leave_request_id"] == rid),
            })
        items.append({
            "employee_id": eid,
            "available_dates": [d for d in window_days if d not in blocked_days],
            "unavailable_dates": sorted(mine, key=lambda b: (b["date"], b["leave_request_id"])),
            "leave_requests": refs_for_emp,
        })

    return {
        "start_date": start_date,
        "end_date": end_date,
        "employees": items,
    }


def generate_draft_roster(
    db: Session,
    problem: Dict[str, Any],
    current_user: User,
) -> Dict[str, Any]:
    """Run the solver, store a draft roster version, and return the result."""
    solver = RosterSolver(
        time_limit_seconds=problem.get("time_limit_seconds", 60.0),
        weights=problem.get("weights"),
        min_rest_hours=problem.get("min_rest_hours", 11.0),
        max_consecutive_days=problem.get("max_consecutive_days", 6),
    )
    result = solver.solve(problem)

    start_date = problem.get("start_date")
    end_date = problem.get("end_date")
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    draft = RosterVersion(
        location_code=problem.get("location_code"),
        period_start=start_date,
        period_end=end_date,
        status="draft",
        solver_status=result.get("solver_status"),
        notes=json.dumps({
            "problem": _json_serializable(problem),
            "result": _json_serializable(result),
        }),
    )
    db.add(draft)
    # The draft creation is a mutation: the audit row belongs to the same
    # transaction as the version row it describes.
    from app.core.audit import record_audit
    record_audit(
        db,
        current_user,
        "generate_draft_roster",
        "RosterVersion",
        None,
        details=(
            f"Draft roster for {problem.get('location_code')} "
            f"{start_date} to {end_date}, solver {result.get('solver_status')}"
        ),
    )
    db.commit()
    db.refresh(draft)

    return {
        "draft_id": draft.id,
        "status": result.get("status"),
        "solver_status": result.get("solver_status"),
        "timed_out": result.get("timed_out"),
        "objective_value": result.get("objective_value"),
        "weight_breakdown": result.get("weight_breakdown"),
        "assignments": result.get("assignments"),
        "roster": result.get("roster"),
        "unfilled_slots": result.get("unfilled_slots"),
        "unfilled": result.get("unfilled"),
        "input_hash": result.get("input_hash"),
    }


def get_draft_roster(db: Session, draft_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a draft roster with full solver output."""
    draft = db.query(RosterVersion).filter(RosterVersion.id == draft_id).first()
    if not draft:
        return None

    try:
        stored = json.loads(draft.notes) if draft.notes else {}
    except json.JSONDecodeError:
        stored = {}

    problem = stored.get("problem", {})
    result = stored.get("result", {})

    return {
        "draft_id": draft.id,
        "location_code": draft.location_code,
        "period_start": draft.period_start.isoformat() if draft.period_start else None,
        "period_end": draft.period_end.isoformat() if draft.period_end else None,
        "status": draft.status,
        "solver_status": draft.solver_status,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
        "problem": problem,
        "result": result,
        "assignments": result.get("assignments", []),
        "roster": result.get("roster", []),
        "unfilled_slots": result.get("unfilled_slots", []),
        "unfilled": result.get("unfilled", []),
        "weight_breakdown": result.get("weight_breakdown", {}),
        "objective_value": result.get("objective_value"),
        "input_hash": result.get("input_hash"),
    }


def adjust_assignment(
    db: Session,
    draft_id: int,
    adjustment: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply a manual assignment change to a draft and re-validate hard constraints."""
    draft = db.query(RosterVersion).filter(RosterVersion.id == draft_id).first()
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")

    if draft.status != "draft":
        raise ValueError(f"Cannot adjust a {draft.status} roster")

    try:
        stored = json.loads(draft.notes) if draft.notes else {}
    except json.JSONDecodeError:
        stored = {}

    problem = stored.get("problem", {})
    result = stored.get("result", {})

    assignments = result.get("assignments", []).copy()
    slot_instance_id = adjustment.get("slot_instance_id")
    employee_id = adjustment.get("employee_id")
    action = adjustment.get("action", "reassign")

    if not slot_instance_id:
        raise ValueError("slot_instance_id is required")

    assignment_idx = None
    for i, a in enumerate(assignments):
        if a.get("slot_instance") == slot_instance_id:
            assignment_idx = i
            break

    if action == "unassign":
        if assignment_idx is not None:
            assignments.pop(assignment_idx)
        else:
            raise ValueError(f"No assignment found for slot {slot_instance_id}")
    elif action == "assign":
        if employee_id is None:
            raise ValueError("employee_id required for assign action")
        slot = None
        for sl in problem.get("slots", []):
            hc = int(sl.get("headcount", 1) or 1)
            for k in range(hc):
                inst_id = f"{sl.get('id', len(assignments))}__{k}"
                if inst_id == slot_instance_id:
                    slot = sl
                    break
            if slot:
                break
        if not slot:
            raise ValueError(f"Slot instance {slot_instance_id} not found")

        emp = None
        for e in problem.get("employees", []):
            if e.get("id") == employee_id:
                emp = e
                break
        if not emp:
            raise ValueError(f"Employee {employee_id} not in problem")

        new_assignment = {
            "slot_instance": slot_instance_id,
            "base_slot_id": slot.get("id"),
            "slot_id": slot.get("id"),
            "employee_id": employee_id,
            "date": slot.get("date"),
            "location": slot.get("location", slot.get("location_id")),
            "role": slot.get("role", slot.get("role_code")),
            "start": slot.get("start", slot.get("start_time", "09:00")),
            "end": slot.get("end", slot.get("end_time", "17:00")),
            "is_night": bool(slot.get("is_night", False)),
        }
        if assignment_idx is not None:
            assignments[assignment_idx] = new_assignment
        else:
            assignments.append(new_assignment)
    elif action == "reassign":
        if employee_id is None:
            raise ValueError("employee_id required for reassign action")
        if assignment_idx is not None:
            assignments[assignment_idx]["employee_id"] = employee_id
        else:
            raise ValueError(f"No existing assignment for slot {slot_instance_id}")
    else:
        raise ValueError(f"Unknown action: {action}")

    violations = validate_solution(problem, assignments)

    result["assignments"] = assignments
    result["roster"] = assignments
    result["violations"] = violations

    slot_instances = []
    for s in problem.get("slots", []):
        hc = int(s.get("headcount", 1) or 1)
        for k in range(hc):
            slot_instances.append({
                "instance_id": f"{s.get('id', len(slot_instances))}__{k}",
                "base_id": s.get("id"),
                "date": s.get("date"),
                "location": s.get("location", s.get("location_id")),
                "role": s.get("role", s.get("role_code")),
                "skill": s.get("skill", s.get("required_skill", s.get("required_skills"))),
                "start": s.get("start", s.get("start_time", "09:00")),
                "end": s.get("end", s.get("end_time", "17:00")),
                "is_night": bool(s.get("is_night", False)),
                "required": bool(s.get("required", False)),
            })

    assigned_instances = {a["slot_instance"] for a in assignments}
    unfilled_instances = [sl for sl in slot_instances if sl["instance_id"] not in assigned_instances]
    unfilled_groups = {}
    for sl in unfilled_instances:
        unfilled_groups.setdefault(sl["base_id"], []).append(sl)

    unfilled_slots = []
    for base_id, sls in unfilled_groups.items():
        sl0 = sls[0]
        cause = "manual_adjustment"
        unfilled_slots.append({
            "slot_id": base_id,
            "date": sl0["date"].isoformat() if hasattr(sl0["date"], "isoformat") else str(sl0["date"]),
            "location": sl0["location"],
            "role": sl0["role"],
            "headcount": len(sls),
            "cause": cause,
            "blocking_constraint": cause,
            "constraint": cause,
        })
    result["unfilled_slots"] = unfilled_slots
    result["unfilled"] = unfilled_slots

    draft.notes = json.dumps({"problem": problem, "result": _json_serializable(result)})
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return {
        "draft_id": draft.id,
        "assignments": assignments,
        "unfilled_slots": unfilled_slots,
        "violations": violations,
        "valid": len(violations) == 0,
    }


def publish_roster(
    db: Session,
    draft_id: int,
    current_user: User,
    publish_at: Optional[datetime] = None,
    notify: bool = True,
) -> RosterVersion:
    """Publish a draft roster as an immutable version."""
    draft = db.query(RosterVersion).filter(RosterVersion.id == draft_id).first()
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")

    if draft.status != "draft":
        raise ValueError(f"Cannot publish a {draft.status} roster")

    try:
        stored = json.loads(draft.notes) if draft.notes else {}
    except json.JSONDecodeError:
        stored = {}

    problem = stored.get("problem", {})
    result = stored.get("result", {})
    assignments = result.get("assignments", [])

    violations = validate_solution(problem, assignments)
    # The database is the last word on availability: leave approved between
    # generation and publish closes the day even if the problem snapshot did
    # not know about it.
    violations = violations + leave_violations(db, assignments)
    if violations:
        raise ValueError(f"Hard constraint violations: {', '.join(violations)}")

    published_at = publish_at or datetime.now(timezone.utc)
    published = RosterVersion(
        location_code=draft.location_code,
        period_start=draft.period_start,
        period_end=draft.period_end,
        status="published",
        published_by=current_user.id,
        published_at=published_at,
        solver_status=draft.solver_status,
        notes=json.dumps({
            "problem": problem,
            "result": _json_serializable(result),
            "published_by": current_user.id,
            "published_at": published_at.isoformat(),
        }),
    )
    db.add(published)

    draft.status = "superseded"
    db.add(draft)

    for a in assignments:
        work_date = a["date"]
        if isinstance(work_date, str):
            work_date = date.fromisoformat(work_date)
        entry = RosterEntry(
            employee_id=a["employee_id"],
            work_date=work_date,
            shift_template_id=None,
            start_time=a["start"],
            end_time=a["end"],
            is_night=a.get("is_night", False),
            status="Confirmed",
            notes=f"Published from draft {draft_id}",
        )
        db.add(entry)

    from app.core.audit import record_audit
    record_audit(
        db,
        current_user,
        "publish_roster",
        "RosterVersion",
        published.id,
        details=f"Published roster for {draft.location_code} {draft.period_start} to {draft.period_end}",
    )

    db.commit()
    db.refresh(published)

    evt = {
        "event_type": "shift.published",
        "roster_version": str(published.id),
        "location_code": published.location_code,
        "period_start": published.period_start.isoformat() if published.period_start else None,
        "period_end": published.period_end.isoformat() if published.period_end else None,
        "published_by": str(published.published_by) if published.published_by else None,
        "published_at": published.published_at.isoformat() if published.published_at else None,
        "assignments_count": len(assignments),
        "unfilled_count": len(result.get("unfilled_slots", [])),
    }
    PUBLISHED_EVENTS.append(evt)

    return published


def generate_roster(db: Session, problem: Dict[str, Any], current_user=None) -> Dict[str, Any]:
    """Run the solver and persist draft roster entries. Returns solver result."""
    result = solve_roster_problem(problem)
    # Persist entries for assignments if possible
    try:
        for a in result.get("assignments", []):
            tmpl_id = a.get("shift_template_id")
            if tmpl_id is None:
                # find a template? skip persistence if none
                continue
            entry = RosterEntry(
                employee_id=a["employee_id"],
                work_date=_to_date(a["date"]),
                shift_template_id=tmpl_id,
                start_time=a.get("start", "09:00"),
                end_time=a.get("end", "17:00"),
                is_night=bool(a.get("is_night", False)),
                status="Scheduled",
            )
            db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
    # audit
    try:
        from app.core.audit import record_audit
        if current_user is not None:
            record_audit(db, current_user, "generate_roster", "Roster", None, details=f"solver {result.get('status')}")
            db.commit()
    except Exception:
        pass
    return result


def validate_roster(db: Session, assignments, problem) -> List[str]:
    return validate_solution(problem, assignments)


def publish_roster_legacy(db: Session, version_data: Dict[str, Any], current_user=None) -> RosterVersion:
    """Create an immutable published roster version and emit shift.published."""
    rv = RosterVersion(
        location_code=version_data.get("location_code") or version_data.get("location_id"),
        period_start=_to_date(version_data["start_date"]) if "start_date" in version_data else _to_date(version_data.get("period_start")),
        period_end=_to_date(version_data["end_date"]) if "end_date" in version_data else _to_date(version_data.get("period_end")),
        status="published",
        published_by=getattr(current_user, "id", None),
        published_at=datetime.now(timezone.utc),
        solver_status=version_data.get("solver_status"),
    )
    db.add(rv)
    db.commit()
    db.refresh(rv)
    # emit event (in-process record + audit)
    evt = {
        "event_type": "shift.published",
        "roster_version": str(rv.id),
        "location_code": rv.location_code,
        "published_by": str(rv.published_by) if rv.published_by else None,
        "published_at": rv.published_at.isoformat() if rv.published_at else None,
    }
    PUBLISHED_EVENTS.append(evt)
    try:
        from app.core.audit import record_audit
        if current_user is not None:
            record_audit(db, current_user, "publish_roster", "RosterVersion", rv.id, details="shift.published")
            db.commit()
    except Exception:
        pass
    return rv


def revalidate_assignment(db: Session, entry_id: int, new_data: Dict[str, Any]) -> List[str]:
    """Re-validate hard constraints for a manual adjustment. Returns violations."""
    return []


# --- Roster Versioning ---

def list_roster_versions(
    db: Session,
    *,
    location_code: Optional[str] = None,
    status: Optional[str] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    """List roster versions with filters and pagination."""
    query = db.query(RosterVersion)

    if location_code:
        query = query.filter(RosterVersion.location_code == location_code)
    if status:
        query = query.filter(RosterVersion.status == status)
    if period_start:
        query = query.filter(RosterVersion.period_start >= period_start)
    if period_end:
        query = query.filter(RosterVersion.period_end <= period_end)

    query = query.order_by(RosterVersion.id.desc())

    total = query.count()
    total_pages = (total + page_size - 1) // page_size

    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # Build response items with counts
    result_items = []
    for rv in items:
        entry_count = db.query(RosterEntry).filter(
            RosterEntry.work_date >= rv.period_start,
            RosterEntry.work_date <= rv.period_end,
        ).count()

        unfilled_count = 0
        if rv.notes:
            try:
                stored = json.loads(rv.notes)
                result = stored.get("result", {})
                unfilled_count = len(result.get("unfilled_slots", []))
            except (json.JSONDecodeError, AttributeError):
                pass

        result_items.append({
            "id": rv.id,
            "location_code": rv.location_code,
            "period_start": rv.period_start,
            "period_end": rv.period_end,
            "status": rv.status,
            "published_by": rv.published_by,
            "published_at": rv.published_at,
            "solver_status": rv.solver_status,
            "created_at": rv.created_at,
            "entry_count": entry_count,
            "unfilled_count": unfilled_count,
        })

    return {
        "items": result_items,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


def get_roster_version(db: Session, version_id: int) -> Optional[Dict[str, Any]]:
    """Get a roster version with all entries and solver data."""
    rv = db.query(RosterVersion).filter(RosterVersion.id == version_id).first()
    if not rv:
        return None

    entries = db.query(RosterEntry).filter(
        RosterEntry.work_date >= rv.period_start,
        RosterEntry.work_date <= rv.period_end,
    ).all()

    problem = {}
    result = {}
    assignments = []
    unfilled_slots = []
    weight_breakdown = None
    objective_value = None
    input_hash = ""

    if rv.notes:
        try:
            stored = json.loads(rv.notes)
            problem = stored.get("problem", {})
            result = stored.get("result", {})
            assignments = result.get("assignments", [])
            unfilled_slots = result.get("unfilled_slots", [])
            weight_breakdown = result.get("weight_breakdown")
            objective_value = result.get("objective_value")
            input_hash = result.get("input_hash", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    return {
        "id": rv.id,
        "location_code": rv.location_code,
        "period_start": rv.period_start,
        "period_end": rv.period_end,
        "status": rv.status,
        "published_by": rv.published_by,
        "published_at": rv.published_at,
        "solver_status": rv.solver_status,
        "created_at": rv.created_at,
        "entry_count": len(entries),
        "unfilled_count": len(unfilled_slots),
        "entries": entries,
        "problem": problem,
        "result": result,
        "assignments": assignments,
        "unfilled_slots": unfilled_slots,
        "weight_breakdown": weight_breakdown,
        "objective_value": objective_value,
        "input_hash": input_hash,
    }


def compare_versions(
    db: Session,
    version_id: int,
    base_version_id: int,
) -> Dict[str, Any]:
    """Compare two roster versions and return diffs."""
    version = db.query(RosterVersion).filter(RosterVersion.id == version_id).first()
    base_version = db.query(RosterVersion).filter(RosterVersion.id == base_version_id).first()

    if not version or not base_version:
        raise ValueError("One or both versions not found")

    # Get entries for both versions
    version_entries = db.query(RosterEntry).filter(
        RosterEntry.work_date >= version.period_start,
        RosterEntry.work_date <= version.period_end,
    ).all()

    base_entries = db.query(RosterEntry).filter(
        RosterEntry.work_date >= base_version.period_start,
        RosterEntry.work_date <= base_version.period_end,
    ).all()

    # Create lookup maps by (employee_id, work_date, start_time, end_time)
    def entry_key(e: RosterEntry):
        return (e.employee_id, e.work_date.isoformat(), e.start_time, e.end_time)

    version_map = {entry_key(e): e for e in version_entries}
    base_map = {entry_key(e): e for e in base_entries}

    added = []
    removed = []
    changed = []

    # Find added and changed
    for key, entry in version_map.items():
        if key not in base_map:
            added.append({
                "type": "added",
                "entry": entry,
                "base_entry": None,
                "changes": {},
            })
        else:
            base_entry = base_map[key]
            changes = {}
            if entry.start_time != base_entry.start_time:
                changes["start_time"] = {"from": base_entry.start_time, "to": entry.start_time}
            if entry.end_time != base_entry.end_time:
                changes["end_time"] = {"from": base_entry.end_time, "to": entry.end_time}
            if entry.shift_template_id != base_entry.shift_template_id:
                changes["shift_template_id"] = {"from": base_entry.shift_template_id, "to": entry.shift_template_id}
            if entry.is_night != base_entry.is_night:
                changes["is_night"] = {"from": base_entry.is_night, "to": entry.is_night}
            if entry.status != base_entry.status:
                changes["status"] = {"from": base_entry.status, "to": entry.status}
            if changes:
                changed.append({
                    "type": "changed",
                    "entry": entry,
                    "base_entry": base_entry,
                    "changes": changes,
                })

    # Find removed
    for key, base_entry in base_map.items():
        if key not in version_map:
            removed.append({
                "type": "removed",
                "entry": None,
                "base_entry": base_entry,
                "changes": {},
            })

    summary = {
        "added": len(added),
        "removed": len(removed),
        "changed": len(changed),
        "unchanged": len(version_entries) - len(added) - len(changed),
    }

    return {
        "version_id": version_id,
        "base_version_id": base_version_id,
        "added": added,
        "removed": removed,
        "changed": changed,
        "summary": summary,
    }


def create_draft_from_version(
    db: Session,
    version_id: int,
    current_user,
    new_period_start: Optional[date] = None,
    new_period_end: Optional[date] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new draft roster from a published version."""
    version = db.query(RosterVersion).filter(RosterVersion.id == version_id).first()
    if not version:
        raise ValueError(f"Version {version_id} not found")

    if version.status != "published":
        raise ValueError(f"Can only create draft from published version (current: {version.status})")

    period_start = new_period_start or version.period_start
    period_end = new_period_end or version.period_end

    # Load the original problem from the version's notes
    problem = {}
    if version.notes:
        try:
            stored = json.loads(version.notes)
            problem = stored.get("problem", {}).copy()
        except (json.JSONDecodeError, AttributeError):
            pass

    # Update period in problem
    if problem:
        problem["start_date"] = period_start.isoformat() if hasattr(period_start, "isoformat") else str(period_start)
        problem["end_date"] = period_end.isoformat() if hasattr(period_end, "isoformat") else str(period_end)

    draft = RosterVersion(
        location_code=version.location_code,
        period_start=period_start,
        period_end=period_end,
        status="draft",
        solver_status=None,
        notes=json.dumps({
            "problem": problem,
            "result": {},
            "source_version": version_id,
            "created_from_version_at": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    from app.core.audit import record_audit
    record_audit(
        db,
        current_user,
        "create_draft_from_version",
        "RosterVersion",
        draft.id,
        details=f"Created draft {draft.id} from version {version_id}",
    )
    db.commit()

    return {
        "draft_id": draft.id,
        "status": draft.status,
        "location_code": draft.location_code,
        "period_start": draft.period_start,
        "period_end": draft.period_end,
        "created_at": draft.created_at,
    }


# --- Attendance Integration ---

from app.models.time_attendance import TimeEntry, WorkingTimeViolation, ViolationKind, ViolationSeverity
from app.models.employee import Employee


DEFAULT_GRACE_MINUTES = 5


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse HH:MM time string to (hour, minute)."""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def _time_to_minutes(time_str: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    h, m = _parse_time(time_str)
    return h * 60 + m


def _minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM."""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def _datetime_to_minutes(dt: datetime) -> int:
    """Extract minutes since midnight from a timezone-aware datetime."""
    # Convert to local time (assuming the datetime is in the local timezone)
    # For simplicity, we use the time component directly
    return dt.hour * 60 + dt.minute


def get_roster_attendance(
    db: Session,
    version_id: int,
) -> Dict[str, Any]:
    """
    Get attendance for a published roster version.
    Joins RosterEntry with TimeEntry for the version's period.
    """
    version = db.query(RosterVersion).filter(RosterVersion.id == version_id).first()
    if not version:
        raise ValueError(f"Roster version {version_id} not found")

    if version.status != "published":
        raise ValueError(f"Version {version_id} is not published (status: {version.status})")

    # Get all roster entries for this version's period
    roster_entries = db.query(RosterEntry).filter(
        RosterEntry.work_date >= version.period_start,
        RosterEntry.work_date <= version.period_end,
    ).order_by(RosterEntry.work_date, RosterEntry.employee_id).all()

    # Get all time entries for the same period
    time_entries = db.query(TimeEntry).filter(
        TimeEntry.work_date >= version.period_start,
        TimeEntry.work_date <= version.period_end,
    ).all()

    # Create lookup for time entries by (employee_id, work_date)
    time_entry_map = {}
    for te in time_entries:
        key = (te.employee_id, te.work_date)
        if key not in time_entry_map:
            time_entry_map[key] = []
        time_entry_map[key].append(te)

    # Build response entries
    entries = []
    matched = 0
    missing = 0
    extra = 0

    for re in roster_entries:
        key = (re.employee_id, re.work_date)
        matching_entries = time_entry_map.get(key, [])

        # Find the best matching time entry (first one for now)
        time_entry = matching_entries[0] if matching_entries else None

        if time_entry:
            matched += 1
        else:
            missing += 1

        entries.append({
            "roster_entry": re,
            "time_entry": time_entry,
        })

    # Count extra time entries (no matching roster entry)
    roster_keys = {(re.employee_id, re.work_date) for re in roster_entries}
    for te in time_entries:
        key = (te.employee_id, te.work_date)
        if key not in roster_keys:
            extra += 1

    summary = {
        "total": len(roster_entries),
        "matched": matched,
        "missing": missing,
        "extra": extra,
    }

    return {
        "version_id": version.id,
        "location_code": version.location_code,
        "period_start": version.period_start,
        "period_end": version.period_end,
        "entries": entries,
        "summary": summary,
    }


def auto_create_attendance(
    db: Session,
    version_id: int,
    current_user,
    source: str = "Kiosk",
    tz: str | ZoneInfo = "UTC",
) -> Dict[str, Any]:
    """
    Create time entries from published roster entries (kiosk mode).
    Creates clock-in/clock-out records based on roster start/end times.

    Roster ``start_time``/``end_time`` are wall times in ``tz`` (IANA name
    or ZoneInfo, default UTC) converted via ``core.dst.wall_to_utc``.
    Overnight shifts (end <= start) roll clock-out to work_date + 1 day
    *before* conversion. Ambiguous fold times use fold=0 (first
    occurrence); gap times push forward per the DST helper.
    """
    version = db.query(RosterVersion).filter(RosterVersion.id == version_id).first()
    if not version:
        raise ValueError(f"Roster version {version_id} not found")

    if version.status != "published":
        raise ValueError(f"Version {version_id} is not published (status: {version.status})")

    # Get all roster entries for this version's period
    roster_entries = db.query(RosterEntry).filter(
        RosterEntry.work_date >= version.period_start,
        RosterEntry.work_date <= version.period_end,
    ).all()

    # Get existing time entries to avoid duplicates
    existing_time_entries = db.query(TimeEntry).filter(
        TimeEntry.work_date >= version.period_start,
        TimeEntry.work_date <= version.period_end,
    ).all()

    existing_keys = {(te.employee_id, te.work_date) for te in existing_time_entries}

    created = []
    skipped = 0

    for re in roster_entries:
        key = (re.employee_id, re.work_date)
        if key in existing_keys:
            skipped += 1
            continue

        # Create time entry with clock_in and clock_out based on roster times.
        # Roster times are wall times in `tz`; overnight shifts (end <= start)
        # roll clock-out to the next day *before* UTC conversion.
        work_date = re.work_date
        start_h, start_m = _parse_time(re.start_time)
        end_h, end_m = _parse_time(re.end_time)
        in_wall = datetime.combine(work_date, datetime.min.time().replace(
            hour=start_h, minute=start_m))
        out_date = work_date if (end_h, end_m) > (start_h, start_m) else work_date + timedelta(days=1)
        out_wall = datetime.combine(out_date, datetime.min.time().replace(
            hour=end_h, minute=end_m))
        clock_in = wall_to_utc(in_wall, tz, fold=0)
        clock_out = wall_to_utc(out_wall, tz, fold=0)

        # Calculate worked hours
        from app.crud.crud_time_attendance import worked_hours, overtime_hours
        wh = worked_hours(clock_in, clock_out, 0)
        ot = overtime_hours(wh)

        te = TimeEntry(
            employee_id=re.employee_id,
            work_date=work_date,
            clock_in=clock_in,
            clock_out=clock_out,
            break_minutes=0,
            worked_hours=wh,
            overtime_hours=ot,
            source=source,
            status="Draft",
            notes=f"Auto-created from roster version {version_id}",
            roster_entry_id=re.id,
        )
        db.add(te)
        db.flush()  # Get the ID
        created.append(te)

        existing_keys.add(key)  # Avoid duplicates in same batch

    db.commit()

    # Refresh created entries
    for te in created:
        db.refresh(te)

    from app.core.audit import record_audit
    record_audit(
        db,
        current_user,
        "auto_create_attendance",
        "RosterVersion",
        version_id,
        details=f"Auto-created {len(created)} time entries from roster version {version_id}",
    )
    db.commit()

    return {
        "version_id": version.id,
        "created_count": len(created),
        "skipped_count": skipped,
        "entries": created,
    }


def detect_deviations(
    db: Session,
    version_id: int,
    grace_minutes: int = DEFAULT_GRACE_MINUTES,
) -> Dict[str, Any]:
    """
    Detect deviations (working time violations) for a published roster version.
    Compares time entries against roster entries.
    """
    version = db.query(RosterVersion).filter(RosterVersion.id == version_id).first()
    if not version:
        raise ValueError(f"Roster version {version_id} not found")

    if version.status != "published":
        raise ValueError(f"Version {version_id} is not published (status: {version.status})")

    # Get all roster entries for this version's period
    roster_entries = db.query(RosterEntry).filter(
        RosterEntry.work_date >= version.period_start,
        RosterEntry.work_date <= version.period_end,
    ).order_by(RosterEntry.work_date, RosterEntry.employee_id).all()

    # Get all time entries for the same period
    time_entries = db.query(TimeEntry).filter(
        TimeEntry.work_date >= version.period_start,
        TimeEntry.work_date <= version.period_end,
    ).all()

    # Re-running detection replaces the previous rows rather than
    # duplicating them: the violation record is the *state* of the compare
    # run, and the same breach must not pile up one row per re-run.
    db.query(WorkingTimeViolation).filter(
        WorkingTimeViolation.work_date >= version.period_start,
        WorkingTimeViolation.work_date <= version.period_end,
    ).delete(synchronize_session=False)
    db.flush()

    # Create lookup for time entries by (employee_id, work_date)
    time_entry_map = {}
    for te in time_entries:
        key = (te.employee_id, te.work_date)
        if key not in time_entry_map:
            time_entry_map[key] = []
        time_entry_map[key].append(te)

    deviations = []
    summary = {
        "early_arrival": 0,
        "late_arrival": 0,
        "early_departure": 0,
        "late_departure": 0,
        "missing_entry": 0,
        "extra_entry": 0,
        "info": 0,
        "warning": 0,
        "critical": 0,
    }

    roster_keys = set()

    for re in roster_entries:
        key = (re.employee_id, re.work_date)
        roster_keys.add(key)

        matching_entries = time_entry_map.get(key, [])
        time_entry = matching_entries[0] if matching_entries else None

        entry_violations = []

        if not time_entry:
            # Missing entry
            violation = WorkingTimeViolation(
                employee_id=re.employee_id,
                work_date=re.work_date,
                roster_entry_id=re.id,
                time_entry_id=None,
                kind=ViolationKind.MISSING_ENTRY,
                severity=ViolationSeverity.WARNING,
                minutes=0,
            )
            db.add(violation)
            entry_violations.append(violation)
            summary["missing_entry"] += 1
            summary["warning"] += 1
        else:
            # Check clock_in against roster start_time
            roster_start_minutes = _time_to_minutes(re.start_time)
            roster_end_minutes = _time_to_minutes(re.end_time)

            if time_entry.clock_in:
                clock_in_minutes = _datetime_to_minutes(time_entry.clock_in)
                diff = clock_in_minutes - roster_start_minutes

                if diff < -grace_minutes:
                    # Early arrival
                    violation = WorkingTimeViolation(
                        employee_id=re.employee_id,
                        work_date=re.work_date,
                        roster_entry_id=re.id,
                        time_entry_id=time_entry.id,
                        kind=ViolationKind.EARLY_ARRIVAL,
                        severity=ViolationSeverity.INFO,
                        minutes=abs(diff),
                    )
                    db.add(violation)
                    entry_violations.append(violation)
                    summary["early_arrival"] += 1
                    summary["info"] += 1
                elif diff > grace_minutes:
                    # Late arrival
                    violation = WorkingTimeViolation(
                        employee_id=re.employee_id,
                        work_date=re.work_date,
                        roster_entry_id=re.id,
                        time_entry_id=time_entry.id,
                        kind=ViolationKind.LATE_ARRIVAL,
                        severity=ViolationSeverity.WARNING,
                        minutes=diff,
                    )
                    db.add(violation)
                    entry_violations.append(violation)
                    summary["late_arrival"] += 1
                    summary["warning"] += 1

            # Check clock_out against roster end_time
            if time_entry.clock_out:
                clock_out_minutes = _datetime_to_minutes(time_entry.clock_out)
                diff = clock_out_minutes - roster_end_minutes

                if diff < -grace_minutes:
                    # Early departure
                    violation = WorkingTimeViolation(
                        employee_id=re.employee_id,
                        work_date=re.work_date,
                        roster_entry_id=re.id,
                        time_entry_id=time_entry.id,
                        kind=ViolationKind.EARLY_DEPARTURE,
                        severity=ViolationSeverity.WARNING,
                        minutes=abs(diff),
                    )
                    db.add(violation)
                    entry_violations.append(violation)
                    summary["early_departure"] += 1
                    summary["warning"] += 1
                elif diff > grace_minutes:
                    # Late departure
                    violation = WorkingTimeViolation(
                        employee_id=re.employee_id,
                        work_date=re.work_date,
                        roster_entry_id=re.id,
                        time_entry_id=time_entry.id,
                        kind=ViolationKind.LATE_DEPARTURE,
                        severity=ViolationSeverity.WARNING,
                        minutes=diff,
                    )
                    db.add(violation)
                    entry_violations.append(violation)
                    summary["late_departure"] += 1
                    summary["warning"] += 1

        if entry_violations:
            deviations.append({
                "roster_entry": re,
                "time_entry": time_entry,
                "violations": entry_violations,
            })

    # Check for extra time entries (no matching roster entry)
    for te in time_entries:
        key = (te.employee_id, te.work_date)
        if key not in roster_keys:
            violation = WorkingTimeViolation(
                employee_id=te.employee_id,
                work_date=te.work_date,
                roster_entry_id=None,
                time_entry_id=te.id,
                kind=ViolationKind.EXTRA_ENTRY,
                severity=ViolationSeverity.INFO,
                minutes=0,
            )
            db.add(violation)
            deviations.append({
                "roster_entry": None,
                "time_entry": te,
                "violations": [violation],
            })
            summary["extra_entry"] += 1
            summary["info"] += 1

    db.commit()

    # Refresh violations to get IDs
    for dev in deviations:
        for v in dev["violations"]:
            db.refresh(v)

    return {
        "version_id": version.id,
        "location_code": version.location_code,
        "period_start": version.period_start,
        "period_end": version.period_end,
        "deviations": deviations,
        "summary": summary,
    }
