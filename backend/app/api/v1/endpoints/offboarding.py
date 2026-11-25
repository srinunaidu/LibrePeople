from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, WORKFORCE_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.visibility import ensure_can_view_employee
from app.crud import crud_offboarding as crud
from app.crud.crud_employee import get_employee, update_employee
from app.models.employee import Employee
from app.models.user import User
from app.services import notifications as notify
from app.schemas.employee import EmployeeUpdate
from app.schemas.offboarding import (
    OffboardingItemOut,
    OffboardingItemUpdate,
    OffboardingTaskCreate,
    OffboardingTaskOut,
    OffboardingTaskUpdated,
    TerminationCreate,
    TerminationOut,
    TerminationUpdate,
)

router = APIRouter()


def _notify_termination(db: Session, employee_id: int, notification_type: str,
                        category: str, title: str, message: str,
                        termination_id: int) -> None:
    """Notify the employee behind an offboarding case, if they have a login."""
    recipient = notify.user_id_for_employee(db, employee_id)
    if recipient is None:
        return
    notify.emit(
        db,
        recipient_user_id=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        category=category,
        entity_type="termination",
        entity_id=termination_id,
    )


# --- Checklist templates ---------------------------------------------------- #

@router.get("/tasks", response_model=list[OffboardingTaskOut], operation_id="offboardingListOffboardingtasks")
def list_tasks(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    return crud.get_tasks(db, active_only=active_only)


@router.post("/tasks", response_model=OffboardingTaskOut, status_code=201, operation_id="offboardingCreateOffboardingtasks")
def create_task(
    payload: OffboardingTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    task = crud.create_task(db, payload)
    record_audit(db, current_user, "create_offboarding_task", "OffboardingTask", task.id)
    db.commit()
    return task


@router.put("/tasks/{task_id}", response_model=OffboardingTaskOut, operation_id="offboardingUpdateOffboardingtasks")
def update_task(
    task_id: int,
    payload: OffboardingTaskUpdated,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Offboarding task not found")
    task = crud.update_task(db, task, payload)
    record_audit(db, current_user, "update_offboarding_task", "OffboardingTask", task.id)
    db.commit()
    return task


# --- Terminations ----------------------------------------------------------- #

@router.get("/terminations", response_model=list[TerminationOut], operation_id="offboardingListOffboardingterminations")
def list_terminations(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Terminations, scoped to the caller's visibility.

    Termination records carry exit reasons and are sensitive; any
    authenticated user could previously list them all.
    """
    from app.core.visibility import apply_visibility
    from app.models.offboarding import Termination

    query = db.query(Termination)
    query = apply_visibility(query, Termination.employee_id, current_user, db)
    if status:
        query = query.filter(Termination.status == status)
    return query.order_by(Termination.id.desc()).all()


@router.get("/terminations/{termination_id}", response_model=TerminationOut, operation_id="offboardingGetOffboardingterminations")
def get_termination(
    termination_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    termination = crud.get_termination(db, termination_id)
    if not termination:
        raise HTTPException(status_code=404, detail="Termination not found")
    ensure_can_view_employee(db, current_user, termination.employee_id)
    return termination


@router.post("/terminations", response_model=TerminationOut, status_code=201, operation_id="offboardingCreateOffboardingterminations")
def start_termination(
    payload: TerminationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    employee = get_employee(db, payload.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.status == "Terminated":
        raise HTTPException(status_code=400, detail="Employee is already terminated")
    termination = crud.create_termination(db, payload, current_user.id)
    crud.apply_default_checklist(db, termination.id)
    record_audit(db, current_user, "start_termination", "Termination", termination.id)
    # The exit has started: the employee hears it first, from the record.
    _notify_termination(
        db, termination.employee_id, "warning", "offboarding",
        f"Offboarding started (case #{termination.id})",
        "Your offboarding case has been opened. Your manager or HR will "
        "walk you through the exit checklist.",
        termination.id,
    )
    db.commit()
    return crud.get_termination(db, termination.id)


@router.put("/terminations/{termination_id}", response_model=TerminationOut, operation_id="offboardingUpdateOffboardingterminations")
def update_termination(
    termination_id: int,
    payload: TerminationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    termination = crud.get_termination(db, termination_id)
    if not termination:
        raise HTTPException(status_code=404, detail="Termination not found")
    termination = crud.update_termination(db, termination, payload)
    if payload.status == "In Progress" and termination.status == "Initiated":
        pass
    record_audit(db, current_user, "update_termination", "Termination", termination.id)
    db.commit()
    return termination


@router.post("/terminations/{termination_id}/complete", response_model=TerminationOut, operation_id="offboardingCreateOffboardingterminationscomplete")
def complete_termination(
    termination_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    termination = crud.get_termination(db, termination_id)
    if not termination:
        raise HTTPException(status_code=404, detail="Termination not found")
    crud.complete_termination(db, termination)
    # Mark the employee as terminated in the master data.
    employee = get_employee(db, termination.employee_id)
    if employee:
        update_employee(
            db,
            employee,
            EmployeeUpdate(status="Terminated"),
        )
    record_audit(db, current_user, "complete_termination", "Termination", termination.id)
    # The exit is closed: full-and-final follows, and the employee is told.
    _notify_termination(
        db, termination.employee_id, "success", "offboarding",
        f"Offboarding completed (case #{termination.id})",
        "Your offboarding case is complete. Your full-and-final settlement "
        "will follow through payroll.",
        termination.id,
    )
    db.commit()
    return crud.get_termination(db, termination.id)


@router.post("/terminations/{termination_id}/cancel", response_model=TerminationOut, operation_id="offboardingCreateOffboardingterminationscancel")
def cancel_termination(
    termination_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    termination = crud.get_termination(db, termination_id)
    if not termination:
        raise HTTPException(status_code=404, detail="Termination not found")
    termination.status = "Cancelled"
    db.add(termination)
    db.commit()
    record_audit(db, current_user, "cancel_termination", "Termination", termination.id)
    db.commit()
    return crud.get_termination(db, termination.id)


@router.get("/terminations/{termination_id}/progress", operation_id="offboardingListOffboardingterminationsprogress")
def termination_progress(
    termination_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    if not crud.get_termination(db, termination_id):
        raise HTTPException(status_code=404, detail="Termination not found")
    return crud.item_progress(db, termination_id)


# --- Checklist items -------------------------------------------------------- #

@router.put("/items/{item_id}", response_model=OffboardingItemOut, operation_id="offboardingUpdateOffboardingitems")
def update_item(
    item_id: int,
    payload: OffboardingItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    item = crud.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Offboarding item not found")
    item = crud.update_item(db, item, payload)
    record_audit(db, current_user, "update_offboarding_item", "OffboardingItem", item.id)
    db.commit()
    return item
