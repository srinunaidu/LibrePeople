from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, MANAGER_ROLES, WORKFORCE_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.visibility import apply_visibility, ensure_can_view_employee, ensure_manages_direct_report
from app.models.performance import (
    CompensationBand,
    Goal,
    MeritAllocation,
    MeritCycle,
    PerformanceReview,
    ReviewFeedback,
)
from app.models.user import User
from app.schemas.performance import (
    CompensationBandCreate,
    CompensationBandOut,
    GoalCreate,
    GoalOut,
    GoalUpdate,
    MeritAllocationCreate,
    MeritAllocationOut,
    MeritCycleCreate,
    MeritCycleOut,
    PerformanceReviewCreate,
    PerformanceReviewOut,
    PerformanceReviewUpdate,
    ReviewFeedbackCreate,
    ReviewFeedbackOut,
)

router = APIRouter()


def _crud_list(model):
    return lambda db, **kw: db.query(model).order_by(model.id.desc()).all()


# --- Goals ------------------------------------------------------------------ #

@router.get("/goals", response_model=list[GoalOut], operation_id="performanceListPerformancegoals")
def list_goals(employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(Goal)
    q = apply_visibility(q, Goal.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(Goal.employee_id == employee_id)
    return q.order_by(Goal.id.desc()).all()


@router.post("/goals", response_model=GoalOut, status_code=201, operation_id="performanceCreatePerformancegoals")
def create_goal(payload: GoalCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*MANAGER_ROLES))):
    ensure_manages_direct_report(db, u, payload.employee_id)
    obj = Goal(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_goal", "Goal", obj.id); db.commit()
    return obj


@router.put("/goals/{goal_id}", response_model=GoalOut, operation_id="performanceUpdatePerformancegoals")
def update_goal(goal_id: int, payload: GoalUpdate, db: Session = Depends(get_db), u: User = Depends(require_roles(*MANAGER_ROLES))):
    obj = db.query(Goal).filter(Goal.id == goal_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Goal not found")
    for f, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "update_goal", "Goal", obj.id); db.commit()
    return obj


# --- Performance reviews ---------------------------------------------------- #

@router.get("/reviews", response_model=list[PerformanceReviewOut], operation_id="performanceListPerformancereviews")
def list_reviews(employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(PerformanceReview)
    q = apply_visibility(q, PerformanceReview.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(PerformanceReview.employee_id == employee_id)
    return q.order_by(PerformanceReview.id.desc()).all()


@router.post("/reviews", response_model=PerformanceReviewOut, status_code=201, operation_id="performanceCreatePerformancereviews")
def create_review(payload: PerformanceReviewCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*MANAGER_ROLES))):
    obj = PerformanceReview(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_review", "PerformanceReview", obj.id); db.commit()
    return obj


@router.put("/reviews/{review_id}", response_model=PerformanceReviewOut, operation_id="performanceUpdatePerformancereviews")
def update_review(review_id: int, payload: PerformanceReviewUpdate, db: Session = Depends(get_db), u: User = Depends(require_roles(*MANAGER_ROLES))):
    obj = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Review not found")
    for f, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "update_review", "PerformanceReview", obj.id); db.commit()
    return obj


@router.post("/reviews/{review_id}/finalize", response_model=PerformanceReviewOut, operation_id="performanceCreatePerformancereviewsfinalize")
def finalize_review(review_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*MANAGER_ROLES))):
    from datetime import datetime, timezone

    obj = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Review not found")
    obj.status = "Finalized"
    obj.finalized_at = datetime.now(timezone.utc)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "finalize_review", "PerformanceReview", obj.id); db.commit()
    return obj


# --- Review feedback -------------------------------------------------------- #

@router.get("/feedback", response_model=list[ReviewFeedbackOut], operation_id="performanceGetPerformancefeedback")
def list_feedback(review_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(ReviewFeedback)
    if review_id:
        review = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        ensure_can_view_employee(db, u, review.employee_id)
        q = q.filter(ReviewFeedback.review_id == review_id)
    return q.order_by(ReviewFeedback.id.desc()).all()


@router.post("/feedback", response_model=ReviewFeedbackOut, status_code=201, operation_id="performanceCreatePerformancefeedback")
def create_feedback(payload: ReviewFeedbackCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    obj = ReviewFeedback(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_feedback", "ReviewFeedback", obj.id); db.commit()
    return obj


# --- Compensation bands ----------------------------------------------------- #

@router.get("/compensation-bands", response_model=list[CompensationBandOut], operation_id="performanceListPerformancecompensationbands")
def list_bands(job_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    q = db.query(CompensationBand)
    if job_id:
        q = q.filter(CompensationBand.job_id == job_id)
    return q.order_by(CompensationBand.id).all()


@router.post("/compensation-bands", response_model=CompensationBandOut, status_code=201, operation_id="performanceCreatePerformancecompensationbands")
def create_band(payload: CompensationBandCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = CompensationBand(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_compensation_band", "CompensationBand", obj.id); db.commit()
    return obj


# --- Merit cycles ----------------------------------------------------------- #

@router.get("/merit-cycles", response_model=list[MeritCycleOut], operation_id="performanceListPerformancemeritcycles")
def list_cycles(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    return db.query(MeritCycle).order_by(MeritCycle.year.desc()).all()


@router.post("/merit-cycles", response_model=MeritCycleOut, status_code=201, operation_id="performanceCreatePerformancemeritcycles")
def create_cycle(payload: MeritCycleCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = MeritCycle(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_merit_cycle", "MeritCycle", obj.id); db.commit()
    return obj


@router.get("/merit-allocations", response_model=list[MeritAllocationOut], operation_id="performanceListPerformancemeritallocations")
def list_allocations(cycle_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    q = db.query(MeritAllocation)
    q = apply_visibility(q, MeritAllocation.employee_id, u, db)
    if cycle_id:
        q = q.filter(MeritAllocation.cycle_id == cycle_id)
    return q.order_by(MeritAllocation.id).all()


@router.post("/merit-allocations", response_model=MeritAllocationOut, status_code=201, operation_id="performanceCreatePerformancemeritallocations")
def create_allocation(payload: MeritAllocationCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = MeritAllocation(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_merit_allocation", "MeritAllocation", obj.id); db.commit()
    return obj
