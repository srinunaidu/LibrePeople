from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, ALL_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.presets.diff import diff_preset
from app.core.presets.loader import load_all_presets, load_preset
from app.core.presets.provenance import provenance_report
from app.core.presets.readiness import check_readiness, read_facts
from app.core.presets.tenant_state import read_state
from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.models.user import User
from app.schemas.onboarding import (
    OnboardingTaskCreate,
    OnboardingTaskUpdate,
    OnboardingTaskOut,
    OnboardingDocumentOut,
    OnboardingDocumentUpdate,
    OnboardingSummary,
    PresetDetailOut,
    PresetDifferenceOut,
    PresetSummaryOut,
    ReadinessFindingOut,
    ReadinessOut,
)
from app.crud.crud_onboarding import (
    get_task,
    get_tasks_for_employee,
    create_task,
    update_task,
    get_document,
    get_documents_for_employee,
    create_document,
    update_document,
    apply_default_checklist,
)
from app.crud.crud_employee import get_employee
from app.services import notifications as notify
from app.services.storage import get_storage

router = APIRouter()


def _notify_onboarding(db: Session, task) -> None:
    """Notify the employee whose onboarding task just completed."""
    recipient = notify.user_id_for_employee(db, task.employee_id)
    if recipient is None:
        return
    notify.emit(
        db,
        recipient_user_id=recipient,
        title=f"Onboarding task completed: {task.title}",
        message=f"Your onboarding task '{task.title}' is now marked Completed.",
        notification_type="success",
        category="onboarding",
        entity_type="onboarding_task",
        entity_id=task.id,
    )


# --------------------------------------------------------------------------
# Presets, the difference report and the readiness check
# --------------------------------------------------------------------------
#
# These four operations are read-only. A preset is a suggestion the
# customer may refuse, so the server reports what a preset would change
# before anything changes, and the readiness check changes nothing at all.
#
# They are registered before the employee-onboarding routes below, so that
# `/onboarding/presets` is never read as an employee identifier.


def _now() -> str:
    """The timestamp the reports carry, in UTC."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _preset_summary(preset) -> PresetSummaryOut:
    organisation = preset.document.get("organisation_templates") or {}
    return PresetSummaryOut(
        id=preset.preset_id,
        name=preset.name,
        industry=preset.business_type,
        modules=preset.module_keys,
        default_roles=list(organisation.get("roles") or []),
        recommended_settings={
            "version": preset.version,
            "status": preset.status,
            "enabled_by_default": preset.enabled_by_default,
        },
        version=preset.version,
        status=preset.status,
        description=preset.description,
    )


def _preset_detail(preset) -> PresetDetailOut:
    organisation = preset.document.get("organisation_templates") or {}
    graph = preset.graph()
    summary = _preset_summary(preset)
    return PresetDetailOut(
        **summary.model_dump(),
        business_type=preset.business_type,
        created_at=str(preset.document.get("created_at", "")),
        updated_at=str(preset.document.get("updated_at", "")),
        module_dependencies={
            module: list(graph.dependencies(module)) for module in graph.modules
        },
        organisation_templates=organisation,
        dashboards=preset.document.get("dashboards") or {},
        forecast_drivers=preset.document.get("forecast_drivers") or {},
        import_templates=list(preset.document.get("import_templates") or []),
        validations=list(preset.validations),
        exclusions=list(preset.exclusions),
        configuration=preset.configuration,
        preset=preset.document,
    )


@router.get("/presets", response_model=list[PresetSummaryOut], operation_id="onboardingListPresets")
def list_presets(
    page: int = Query(1, ge=1, description="1-based page number."),
    page_size: int = Query(50, ge=1, le=200, description="Rows per page."),
    industry: str | None = Query(
        None, description="Only the presets of this business type."
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """List the configuration presets.

    The presets are the catalogue of starting configurations, one per kind
    of business. The list is paged. A preset that does not exist, or that
    breaks its contract, is not served: the catalogue is either right or it
    is not served at all.
    """
    presets = [
        preset
        for preset in load_all_presets()
        if industry is None or preset.business_type == industry
    ]
    start = (page - 1) * page_size
    return [_preset_summary(preset) for preset in presets[start : start + page_size]]


@router.get("/presets/{preset_id}", response_model=PresetDetailOut, operation_id="onboardingGetPreset")
def read_preset(
    preset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Read one configuration preset.

    The whole document is returned: the modules and their dependency edges,
    the organisation templates, the shift templates, the leave types, the
    dashboards and the indicators, the forecast drivers, the import
    templates, the validations and the exclusions.
    """
    return _preset_detail(load_preset(preset_id))


