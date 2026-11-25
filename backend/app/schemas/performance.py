from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class GoalCreate(BaseModel):
    employee_id: int
    title: str
    description: Optional[str] = None
    weight: float = 0
    progress: float = 0
    status: str = "Not Started"
    due_date: Optional[date] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    weight: Optional[float] = None
    progress: Optional[float] = None
    status: Optional[str] = None
    due_date: Optional[date] = None


class GoalOut(GoalCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PerformanceReviewCreate(BaseModel):
    employee_id: int
    reviewer_id: Optional[int] = None
    period: str
    status: str = "Draft"
    overall_rating: Optional[float] = None
    manager_comments: Optional[str] = None
    employee_comments: Optional[str] = None


class PerformanceReviewUpdate(BaseModel):
    reviewer_id: Optional[int] = None
    status: Optional[str] = None
    overall_rating: Optional[float] = None
    manager_comments: Optional[str] = None
    employee_comments: Optional[str] = None


class PerformanceReviewOut(PerformanceReviewCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewFeedbackCreate(BaseModel):
    review_id: int
    from_employee_id: Optional[int] = None
    feedback_type: str = "Peer"
    rating: Optional[float] = None
    comments: Optional[str] = None


class ReviewFeedbackOut(ReviewFeedbackCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompensationBandCreate(BaseModel):
    job_id: int
    level: str
    min_salary: float = 0
    mid_salary: float = 0
    max_salary: float = 0
    currency: str = "INR"


class CompensationBandOut(CompensationBandCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeritCycleCreate(BaseModel):
    name: str
    year: int
    budget_percent: float = 0
    start_date: date
    end_date: date
    status: str = "Draft"


class MeritCycleOut(MeritCycleCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeritAllocationCreate(BaseModel):
    cycle_id: int
    employee_id: int
    current_salary: float = 0
    proposed_salary: float = 0
    increase_percent: float = 0
    status: str = "Draft"


class MeritAllocationOut(MeritAllocationCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
