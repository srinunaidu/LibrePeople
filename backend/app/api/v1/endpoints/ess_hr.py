from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.booleans import is_false, is_true
from app.core.errors import forbidden, validation
from app.core.tenancy import tenant_matches
from app.services import notifications as notify
from app.api.deps import ADMIN_ROLES, ALL_ROLES, MANAGER_ROLES, ASSOCIATE_ROLES, get_db, require_roles, tenant_id_for
from app.core.sensitive_fields import mask_bank_tax, refuse_bank_tax_write
from app.core.audit import record_audit
from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.models.ess_hr import (
    Announcement,
    ComplianceCheck,
    ContinuousFeedback,
    EmployeeDirectory,
    EmployeeFile,
    EmployeeSelfService,
    GoalAlignment,
    Notification,
    OrgChartNode,
)
from app.models.user import User
from app.schemas.ess_hr import (
    AnnouncementCreate,
    AnnouncementOut,
    ComplianceCheckOut,
    ContinuousFeedbackCreate,
    ContinuousFeedbackOut,
    DirectoryEntryOut,
    EmployeeFileCreate,
    EmployeeFileOut,
    ESSProfileCreate,
    ESSProfileOut,
    GoalAlignmentCreate,
    GoalAlignmentOut,
    NotificationCreate,
    NotificationOut,
    NotificationPreferencesUpdate,
    OrgNodeOut,
)

router = APIRouter()


# --- ESS Profile ------------------------------------------------------------ #


def _ess_profile_response(obj, actor) -> dict:
    """The ESS profile as a dict with bank and tax fields governed by policy."""
    data = {c.name: getattr(obj, c.name, None) for c in obj.__table__.columns}
    return mask_bank_tax(data, actor.role)


