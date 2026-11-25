from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.booleans import is_true
from app.models.scheduling import RosterEntry, ShiftSwap, ShiftTemplate
from app.schemas.scheduling import (
    RosterEntryCreate,
    RosterEntryUpdate,
    RosterGenerate,
    ShiftTemplateCreate,
    ShiftTemplateUpdate,
    SwapCreate,
)


def get_template(db: Session, template_id: int) -> ShiftTemplate | None:
    return db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()


def get_template_by_code(db: Session, code: str) -> ShiftTemplate | None:
    return db.query(ShiftTemplate).filter(ShiftTemplate.code == code).first()


def get_templates(db: Session, active_only: bool = False) -> list[ShiftTemplate]:
    query = db.query(ShiftTemplate)
    if active_only:
        query = query.filter(is_true(ShiftTemplate.is_active))
    return query.order_by(ShiftTemplate.code).all()


def create_template(db: Session, template_in: ShiftTemplateCreate) -> ShiftTemplate:
    db_obj = ShiftTemplate(**template_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_template(
    db: Session, db_obj: ShiftTemplate, template_in: ShiftTemplateUpdate
) -> ShiftTemplate:
    for field, value in template_in.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_roster(
    db: Session,
    employee_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[RosterEntry]:
    query = db.query(RosterEntry)
    if employee_id:
        query = query.filter(RosterEntry.employee_id == employee_id)
    if start:
        query = query.filter(RosterEntry.work_date >= start)
    if end:
        query = query.filter(RosterEntry.work_date <= end)
    return query.order_by(RosterEntry.work_date, RosterEntry.id).all()


def get_roster_entry(db: Session, entry_id: int) -> RosterEntry | None:
    return db.query(RosterEntry).filter(RosterEntry.id == entry_id).first()


def create_roster_entry(db: Session, entry_in: RosterEntryCreate) -> RosterEntry:
    db_obj = RosterEntry(**entry_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def generate_roster(db: Session, spec: RosterGenerate) -> list[RosterEntry]:
    """Create one roster entry per day in the range from a shift template."""
    template = get_template(db, spec.shift_template_id)
    if not template:
        return []
    entries: list[RosterEntry] = []
    day = spec.start_date
    while day <= spec.end_date:
        if not db.query(RosterEntry).filter(
            RosterEntry.employee_id == spec.employee_id, RosterEntry.work_date == day
        ).first():
            entries.append(
                RosterEntry(
                    employee_id=spec.employee_id,
                    work_date=day,
                    shift_template_id=template.id,
                    start_time=template.start_time,
                    end_time=template.end_time,
                    is_night=template.is_night,
                    status="Scheduled",
                )
            )
        day += timedelta(days=1)
    if entries:
        db.add_all(entries)
        db.commit()
        for entry in entries:
            db.refresh(entry)
    return entries


def update_roster_entry(
    db: Session, db_obj: RosterEntry, entry_in: RosterEntryUpdate
) -> RosterEntry:
    for field, value in entry_in.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_swap(db: Session, swap_id: int) -> ShiftSwap | None:
    return db.query(ShiftSwap).filter(ShiftSwap.id == swap_id).first()


def get_swaps(db: Session, status: str | None = None) -> list[ShiftSwap]:
    query = db.query(ShiftSwap)
    if status:
        query = query.filter(ShiftSwap.status == status)
    return query.order_by(ShiftSwap.created_at.desc()).all()


def create_swap(db: Session, requester_id: int, payload: SwapCreate) -> ShiftSwap:
    db_obj = ShiftSwap(
        roster_entry_id=payload.roster_entry_id,
        requester_id=requester_id,
        target_id=payload.target_id,
        proposed_date=payload.proposed_date,
        status="Pending",
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def decide_swap(
    db: Session, db_obj: ShiftSwap, approved: bool, decided_by: int
) -> ShiftSwap:
    db_obj.status = "Approved" if approved else "Rejected"
    db_obj.decided_by = decided_by
    db_obj.decided_at = datetime.utcnow()
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
