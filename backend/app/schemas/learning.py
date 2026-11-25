from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class CourseCreate(BaseModel):
    title: str
    code: str
    description: Optional[str] = None
    category: str = "General"
    duration_hours: float = 0
    is_mandatory: bool = False
    is_active: bool = True


class CourseOut(CourseCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseEnrollmentCreate(BaseModel):
    employee_id: int
    course_id: int
    status: str = "Enrolled"
    score: Optional[float] = None


class CourseEnrollmentOut(CourseEnrollmentCreate):
    id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CertificationCreate(BaseModel):
    employee_id: int
    name: str
    issuer: Optional[str] = None
    issued_date: date
    expiry_date: Optional[date] = None
    certificate_url: Optional[str] = None


class CertificationOut(CertificationCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TalentPoolCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TalentPoolOut(TalentPoolCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TalentPoolMemberCreate(BaseModel):
    pool_id: int
    employee_id: int
    readiness: str = "Ready in 2-3 years"
    notes: Optional[str] = None


class TalentPoolMemberOut(TalentPoolMemberCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SuccessionPlanCreate(BaseModel):
    position_id: int
    primary_successor_id: Optional[int] = None
    backup_successor_id: Optional[int] = None
    readiness: str = "Ready in 2-3 years"
    notes: Optional[str] = None


class SuccessionPlanOut(SuccessionPlanCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
