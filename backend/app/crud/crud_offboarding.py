from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.booleans import is_true
from app.models.offboarding import OffboardingItem, OffboardingTask, Termination
from app.schemas.offboarding import (
    OffboardingItemUpdate,
    OffboardingTaskCreate,
    OffboardingTaskUpdated,
    TerminationCreate,
    TerminationUpdate,
)

# Default checklist applied to every offboarding case.
DEFAULT_OFFBOARDING_TASKS: list[dict] = [
    {"name": "Collect company laptop and peripherals", "category": "IT", "default_assignee_role": "HR"},
    {"name": "Revoke system and building access", "category": "IT", "default_assignee_role": "IT"},
    {"name": "Set up final pay and settlement", "category": "Finance", "default_assignee_role": "Payroll"},
    {"name": "Exit interview", "category": "HR", "default_assignee_role": "HR"},
    {"name": "Knowledge transfer handover", "category": "General", "default_assignee_role": "Manager"},
    {"name": "Return ID badge and office keys", "category": "Facilities", "default_assignee_role": "Facilities"},
]


# --- Checklist templates ---------------------------------------------------- #

def get_task(db: Session, task_id: int) -> OffboardingTask | None:
    return db.query(OffboardingTask).filter(OffboardingTask.id == task_id).first()


def get_tasks(db: Session, active_only: bool = False) -> list[OffboardingTask]:
    query = db.query(OffboardingTask)
    if active_only:
        query = query.filter(is_true(OffboardingTask.is_active))
    return query.order_by(OffboardingTask.category, OffboardingTask.name).all()


def create_task(db: Session, payload: OffboardingTaskCreate) -> OffboardingTask:
    db_obj = OffboardingTask(**payload.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_task(db: Session, db_obj: OffboardingTask, payload: OffboardingTaskUpdated) -> OffboardingTask:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


# --- Terminations ----------------------------------------------------------- #

def get_terminations(db: Session, status: str | None = None) -> list[Termination]:
    query = db.query(Termination)
    if status:
        query = query.filter(Termination.status == status)
    return query.order_by(Termination.created_at.desc()).all()


def get_termination(db: Session, termination_id: int) -> Termination | None:
    return db.query(Termination).filter(Termination.id == termination_id).first()


def get_item(db: Session, item_id: int) -> OffboardingItem | None:
    return db.query(OffboardingItem).filter(OffboardingItem.id == item_id).first()


def create_termination(db: Session, payload: TerminationCreate, initiated_by: int) -> Termination:
    db_obj = Termination(
        employee_id=payload.employee_id,
        last_working_date=payload.last_working_date,
        termination_type=payload.termination_type,
        reason=payload.reason,
        final_pay_amount=payload.final_pay_amount,
        initiated_by=initiated_by,
        status="Initiated",
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def apply_default_checklist(db: Session, termination_id: int) -> list[OffboardingItem]:
    """Instantiate the standard offboarding checklist for a termination."""
    created: list[OffboardingItem] = []
    for item in DEFAULT_OFFBOARDING_TASKS:
        created.append(
            OffboardingItem(
                termination_id=termination_id,
                name=item["name"],
                category=item["category"],
                assigned_to=item.get("default_assignee_role"),
                status="Pending",
            )
        )
    if created:
        db.add_all(created)
        db.commit()
        for item in created:
            db.refresh(item)
    return created


def update_termination(db: Session, db_obj: Termination, payload: TerminationUpdate) -> Termination:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_item(db: Session, db_obj: OffboardingItem, payload: OffboardingItemUpdate) -> OffboardingItem:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    if data.get("status") == "Completed":
        db_obj.completed_at = datetime.utcnow()
    elif data.get("status") == "Pending":
        db_obj.completed_at = None
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def complete_termination(db: Session, db_obj: Termination) -> Termination:
    db_obj.status = "Completed"
    db_obj.completed_at = datetime.utcnow()
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def item_progress(db: Session, termination_id: int) -> dict:
    items = db.query(OffboardingItem).filter(OffboardingItem.termination_id == termination_id).all()
    total = len(items)
    done = sum(1 for i in items if i.status == "Completed")
    return {
        "total": total,
        "completed": done,
        "progress_percent": int((done / total) * 100) if total else 0,
    }
