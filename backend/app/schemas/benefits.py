from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class BenefitPlanCreate(BaseModel):
    name: str
    code: str
    plan_type: str
    provider: Optional[str] = None
    employer_contribution: float = 0
    employee_contribution: float = 0
    is_active: bool = True


class BenefitPlanOut(BenefitPlanCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BenefitEnrollmentCreate(BaseModel):
    employee_id: int
    plan_id: int
    effective_date: date
    end_date: Optional[date] = None
    status: str = "Active"


class BenefitEnrollmentOut(BenefitEnrollmentCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LifeEventCreate(BaseModel):
    employee_id: int
    event_type: str
    event_date: date
    description: Optional[str] = None
    status: str = "Pending"


class LifeEventOut(LifeEventCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeaveOfAbsenceCreate(BaseModel):
    employee_id: int
    leave_type: str
    start_date: date
    end_date: Optional[date] = None
    status: str = "Pending"
    notes: Optional[str] = None


class LeaveOfAbsenceOut(LeaveOfAbsenceCreate):
    id: int
    approved_by: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
