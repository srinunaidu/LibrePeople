from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, ALL_ROLES, MANAGER_ROLES, WORKFORCE_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.models.learning import (
    Certification,
    Course,
    CourseEnrollment,
    SuccessionPlan,
    TalentPool,
    TalentPoolMember,
)
from app.models.user import User
from app.schemas.learning import (
    CertificationCreate,
    CertificationOut,
    CourseCreate,
    CourseEnrollmentCreate,
    CourseEnrollmentOut,
    CourseOut,
    SuccessionPlanCreate,
    SuccessionPlanOut,
    TalentPoolCreate,
    TalentPoolMemberCreate,
    TalentPoolMemberOut,
    TalentPoolOut,
)

router = APIRouter()


# --- Courses ---------------------------------------------------------------- #

@router.get("/courses", response_model=list[CourseOut], operation_id="learningListLearningcourses")
def list_courses(db: Session = Depends(get_db), u: User = Depends(require_roles(*ALL_ROLES))):
    return db.query(Course).order_by(Course.code).all()


@router.post("/courses", response_model=CourseOut, status_code=201, operation_id="learningCreateLearningcourses")
def create_course(payload: CourseCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = Course(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_course", "Course", obj.id); db.commit()
    return obj


# --- Enrollments ------------------------------------------------------------ #

@router.get("/course-enrollments", response_model=list[CourseEnrollmentOut], operation_id="learningListLearningcourseenrollments")
def list_enrollments(employee_id: int | None = None, course_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(CourseEnrollment)
    q = apply_visibility(q, CourseEnrollment.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(CourseEnrollment.employee_id == employee_id)
    if course_id:
        q = q.filter(CourseEnrollment.course_id == course_id)
    return q.order_by(CourseEnrollment.id.desc()).all()


@router.post("/course-enrollments", response_model=CourseEnrollmentOut, status_code=201, operation_id="learningCreateLearningcourseenrollments")
def create_enrollment(payload: CourseEnrollmentCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    obj = CourseEnrollment(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_course_enrollment", "CourseEnrollment", obj.id); db.commit()
    return obj


@router.put("/course-enrollments/{enrollment_id}/complete", response_model=CourseEnrollmentOut, operation_id="learningUpdateLearningcourseenrollmentscomplete")
def complete_enrollment(enrollment_id: int, score: float | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    from datetime import datetime, timezone

    obj = db.query(CourseEnrollment).filter(CourseEnrollment.id == enrollment_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    obj.status = "Completed"
    obj.completed_at = datetime.now(timezone.utc)
    if score is not None:
        obj.score = score
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "complete_course", "CourseEnrollment", obj.id); db.commit()
    return obj


# --- Certifications --------------------------------------------------------- #

@router.get("/certifications", response_model=list[CertificationOut], operation_id="learningListLearningcertifications")
def list_certifications(employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(Certification)
    q = apply_visibility(q, Certification.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(Certification.employee_id == employee_id)
    return q.order_by(Certification.id.desc()).all()


@router.post("/certifications", response_model=CertificationOut, status_code=201, operation_id="learningCreateLearningcertifications")
def create_certification(payload: CertificationCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    obj = Certification(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_certification", "Certification", obj.id); db.commit()
    return obj


# --- Talent pools ----------------------------------------------------------- #

@router.get("/talent-pools", response_model=list[TalentPoolOut], operation_id="learningListLearningtalentpools")
def list_pools(db: Session = Depends(get_db), u: User = Depends(require_roles(*MANAGER_ROLES))):
    return db.query(TalentPool).order_by(TalentPool.name).all()


@router.post("/talent-pools", response_model=TalentPoolOut, status_code=201, operation_id="learningCreateLearningtalentpools")
def create_pool(payload: TalentPoolCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = TalentPool(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_talent_pool", "TalentPool", obj.id); db.commit()
    return obj


@router.post("/talent-pool-members", response_model=TalentPoolMemberOut, status_code=201, operation_id="learningCreateLearningtalentpoolmembers")
def add_pool_member(payload: TalentPoolMemberCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = TalentPoolMember(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "add_talent_pool_member", "TalentPoolMember", obj.id); db.commit()
    return obj


# --- Succession ------------------------------------------------------------- #

@router.get("/succession-plans", response_model=list[SuccessionPlanOut], operation_id="learningListLearningsuccessionplans")
def list_succession(db: Session = Depends(get_db), u: User = Depends(require_roles(*MANAGER_ROLES))):
    return db.query(SuccessionPlan).order_by(SuccessionPlan.id.desc()).all()


@router.post("/succession-plans", response_model=SuccessionPlanOut, status_code=201, operation_id="learningCreateLearningsuccessionplans")
def create_succession(payload: SuccessionPlanCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = SuccessionPlan(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_succession_plan", "SuccessionPlan", obj.id); db.commit()
    return obj
