from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.time_attendance import TimeEntryOut, ViolationKind, ViolationSeverity, WorkingTimeViolationOut


class ShiftTemplateCreate(BaseModel):
    name: str
    code: str
    start_time: str
    end_time: str
    break_minutes: int = 0
    is_night: bool = False
    is_active: bool = True


class ShiftTemplateUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    break_minutes: Optional[int] = None
    is_night: Optional[bool] = None
    is_active: Optional[bool] = None


class ShiftTemplateOut(ShiftTemplateCreate):
    id: int

    class Config:
        from_attributes = True


class RosterEntryCreate(BaseModel):
    employee_id: int
    work_date: date
    shift_template_id: Optional[int] = None
    start_time: str
    end_time: str
    is_night: bool = False
    notes: Optional[str] = None


class RosterEntryUpdate(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_night: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class RosterEntryOut(BaseModel):
    id: int
    employee_id: int
    work_date: date
    shift_template_id: Optional[int] = None
    start_time: str
    end_time: str
    is_night: bool
    status: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class RosterGenerate(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    shift_template_id: int


# --- New schemas for solver-based roster generation ---

class EmployeeProblem(BaseModel):
    """Employee definition for the solver problem."""
    id: int
    skills: List[str] = Field(default_factory=list)
    max_hours_per_day: float = 8.0
    max_hours_per_week: float = 40.0
    locations: List[str] = Field(default_factory=list)
    unavailable_dates: List[date] = Field(default_factory=list)
    preferences: Dict[str, float] = Field(default_factory=dict)
    cost_per_slot: float = 0.0
    night_ok: bool = True


class SlotProblem(BaseModel):
    """Slot (demand) definition for the solver problem."""
    id: str
    date: date
    location: Optional[str] = None
    role: Optional[str] = None
    skill: Optional[str] = None
    start_time: str = "09:00"
    end_time: str = "17:00"
    is_night: bool = False
    headcount: int = 1
    required: bool = False
    cost: Optional[float] = None


class ConstraintsProblem(BaseModel):
    """Hard constraints for the solver."""
    max_shifts_per_employee: Optional[int] = None
    max_weekly_hours: Optional[float] = None
    min_rest_hours: float = 11.0
    max_consecutive_days: int = 6
    labour_limits: Dict[str, int] = Field(default_factory=dict)


class RosterGenerateRequest(BaseModel):
    """Request to generate a draft roster via the solver."""
    start_date: date
    end_date: date
    location_code: str
    employees: List[EmployeeProblem]
    slots: List[SlotProblem]
    constraints: Optional[ConstraintsProblem] = None
    weights: Optional[Dict[str, float]] = None
    time_limit_seconds: float = 60.0


class WeightBreakdown(BaseModel):
    """Weight breakdown from the solver."""
    fairness: Dict[str, Any] = Field(default_factory=dict)
    preference: int = 0
    cost: float = 0.0
    continuity: int = 0
    weights: Dict[str, float] = Field(default_factory=dict)


class SolverMetadata(BaseModel):
    """Solver run metadata."""
    solver: str = "ortools-cp-sat"
    status: str
    time_limit_seconds: int
    solve_time_ms: int
    objective_value: Optional[float] = None
    evaluated_nodes: int = 0
    input_hash: str


class UnfilledSlot(BaseModel):
    """An unfilled slot with its cause."""
    slot_id: str
    date: date
    location: Optional[str] = None
    role: Optional[str] = None
    headcount: int
    cause: str
    blocking_constraint: Optional[str] = None
    constraint: Optional[str] = None


class RosterGenerateResponse(BaseModel):
    """Response from roster generation with draft ID and solver output."""
    draft_id: int
    status: str
    solver_status: str
    timed_out: bool
    objective_value: Optional[float] = None
    weight_breakdown: WeightBreakdown
    assignments: List[Dict[str, Any]]
    roster: List[Dict[str, Any]]
    unfilled_slots: List[UnfilledSlot]
    unfilled: List[UnfilledSlot]
    input_hash: str


class RosterDraftOut(BaseModel):
    """Full draft roster data for manager review."""
    draft_id: int
    location_code: Optional[str] = None
    period_start: date
    period_end: date
    status: str
    solver_status: Optional[str] = None
    created_at: datetime
    problem: Dict[str, Any]
    result: Dict[str, Any]
    assignments: List[Dict[str, Any]]
    roster: List[Dict[str, Any]]
    unfilled_slots: List[UnfilledSlot]
    unfilled: List[UnfilledSlot]
    weight_breakdown: WeightBreakdown
    objective_value: Optional[float] = None
    input_hash: str


class AdjustmentAction(BaseModel):
    """Manual assignment adjustment."""
    slot_instance_id: str
    employee_id: Optional[int] = None
    action: str = "reassign"  # assign, unassign, reassign


class AdjustmentResponse(BaseModel):
    """Response from a manual adjustment."""
    draft_id: int
    assignments: List[Dict[str, Any]]
    unfilled_slots: List[UnfilledSlot]
    violations: List[str]
    valid: bool


class RosterPublishRequest(BaseModel):
    """Request to publish a draft roster."""
    draft_id: int
    publish_at: Optional[datetime] = None
    notify: bool = True


class RosterVersionOut(BaseModel):
    """Published roster version."""
    id: int
    location_code: Optional[str] = None
    period_start: date
    period_end: date
    status: str
    published_by: Optional[int] = None
    published_at: Optional[datetime] = None
    solver_status: Optional[str] = None
    created_at: datetime
    entry_count: int = 0
    unfilled_count: int = 0

    class Config:
        from_attributes = True


class RosterVersionDetailOut(RosterVersionOut):
    """Roster version with full entries and solver data."""
    entries: List[RosterEntryOut] = Field(default_factory=[])
    problem: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    assignments: List[Dict[str, Any]] = Field(default_factory=[])
    unfilled_slots: List[UnfilledSlot] = Field(default_factory=[])
    weight_breakdown: Optional[WeightBreakdown] = None
    objective_value: Optional[float] = None
    input_hash: str = ""


class RosterVersionListParams(BaseModel):
    """Query parameters for listing roster versions."""
    location_code: Optional[str] = None
    status: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class PaginatedRosterVersions(BaseModel):
    items: List[RosterVersionOut]
    meta: Dict[str, Any]


class VersionDiffEntry(BaseModel):
    """A single entry in a version comparison diff."""
    type: str  # "added", "removed", "changed"
    entry: Optional[RosterEntryOut] = None
    base_entry: Optional[RosterEntryOut] = None
    changes: Dict[str, Any] = Field(default_factory=dict)


class VersionCompareResponse(BaseModel):
    """Response from comparing two roster versions."""
    version_id: int
    base_version_id: int
    added: List[VersionDiffEntry] = Field(default_factory=[])
    removed: List[VersionDiffEntry] = Field(default_factory=[])
    changed: List[VersionDiffEntry] = Field(default_factory=[])
    summary: Dict[str, int] = Field(default_factory=dict)


class CreateDraftFromVersionRequest(BaseModel):
    """Request to create a new draft from a published version."""
    new_period_start: Optional[date] = None
    new_period_end: Optional[date] = None
    notes: Optional[str] = None


class CreateDraftFromVersionResponse(BaseModel):
    """Response from creating a draft from a version."""
    draft_id: int
    status: str
    location_code: Optional[str] = None
    period_start: date
    period_end: date
    created_at: datetime


# --- Leave-to-roster availability schemas -----------------------------------

class LeaveBlockedDay(BaseModel):
    """One day an approved leave request blocks, with the leave reference."""
    date: date
    leave_request_id: int
    leave_type_id: int
    leave_type_code: Optional[str] = None


class LeaveReference(BaseModel):
    """The leave request behind a run of blocked days, quantified."""
    leave_request_id: int
    leave_type_id: int
    leave_type_code: Optional[str] = None
    start_date: date
    end_date: date
    days: int


class EmployeeAvailability(BaseModel):
    """Per-employee availability over the queried window."""
    employee_id: int
    available_dates: List[date] = Field(default_factory=list)
    unavailable_dates: List[LeaveBlockedDay] = Field(default_factory=list)
    leave_requests: List[LeaveReference] = Field(default_factory=list)


class AvailabilityResponse(BaseModel):
    """Availability for the queried window: leave subtracted, references shown."""
    start_date: date
    end_date: date
    employees: List[EmployeeAvailability] = Field(default_factory=list)


class SwapCreate(BaseModel):
    roster_entry_id: int
    target_id: Optional[int] = None
    proposed_date: Optional[date] = None


class SwapOut(BaseModel):
    id: int
    roster_entry_id: int
    requester_id: int
    target_id: Optional[int] = None
    proposed_date: Optional[date] = None
    status: str
    decided_by: Optional[int] = None
    decided_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Attendance integration schemas ---

class RosterAttendanceEntry(BaseModel):
    """A roster entry with its linked time entry (if any)."""
    roster_entry: RosterEntryOut
    time_entry: Optional[TimeEntryOut] = None


class RosterAttendanceResponse(BaseModel):
    """Attendance data for a published roster version."""
    version_id: int
    location_code: Optional[str] = None
    period_start: date
    period_end: date
    entries: List[RosterAttendanceEntry]
    summary: Dict[str, int]  # total, matched, missing, extra


class AutoCreateAttendanceRequest(BaseModel):
    """Request to auto-create time entries from roster (kiosk mode)."""
    source: str = "Kiosk"  # Source identifier for auto-created entries
    tz: Optional[str] = None  # IANA zone for roster wall times; default UTC


class AutoCreateAttendanceResponse(BaseModel):
    """Response from auto-creating attendance."""
    version_id: int
    created_count: int
    skipped_count: int
    entries: List[TimeEntryOut]


class DeviationEntry(BaseModel):
    """A single deviation (violation) for a roster entry."""
    roster_entry: RosterEntryOut
    time_entry: Optional[TimeEntryOut] = None
    violations: List[WorkingTimeViolationOut]


class DeviationsResponse(BaseModel):
    """Deviations for a published roster version."""
    version_id: int
    location_code: Optional[str] = None
    period_start: date
    period_end: date
    deviations: List[DeviationEntry]
    summary: Dict[str, int]  # by kind and severity
