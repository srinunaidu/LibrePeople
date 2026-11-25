from datetime import date, datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel


class ViolationKind(str, Enum):
    EARLY_ARRIVAL = "early_arrival"
    LATE_ARRIVAL = "late_arrival"
    EARLY_DEPARTURE = "early_departure"
    LATE_DEPARTURE = "late_departure"
    MISSING_ENTRY = "missing_entry"
    EXTRA_ENTRY = "extra_entry"


class ViolationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class WorkingTimeViolationOut(BaseModel):
    id: int
    employee_id: int
    work_date: date
    roster_entry_id: Optional[int] = None
    time_entry_id: Optional[int] = None
    kind: ViolationKind
    severity: ViolationSeverity
    minutes: int
    detected_at: datetime
    resolved: bool

    class Config:
        from_attributes = True


class ClockIn(BaseModel):
    employee_id: int
    work_date: Optional[date] = None
    source: str = "Web"
    notes: Optional[str] = None


class ClockOut(BaseModel):
    employee_id: int
    notes: Optional[str] = None


class TimeEntryCreate(BaseModel):
    employee_id: int
    work_date: date
    clock_in: datetime
    clock_out: Optional[datetime] = None
    break_minutes: int = 0
    source: str = "Manual"
    notes: Optional[str] = None
    roster_entry_id: Optional[int] = None


class TimeEntryUpdate(BaseModel):
    work_date: Optional[date] = None
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    break_minutes: Optional[int] = None
    source: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    roster_entry_id: Optional[int] = None


class TimeEntryOut(BaseModel):
    id: int
    employee_id: int
    work_date: date
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    break_minutes: int
    worked_hours: float
    overtime_hours: float
    source: str
    status: str
    notes: Optional[str] = None
    roster_entry_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimesheetGenerate(BaseModel):
    employee_id: int
    period_start: date
    period_end: date


class TimesheetOut(BaseModel):
    id: int
    employee_id: int
    period_start: date
    period_end: date
    total_hours: float
    overtime_hours: float
    entry_count: int
    status: str
    generated_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CorrectionStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class TimeCorrectionCreate(BaseModel):
    employee_id: int
    time_entry_id: Optional[int] = None
    work_date: date
    requested_clock_in: Optional[datetime] = None
    requested_clock_out: Optional[datetime] = None
    reason: Optional[str] = None


class TimeCorrectionOut(BaseModel):
    id: int
    employee_id: int
    time_entry_id: Optional[int] = None
    work_date: date
    requested_clock_in: Optional[datetime] = None
    requested_clock_out: Optional[datetime] = None
    reason: Optional[str] = None
    status: CorrectionStatus
    requested_by: Optional[int] = None
    decided_by: Optional[int] = None
    decided_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PeriodLockCreate(BaseModel):
    period_start: date
    period_end: date


class PeriodLockOut(BaseModel):
    id: int
    period_start: date
    period_end: date
    is_locked: bool
    locked_by: Optional[int] = None
    locked_at: Optional[datetime] = None
    reopened_by: Optional[int] = None
    reopened_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PeriodStatusOut(BaseModel):
    period_start: date
    period_end: date
    is_locked: bool