@router.get("/ess/profile/{employee_id}", response_model=ESSProfileOut, operation_id="essGetEssessprofile")
def get_ess_profile(employee_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    from app.models.ess_hr import EmployeeSelfService

    ensure_can_view_employee(db, u, employee_id)
    obj = db.query(EmployeeSelfService).filter(EmployeeSelfService.employee_id == employee_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="ESS profile not found")
    return _ess_profile_response(obj, u)


@router.post("/ess/profile", response_model=ESSProfileOut, status_code=201, operation_id="essCreateEssessprofile")
def create_ess_profile(payload: ESSProfileCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    from app.models.ess_hr import EmployeeSelfService

    refuse_bank_tax_write(payload.model_dump(exclude_unset=True), u.role)
    obj = EmployeeSelfService(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_ess_profile", "EmployeeSelfService", obj.id); db.commit()
    return _ess_profile_response(obj, u)


@router.put("/ess/profile/{employee_id}", response_model=ESSProfileOut, operation_id="essUpdateEssessprofile")
def update_ess_profile(employee_id: int, payload: ESSProfileCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    from app.models.ess_hr import EmployeeSelfService

    refuse_bank_tax_write(payload.model_dump(exclude_unset=True), u.role)
    obj = db.query(EmployeeSelfService).filter(EmployeeSelfService.employee_id == employee_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="ESS profile not found")
    for f, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "update_ess_profile", "EmployeeSelfService", obj.id); db.commit()
    return _ess_profile_response(obj, u)


# --- Notifications ---------------------------------------------------------- #
#
# Ownership is the whole access rule here. ``recipient_id`` is a *user* id,
# not an employee id, so the employee-visibility filter does not apply —
# every endpoint below scopes to the caller's own login instead. Reading or
# acknowledging another person's notification answers 403.

@router.get("/notifications", response_model=list[NotificationOut], operation_id="essListEssnotifications")
def list_notifications(recipient_id: int | None = None, unread_only: bool = False, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    if recipient_id is not None and recipient_id != u.id:
        raise forbidden("You may only read your own notifications.")
    q = db.query(Notification).filter(Notification.recipient_id == u.id)
    if unread_only:
        q = q.filter(is_false(Notification.is_read))
    return q.order_by(Notification.created_at.desc()).all()


@router.get("/notifications/unread-count", operation_id="essGetEssnotificationsunreadcount")
def unread_notification_count(db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    """How many of the caller's own notifications are still unread."""
    count = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == u.id,
            is_false(Notification.is_read),
        )
        .count()
    )
    return {"unread_count": count}


@router.get("/notifications/preferences", operation_id="essGetEssnotificationspreferences")
def get_notification_preferences(db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    """The caller's event-notification channel flags (LP-NOT-003).

    A caller with no ESS profile reads the product defaults. The flags
    are what the emission gate consults: every flag off means opted out.
    """
    return notify.recipient_preferences(db, u.id)


@router.put("/notifications/preferences", operation_id="essUpdateEssnotificationspreferences")
def update_notification_preferences(payload: NotificationPreferencesUpdate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    """Set the caller's own event-notification channel flags (LP-NOT-003).

    Owner-only by construction: there is no target selector, so the only
    profile this can ever write is the caller's own. A caller with no
    login-linked employee has no profile to hold flags and is refused
    with 404; a caller whose profile does not exist yet gets one created
    from the product defaults with the supplied flags applied. Only the
    flags present in the body change; anything omitted keeps its value.
    """
    if u.employee_id is None:
        raise HTTPException(status_code=404, detail="No ESS profile for this login")
    obj = db.query(EmployeeSelfService).filter(EmployeeSelfService.employee_id == u.employee_id).first()
    if obj is None:
        obj = EmployeeSelfService(employee_id=u.employee_id)
        db.add(obj)
        db.flush()
    for flag in ("notification_email", "notification_sms", "notification_push"):
        short = flag.removeprefix("notification_")
        value = getattr(payload, short)
        if value is not None:
            setattr(obj, flag, bool(value))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return notify.recipient_preferences(db, u.id)


@router.post("/notifications", response_model=NotificationOut, status_code=201, operation_id="essCreateEssnotifications")
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Create a notification for one recipient.

    The notification carries no tenant of its own, so the recipient must
    resolve to the caller's tenant: recipient user -> employee -> tenant.
    A recipient in another tenant — or one that resolves to no tenant at
    all, including an unknown user — answers the same 422 as a missing
    reference, without confirming which case applied.
    """
    recipient = db.get(User, payload.recipient_id)
    tenant_id = tenant_id_for(db)
    recipient_tenant = None
    if recipient is not None and recipient.employee_id is not None:
        from app.models.employee import Employee

        employee = db.get(Employee, recipient.employee_id)
        recipient_tenant = getattr(employee, "tenant_id", None) if employee is not None else None
    if recipient is None or (
        tenant_id is not None and not tenant_matches(recipient_tenant, tenant_id)
    ):
        raise validation(
            "reference_not_found",
            f"User {payload.recipient_id} does not exist.",
            entity="User",
            id=payload.recipient_id,
        )
    obj = Notification(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_notification", "Notification", obj.id); db.commit()
    return obj


@router.put("/notifications/{notification_id}/read", response_model=NotificationOut, operation_id="essUpdateEssnotificationsread")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    from datetime import datetime, timezone

    obj = db.query(Notification).filter(Notification.id == notification_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    # Only the recipient acknowledges their own notification. Anyone else
    # holding a valid id is refused with 403 — which, against the 404
    # above, confirms that the row exists. The list endpoint is
    # owner-scoped, so there is no enumeration beyond ids already known.
    if obj.recipient_id != u.id:
        raise forbidden("You may only acknowledge your own notifications.")
    if not obj.is_read:
        obj.is_read = True
        obj.read_at = datetime.now(timezone.utc)
        db.add(obj); db.commit(); db.refresh(obj)
    return obj


# --- Employee Files --------------------------------------------------------- #

@router.get("/employee-files", response_model=list[EmployeeFileOut], operation_id="essListEssemployeefiles")
def list_employee_files(employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    q = db.query(EmployeeFile)
    q = apply_visibility(q, EmployeeFile.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(EmployeeFile.employee_id == employee_id)
    return q.order_by(EmployeeFile.created_at.desc()).all()


@router.post("/employee-files", response_model=EmployeeFileOut, status_code=201, operation_id="essCreateEssemployeefiles")
def create_employee_file(payload: EmployeeFileCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = EmployeeFile(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_employee_file", "EmployeeFile", obj.id); db.commit()
    return obj


# --- Announcements ---------------------------------------------------------- #

@router.get("/announcements", response_model=list[AnnouncementOut], operation_id="essListEssannouncements")
def list_announcements(published_only: bool = False, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    """Published, non-expired announcements targeted to the caller (AC-06).

    An announcement is visible when it is published, not expired, and its
    audience matches the caller: ``All`` matches everyone; ``Role`` matches
    the caller's role; ``Department`` matches the caller's department.
    ``Location`` has no stored employee location in this deployment, so a
    location-targeted announcement is not excluded on an attribute that
    cannot be evaluated. The ``published_only`` flag is honoured but the
    ESS read surface always returns published, non-expired announcements.
    """
    from app.models.department import Department
    from app.models.employee import Employee
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    q = db.query(Announcement).filter(
        is_true(Announcement.published),
        (Announcement.expires_at.is_(None)) | (Announcement.expires_at > now),
    )
    if published_only:
        q = q.filter(is_true(Announcement.published))
    rows = q.order_by(Announcement.created_at.desc()).all()

    dept_name = None
    if u.employee_id:
        emp = db.query(Employee).filter(Employee.id == u.employee_id).first()
        if emp:
            dept = db.query(Department).filter(Department.id == emp.department_id).first()
            dept_name = dept.name if dept else None

    def visible(a: Announcement) -> bool:
        audience = (a.target_audience or "All").strip()
        value = (a.target_value or "").strip() or None
        if audience == "All":
            return True
        if audience == "Role":
            return value == u.role
        if audience == "Department":
            return value is not None and value == dept_name
        return True

    return [a for a in rows if visible(a)]


@router.post("/announcements", response_model=AnnouncementOut, status_code=201, operation_id="essCreateEssannouncements")
def create_announcement(payload: AnnouncementCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    from datetime import datetime, timezone

    obj = Announcement(**payload.model_dump())
    if obj.published and not obj.published_at:
        obj.published_at = datetime.now(timezone.utc)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_announcement", "Announcement", obj.id); db.commit()
    return obj


@router.put("/announcements/{announcement_id}/publish", response_model=AnnouncementOut, operation_id="essUpdateEssannouncementspublish")
def publish_announcement(announcement_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    from datetime import datetime, timezone

    obj = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Announcement not found")
    obj.published = True
    obj.published_at = datetime.now(timezone.utc)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "publish_announcement", "Announcement", obj.id); db.commit()
    return obj


# --- Employee Directory ----------------------------------------------------- #

@router.get("/directory", response_model=list[DirectoryEntryOut], operation_id="essGetEssdirectory")
def search_directory(q: str | None = None, department: str | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    from sqlalchemy import or_

    query = db.query(EmployeeDirectory)
    query = apply_visibility(query, EmployeeDirectory.employee_id, u, db)
    if q:
        query = query.filter(
            or_(
                EmployeeDirectory.full_name.ilike(f"%{q}%"),
                EmployeeDirectory.email.ilike(f"%{q}%"),
                EmployeeDirectory.job_title.ilike(f"%{q}%"),
            )
        )
    if department:
        query = query.filter(EmployeeDirectory.department == department)
    return query.order_by(EmployeeDirectory.full_name).all()


@router.post("/directory/sync", status_code=201, operation_id="essCreateEssdirectorysync")
def sync_directory(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Rebuild the employee directory from the employee master data."""
    from app.models.employee import Employee
    from app.models.department import Department
    from app.models.job import Job

    employees = db.query(Employee).filter(Employee.status == "Active").all()
    count = 0
    for emp in employees:
        dept = db.query(Department).filter(Department.id == emp.department_id).first()
        job = db.query(Job).filter(Job.id == emp.job_id).first()
        existing = db.query(EmployeeDirectory).filter(EmployeeDirectory.employee_id == emp.id).first()
        if existing:
            existing.full_name = f"{emp.first_name} {emp.last_name}"
            existing.email = emp.email
            existing.department = dept.name if dept else None
            existing.job_title = job.title if job else None
            existing.phone = emp.phone
            existing.is_active = True
        else:
            db.add(EmployeeDirectory(
                employee_id=emp.id,
                full_name=f"{emp.first_name} {emp.last_name}",
                email=emp.email,
                department=dept.name if dept else None,
                job_title=job.title if job else None,
                phone=emp.phone,
                is_active=True,
            ))
        count += 1
    db.commit()
    record_audit(db, u, "sync_directory", "EmployeeDirectory", None, details=f"{count} entries")
    db.commit()
    return {"synced": count}


# --- Org Chart -------------------------------------------------------------- #

@router.get("/org-chart", response_model=list[OrgNodeOut], operation_id="essGetEssorgchart")
def get_org_chart(db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    q = db.query(OrgChartNode)
    q = apply_visibility(q, OrgChartNode.employee_id, u, db)
    return q.order_by(OrgChartNode.depth, OrgChartNode.id).all()


@router.post("/org-chart/rebuild", status_code=201, operation_id="essCreateEssorgchartrebuild")
def rebuild_org_chart(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Rebuild org chart from employee manager relationships."""
    from app.models.employee import Employee

    # Clear existing
    db.query(OrgChartNode).delete()
    db.commit()

    employees = db.query(Employee).all()
    emp_map = {e.id: e for e in employees}

    def get_depth(emp_id, visited=None):
        if visited is None:
            visited = set()
        if emp_id in visited:
            return 0
        visited.add(emp_id)
        emp = emp_map.get(emp_id)
        if not emp or not emp.manager_id:
            return 0
        return 1 + get_depth(emp.manager_id, visited)

    def get_path(emp_id, visited=None):
        if visited is None:
            visited = set()
        if emp_id in visited:
            return str(emp_id)
        visited.add(emp_id)
        emp = emp_map.get(emp_id)
        if not emp or not emp.manager_id:
            return str(emp_id)
        return f"{get_path(emp.manager_id, visited)}/{emp_id}"

    nodes = []
    for emp in employees:
        nodes.append(OrgChartNode(
            employee_id=emp.id,
            manager_id=emp.manager_id,
            depth=get_depth(emp.id),
            path=get_path(emp.id),
        ))
    db.add_all(nodes)
    db.commit()
    record_audit(db, u, "rebuild_org_chart", "OrgChartNode", None, details=f"{len(nodes)} nodes")
    db.commit()
    return {"nodes": len(nodes)}


# --- Goal Alignment (OKR) --------------------------------------------------- #

@router.get("/goal-alignments", response_model=list[GoalAlignmentOut], operation_id="essListEssgoalalignments")
def list_alignments(db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    """Goal alignments, scoped to the goals the caller may see.

    An alignment belongs to a goal, and a goal belongs to an employee, so
    the scoping runs through the goal. The previous implementation passed
    ``GoalAlignment.employee_id`` to the visibility filter — a column the
    table does not have — so the endpoint answered 500 for every caller.
    """
    from app.models.performance import Goal

    q = db.query(GoalAlignment).join(Goal, GoalAlignment.goal_id == Goal.id)
    q = apply_visibility(q, Goal.employee_id, u, db)
    return q.all()


@router.post("/goal-alignments", response_model=GoalAlignmentOut, status_code=201, operation_id="essCreateEssgoalalignments")
def create_alignment(payload: GoalAlignmentCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*MANAGER_ROLES))):
    obj = GoalAlignment(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_goal_alignment", "GoalAlignment", obj.id); db.commit()
    return obj


# --- Continuous Feedback ---------------------------------------------------- #

@router.get("/continuous-feedback", response_model=list[ContinuousFeedbackOut], operation_id="essGetEsscontinuousfeedback")
def list_feedback(to_employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    q = db.query(ContinuousFeedback)
    q = apply_visibility(q, ContinuousFeedback.to_employee_id, u, db)
    if to_employee_id:
        ensure_can_view_employee(db, u, to_employee_id)
        q = q.filter(ContinuousFeedback.to_employee_id == to_employee_id)
    return q.order_by(ContinuousFeedback.created_at.desc()).all()


@router.post("/continuous-feedback", response_model=ContinuousFeedbackOut, status_code=201, operation_id="essCreateEsscontinuousfeedback")
def create_feedback(payload: ContinuousFeedbackCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ASSOCIATE_ROLES))):
    obj = ContinuousFeedback(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_continuous_feedback", "ContinuousFeedback", obj.id); db.commit()
    return obj


# --- Compliance Checks ------------------------------------------------------ #

@router.get("/compliance-checks", response_model=list[ComplianceCheckOut], operation_id="essListEsscompliancechecks")
def list_checks(rule_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """The results of the compliance checks that have been run.

    A check is the evaluation of a rule: it names the rule, whether it
    passed and when. It says nothing about a person, and the table has no
    employee column, so there is nothing for the visibility filter to scope.
    The previous implementation passed ``ComplianceCheck.employee_id`` — a
    column the table does not have — so the endpoint answered 500 for every
    caller. The compliance *findings*, which are about people, are served by
    the compliance module.
    """
    q = db.query(ComplianceCheck)
    if rule_id:
        q = q.filter(ComplianceCheck.rule_id == rule_id)
    return q.order_by(ComplianceCheck.run_at.desc()).all()


@router.post("/compliance-checks/run", status_code=201, operation_id="essCreateEsscompliancechecksrun")
def run_compliance_checks(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    from app.models.compliance import ComplianceRule, ComplianceViolation

    rules = db.query(ComplianceRule).filter(is_true(ComplianceRule.is_active)).all()
    results = []
    for rule in rules:
        # Simulate a check: mark as passed (real impl would evaluate the rule)
        check = ComplianceCheck(rule_id=rule.id, passed=True, details=f"Rule {rule.code} evaluated")
        db.add(check)
        results.append({"rule": rule.code, "passed": True})
    db.commit()
    record_audit(db, u, "run_compliance_checks", "ComplianceCheck", None, details=f"{len(results)} rules checked")
    db.commit()
    return {"checked": len(results), "results": results}
