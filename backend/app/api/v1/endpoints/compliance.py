from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, MANAGER_ROLES, WORKFORCE_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.models.compliance import (
    ComplianceRule,
    ComplianceViolation,
    HeadcountPlan,
    ReportDefinition,
    SavedReport,
    Scenario,
)
from app.models.user import User
from app.schemas.compliance import (
    ComplianceRuleCreate,
    ComplianceRuleOut,
    ComplianceViolationCreate,
    ComplianceViolationOut,
    HeadcountPlanCreate,
    HeadcountPlanOut,
    ReportDefinitionCreate,
    ReportDefinitionOut,
    SavedReportCreate,
    SavedReportOut,
    ScenarioCreate,
    ScenarioOut,
)

router = APIRouter()


# --- Compliance rules ------------------------------------------------------- #

@router.get("/compliance-rules", response_model=list[ComplianceRuleOut], operation_id="complianceListCompliancecompliancerules")
def list_rules(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    return db.query(ComplianceRule).order_by(ComplianceRule.code).all()


@router.post("/compliance-rules", response_model=ComplianceRuleOut, status_code=201, operation_id="complianceCreateCompliancecompliancerules")
def create_rule(payload: ComplianceRuleCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = ComplianceRule(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_compliance_rule", "ComplianceRule", obj.id); db.commit()
    return obj


# --- Violations ------------------------------------------------------------- #

@router.get("/compliance-violations", response_model=list[ComplianceViolationOut], operation_id="complianceListCompliancecomplianceviolations")
def list_violations(employee_id: int | None = None, status: str | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(ComplianceViolation)
    q = apply_visibility(q, ComplianceViolation.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(ComplianceViolation.employee_id == employee_id)
    if status:
        q = q.filter(ComplianceViolation.status == status)
    return q.order_by(ComplianceViolation.detected_at.desc()).all()


@router.post("/compliance-violations", response_model=ComplianceViolationOut, status_code=201, operation_id="complianceCreateCompliancecomplianceviolations")
def create_violation(payload: ComplianceViolationCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = ComplianceViolation(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_compliance_violation", "ComplianceViolation", obj.id); db.commit()
    return obj


@router.put("/compliance-violations/{violation_id}/resolve", response_model=ComplianceViolationOut, operation_id="complianceUpdateCompliancecomplianceviolationsresolve")
def resolve_violation(violation_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    from datetime import datetime, timezone

    obj = db.query(ComplianceViolation).filter(ComplianceViolation.id == violation_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Violation not found")
    obj.status = "Resolved"
    obj.resolved_at = datetime.now(timezone.utc)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "resolve_compliance_violation", "ComplianceViolation", obj.id); db.commit()
    return obj


# --- Headcount plans -------------------------------------------------------- #

@router.get("/headcount-plans", response_model=list[HeadcountPlanOut], operation_id="complianceListComplianceheadcountplans")
def list_plans(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    return db.query(HeadcountPlan).order_by(HeadcountPlan.year.desc()).all()


@router.post("/headcount-plans", response_model=HeadcountPlanOut, status_code=201, operation_id="complianceCreateComplianceheadcountplans")
def create_plan(payload: HeadcountPlanCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = HeadcountPlan(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_headcount_plan", "HeadcountPlan", obj.id); db.commit()
    return obj


# --- Scenarios -------------------------------------------------------------- #

@router.get("/scenarios", response_model=list[ScenarioOut], operation_id="complianceListCompliancescenarios")
def list_scenarios(db: Session = Depends(get_db), u: User = Depends(require_roles(*MANAGER_ROLES))):
    return db.query(Scenario).order_by(Scenario.id.desc()).all()


@router.post("/scenarios", response_model=ScenarioOut, status_code=201, operation_id="complianceCreateCompliancescenarios")
def create_scenario(payload: ScenarioCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = Scenario(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_scenario", "Scenario", obj.id); db.commit()
    return obj


# --- Report definitions ----------------------------------------------------- #

@router.get("/report-definitions", response_model=list[ReportDefinitionOut], operation_id="complianceListCompliancereportdefinitions")
def list_definitions(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    return db.query(ReportDefinition).order_by(ReportDefinition.id.desc()).all()


@router.post("/report-definitions", response_model=ReportDefinitionOut, status_code=201, operation_id="complianceCreateCompliancereportdefinitions")
def create_definition(payload: ReportDefinitionCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = ReportDefinition(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_report_definition", "ReportDefinition", obj.id); db.commit()
    return obj


@router.get("/saved-reports", response_model=list[SavedReportOut], operation_id="complianceListCompliancesavedreports")
def list_saved(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    return db.query(SavedReport).order_by(SavedReport.id.desc()).all()


@router.post("/saved-reports", response_model=SavedReportOut, status_code=201, operation_id="complianceCreateCompliancesavedreports")
def create_saved(payload: SavedReportCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = SavedReport(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "save_report", "SavedReport", obj.id); db.commit()
    return obj
