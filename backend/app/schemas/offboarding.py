from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class OffboardingTaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "General"
    is_required: bool = True
    default_assignee_role: Optional[str] = None
    is_active: bool = True


class OffboardingTaskUpdated(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_required: Optional[bool] = None
    default_assignee_role: Optional[str] = None
    is_active: Optional[bool] = None


class OffboardingTaskOut(OffboardingTaskCreate):
    id: int

    class Config:
        from_attributes = True


class TerminationCreate(BaseModel):
    employee_id: int
    last_working_date: date
    termination_type: str = "Resignation"
    reason: Optional[str] = None
    final_pay_amount: Optional[float] = None


class TerminationUpdate(BaseModel):
    status: Optional[str] = None
    exit_interview_notes: Optional[str] = None
    final_pay_amount: Optional[float] = None


class TerminationOut(BaseModel):
    id: int
    employee_id: int
    last_working_date: date
    termination_type: str
    reason: Optional[str] = None
    status: str
    exit_interview_notes: Optional[str] = None
    final_pay_amount: Optional[float] = None
    initiated_by: Optional[int] = None
    initiated_at: Optional[datetime] = None
    decided_by: Optional[int] = None
    decided_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    items: list["OffboardingItemOut"] = []

    class Config:
        from_attributes = True


class OffboardingItemUpdate(BaseModel):
    name: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class OffboardingItemOut(BaseModel):
    id: int
    termination_id: int
    task_id: Optional[int] = None
    name: str
    category: str
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    status: str
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


TerminationOut.model_rebuild()
