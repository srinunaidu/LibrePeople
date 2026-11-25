from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ComplianceRuleCreate(BaseModel):
    code: str
    name: str
    category: str = "Labor Law"
    description: Optional[str] = None
    severity: str = "Medium"
    is_active: bool = True


class ComplianceRuleOut(ComplianceRuleCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ComplianceViolationCreate(BaseModel):
    employee_id: Optional[int] = None
    rule_id: int
    status: str = "Open"
    notes: Optional[str] = None


class ComplianceViolationOut(ComplianceViolationCreate):
    id: int
    detected_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HeadcountPlanCreate(BaseModel):
    name: str
    year: int
    department_id: Optional[int] = None
    planned_headcount: int = 0
    actual_headcount: int = 0
    budget: Optional[float] = None
    notes: Optional[str] = None


class HeadcountPlanOut(HeadcountPlanCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    base_plan_id: Optional[int] = None
    adjustments_json: Optional[str] = None


class ScenarioOut(ScenarioCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportDefinitionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    query: str
    filters_json: Optional[str] = None


class ReportDefinitionOut(ReportDefinitionCreate):
    id: int
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SavedReportCreate(BaseModel):
    definition_id: Optional[int] = None
    name: str
    result_json: Optional[str] = None


class SavedReportOut(SavedReportCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