@router.get("/presets/{preset_id}/diff", response_model=PresetDifferenceOut, operation_id="onboardingGetPresetDiff")
def read_preset_difference(
    preset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Report what the preset would change, and what it would leave alone.

    Nothing is changed. The report says what the preset adds, what it
    leaves alone, what it would overwrite and what it cannot decide, and
    it carries the provenance of every setting: whether the value came
    from the preset, was set by the customer, or is the customer's change
    to a value the preset suggested.

    The customer's own configuration always wins. A value in
    ``overwrites`` is reported so that the difference is visible; the
    customer's value is the one that stands.
    """
    preset = load_preset(preset_id)
    state = read_state(db)
    difference = diff_preset(preset, state)
    records = provenance_report(preset, state)
    return PresetDifferenceOut(
        preset_id=difference.preset_id,
        preset_version=difference.preset_version,
        adds=[change.as_dict() for change in difference.adds],
        unchanged=[change.as_dict() for change in difference.unchanged],
        overwrites=[change.as_dict() for change in difference.overwrites],
        undecided=[change.as_dict() for change in difference.undecided],
        modules_to_enable=list(difference.modules_to_enable),
        modules_left_alone=list(difference.modules_left_alone),
        exclusions=[dict(item) for item in difference.exclusions],
        provenance=[record.as_dict() for record in records],
        generated_at=_now(),
    )


@router.get("/readiness", response_model=ReadinessOut, operation_id="onboardingGetReadiness")
def read_readiness(
    preset_id: str | None = Query(
        None,
        description=(
            "The preset to judge the setup against. When it is not given, the "
            "preset the deployment has chosen is used."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Report what is configured, what is missing, what is inconsistent and
    what is merely recommended.

    The check reads. It changes nothing: no module is switched on, no
    setting is written, and no record is created.
    """
    state = read_state(db)
    preset = None
    if preset_id:
        preset = load_preset(preset_id)
    elif state.preset_id:
        preset = load_preset(state.preset_id, document=state.preset_document)
    report = check_readiness(state, preset, read_facts(db))
    return ReadinessOut(
        preset_id=report.preset_id,
        preset_version=report.preset_version,
        configured=[finding.as_dict() for finding in report.configured],
        missing=[finding.as_dict() for finding in report.missing],
        inconsistent=[finding.as_dict() for finding in report.inconsistent],
        recommended=[finding.as_dict() for finding in report.recommended],
        findings=[finding.as_dict() for finding in report.findings],
        generated_at=_now(),
    )


def _summary(db: Session, employee_id: int) -> OnboardingSummary:
    tasks = get_tasks_for_employee(db, employee_id)
    documents = get_documents_for_employee(db, employee_id)
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == "Completed")
    percent = int((completed / total) * 100) if total else 0
    return OnboardingSummary(
        employee_id=employee_id,
        total_tasks=total,
        completed_tasks=completed,
        progress_percent=percent,
        documents_uploaded=len(documents),
    )


@router.get("/{employee_id}/summary", response_model=OnboardingSummary, operation_id="onboardingGetOnboardingsummary")
def read_onboarding_summary(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    if not get_employee(db, employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    ensure_can_view_employee(db, current_user, employee_id)
    return _summary(db, employee_id)


@router.post(
    "/{employee_id}/checklist",
    response_model=list[OnboardingTaskOut],
    status_code=201, operation_id="onboardingCreateOnboardingchecklist")
def create_default_checklist(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Create the standard onboarding checklist for an employee."""
    if not get_employee(db, employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    return apply_default_checklist(db, employee_id)


@router.get("/{employee_id}/tasks", response_model=list[OnboardingTaskOut], operation_id="onboardingListOnboardingtasks")
def read_tasks(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    ensure_can_view_employee(db, current_user, employee_id)
    return get_tasks_for_employee(db, employee_id)


@router.post("/tasks", response_model=OnboardingTaskOut, status_code=201, operation_id="onboardingCreateOnboardingtasks")
def create_task_endpoint(
    task_in: OnboardingTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if not get_employee(db, task_in.employee_id):
        raise HTTPException(status_code=400, detail="Employee not found")
    task = create_task(db=db, task_in=task_in)
    record_audit(
        db, current_user, "create_onboarding_task", "OnboardingTask", task.id,
        details="employee_id=" + str(task_in.employee_id) + " title=" + str(task_in.title),
    )
    db.commit()
    return task


@router.put("/tasks/{task_id}", response_model=OnboardingTaskOut, operation_id="onboardingUpdateOnboardingtasks")
def update_task_endpoint(
    task_id: int,
    task_in: OnboardingTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    was_completed = (task.status == "Completed")
    task = update_task(db=db, db_obj=task, task_in=task_in)
    record_audit(
        db, current_user, "update_onboarding_task", "OnboardingTask", task.id,
        details="status=" + str(task.status),
    )
    # The crossing into Completed is the milestone worth announcing: the
    # employee's checklist moved. Any other edit, or a second write of an
    # already-completed task, stays silent (the duplicate guard agrees).
    if task.status == "Completed" and not was_completed:
        _notify_onboarding(db, task)
    db.commit()
    return task


@router.get("/{employee_id}/documents", response_model=list[OnboardingDocumentOut], operation_id="onboardingListOnboardingdocuments")
def read_documents(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    ensure_can_view_employee(db, current_user, employee_id)
    return get_documents_for_employee(db, employee_id)


@router.post(
    "/{employee_id}/documents",
    response_model=OnboardingDocumentOut,
    status_code=201,
    operation_id="onboardingCreateOnboardingdocuments",
)
async def upload_document(
    employee_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if not get_employee(db, employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")

    data = await file.read()
    storage = get_storage()
    key = f"onboarding/{employee_id}/{document_type}/{file.filename}"
    url = storage.save(
        key, data, content_type=file.content_type or "application/octet-stream"
    )
    return create_document(
        db,
        employee_id=employee_id,
        document_type=document_type,
        file_name=file.filename or key,
        storage_url=url,
    )


@router.put("/documents/{document_id}", response_model=OnboardingDocumentOut, operation_id="onboardingUpdateOnboardingdocuments")
def update_document_endpoint(
    document_id: int,
    document_in: OnboardingDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    document = get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    document = update_document(db=db, db_obj=document, document_in=document_in)
    record_audit(
        db, current_user, "update_onboarding_document", "OnboardingDocument",
        document.id, details="status=" + str(document.status),
    )
    db.commit()
    return document
