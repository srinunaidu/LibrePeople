from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, ALL_ROLES, WORKFORCE_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.models.benefits import BenefitEnrollment, BenefitPlan, LeaveOfAbsence, LifeEvent
from app.models.user import User
from app.schemas.benefits import (
    BenefitEnrollmentCreate,
    BenefitEnrollmentOut,
    BenefitPlanCreate,
    BenefitPlanOut,
    LeaveOfAbsenceCreate,
    LeaveOfAbsenceOut,
    LifeEventCreate,
    LifeEventOut,
)

router = APIRouter()


# --- Plans ------------------------------------------------------------------ #

@router.get("/benefit-plans", response_model=list[BenefitPlanOut], operation_id="benefitsListBenefitsbenefitplans")
def list_plans(db: Session = Depends(get_db), u: User = Depends(require_roles(*ALL_ROLES))):
    return db.query(BenefitPlan).order_by(BenefitPlan.code).all()


@router.post("/benefit-plans", response_model=BenefitPlanOut, status_code=201, operation_id="benefitsCreateBenefitsbenefitplans")
def create_plan(payload: BenefitPlanCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = BenefitPlan(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_benefit_plan", "BenefitPlan", obj.id); db.commit()
    return obj


# --- Enrollments ------------------------------------------------------------ #

@router.get("/benefit-enrollments", response_model=list[BenefitEnrollmentOut], operation_id="benefitsListBenefitsbenefitenrollments")
def list_enrollments(employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(BenefitEnrollment)
    q = apply_visibility(q, BenefitEnrollment.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(BenefitEnrollment.employee_id == employee_id)
    return q.order_by(BenefitEnrollment.id.desc()).all()


@router.post("/benefit-enrollments", response_model=BenefitEnrollmentOut, status_code=201, operation_id="benefitsCreateBenefitsbenefitenrollments")
def create_enrollment(payload: BenefitEnrollmentCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    ensure_can_view_employee(db, u, payload.employee_id)
    obj = BenefitEnrollment(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_benefit_enrollment", "BenefitEnrollment", obj.id); db.commit()
    return obj


# --- Life events ------------------------------------------------------------ #

@router.get("/life-events", response_model=list[LifeEventOut], operation_id="benefitsListBenefitslifeevents")
def list_life_events(employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(LifeEvent)
    q = apply_visibility(q, LifeEvent.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(LifeEvent.employee_id == employee_id)
    return q.order_by(LifeEvent.created_at.desc()).all()


@router.post("/life-events", response_model=LifeEventOut, status_code=201, operation_id="benefitsCreateBenefitslifeevents")
def create_life_event(payload: LifeEventCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    ensure_can_view_employee(db, u, payload.employee_id)
    obj = LifeEvent(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_life_event", "LifeEvent", obj.id); db.commit()
    return obj


# --- Leave of absence ------------------------------------------------------- #

@router.get("/leaves-of-absence", response_model=list[LeaveOfAbsenceOut], operation_id="benefitsGetBenefitsleavesofabsence")
def list_loa(employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(LeaveOfAbsence)
    q = apply_visibility(q, LeaveOfAbsence.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(LeaveOfAbsence.employee_id == employee_id)
    return q.order_by(LeaveOfAbsence.created_at.desc()).all()


@router.post("/leaves-of-absence", response_model=LeaveOfAbsenceOut, status_code=201, operation_id="benefitsCreateBenefitsleavesofabsence")
def create_loa(payload: LeaveOfAbsenceCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    ensure_can_view_employee(db, u, payload.employee_id)
    obj = LeaveOfAbsence(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_leave_of_absence", "LeaveOfAbsence", obj.id); db.commit()
    return obj


@router.put("/leaves-of-absence/{loa_id}/approve", response_model=LeaveOfAbsenceOut, operation_id="benefitsUpdateBenefitsleavesofabsenceapprove")
def approve_loa(loa_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    from datetime import datetime, timezone

    obj = db.query(LeaveOfAbsence).filter(LeaveOfAbsence.id == loa_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Leave of absence not found")
    obj.status = "Approved"
    obj.approved_by = u.id
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "approve_leave_of_absence", "LeaveOfAbsence", obj.id); db.commit()
    return obj
