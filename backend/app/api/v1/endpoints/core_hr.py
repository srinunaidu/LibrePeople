from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.booleans import is_true
from app.api.deps import ADMIN_ROLES, ALL_ROLES, WORKFORCE_ROLES, get_db, require_roles, tenant_id_for
from app.api.v1.endpoints.auth import client_ip
from app.core.audit import record_audit
from app.core.errors import ApiError, ErrorCategory, conflict, not_found, validation
from app.core.ids import next_code
from app.core.tenancy import DEFAULT_TENANT_SLUG, tenant_column_criterion, tenant_matches
from app.core.master_data import (
    count_dependents,
    ensure_reference,
    ensure_unique_natural_key,
    load_or_404,
    refuse_if_in_use,
    refuse_null_updates,
)
from app.core.rate_limit import limiter
from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.services import notifications as notify
from app.workflows import service as wf_service
from app.models.core_hr import (
    CaseComment,
    CostCenter,
    DocumentAck,
    DocumentVersion,
    EmployeeDocument,
    HRCase,
    LegalEntity,
    Location,
    Position,
)
from app.storage.backends import AUTHORISED_FILES_PREFIX
from app.models.department import Department
from app.models.job import Job
from app.models.learning import SuccessionPlan
from app.models.user import User
from app.schemas.core_hr import (
    CaseCommentCreate,
    CaseCommentOut,
    CostCenterCreate,
    CostCenterOut,
    CostCenterUpdate,
    DocumentAckOut,
    DocumentVersionCreate,
    DocumentVersionOut,
    EmployeeDocumentCreate,
    EmployeeDocumentOut,
    HRCaseCreate,
    HRCaseOut,
    HRCaseUpdate,
    LegalEntityCreate,
    LegalEntityOut,
    LegalEntityUpdate,
    LocationCreate,
    LocationOut,
    LocationUpdate,
    PositionCreate,
    PositionUpdate,
    PublicContactAccepted,
    PublicContactCreate,
    PositionOut,
)

router = APIRouter()


def _crud(model, schema_out, schema_in):
    pass


# --- Locations ------------------------------------------------------------ #

#: What points at a location. Forecasts keep their row when a location goes
#: away (their foreign key is ``ON DELETE SET NULL``), so they are not a
#: blocker; positions are, because a position names the site it sits at.
_LOCATION_DEPENDENTS = (("positions", Position, Position.location_id),)

#: A position is self-referencing: another position can report to it.
_POSITION_DEPENDENTS = (
    ("positions", Position, Position.reports_to_position_id),
    ("succession_plans", SuccessionPlan, SuccessionPlan.position_id),
)


@router.get("/locations", response_model=list[LocationOut], operation_id="coreHrListCorehrlocations")
def list_locations(db: Session = Depends(get_db), include_inactive: bool = False, u: User = Depends(require_roles(*ALL_ROLES))):
    """Locations, by code.

    `include_inactive` lets the maintenance list see an archived location so
    that it can restore it; the forms that offer a location want the live ones.
    """
    query = db.query(Location)
    if not include_inactive:
        query = query.filter(is_true(Location.is_active))
    return query.order_by(Location.code).all()


@router.post("/locations", response_model=LocationOut, status_code=201, operation_id="coreHrCreateCorehrlocations")
def create_location(payload: LocationCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    location_code = (payload.code or "").strip() or next_code(db, Location, Location.code, "LOC-")
    payload = payload.model_copy(update={"code": location_code})
    ensure_unique_natural_key(db, Location, Location.code, location_code, label="Location")
    obj = Location(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_location", "Location", obj.id, details=f"code={obj.code}"); db.commit()
    return obj


@router.get("/locations/{location_id}", response_model=LocationOut, operation_id="coreHrGetLocation")
def read_location(location_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ALL_ROLES))):
    return load_or_404(db, Location, location_id, "Location")


@router.patch("/locations/{location_id}", response_model=LocationOut, operation_id="coreHrUpdateLocation")
def update_location(location_id: int, payload: LocationUpdate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Edit a location, including restoring an archived one."""
    obj = load_or_404(db, Location, location_id, "Location")
    changes = payload.model_dump(exclude_unset=True)
    refuse_null_updates(changes, ("name", "code", "timezone", "is_active"), "Location")
    if "code" in changes:
        ensure_unique_natural_key(
            db, Location, Location.code, changes["code"], exclude_id=location_id, label="Location"
        )
    for field, value in changes.items():
        setattr(obj, field, value)
    db.add(obj)
    record_audit(db, u, "update_location", "Location", obj.id, details=",".join(sorted(changes)) or "no change")
    db.commit(); db.refresh(obj)
    return obj


@router.delete("/locations/{location_id}", status_code=204, operation_id="coreHrDeleteLocation")
def delete_location(location_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Delete a location no position sits at; refuse one that a position does."""
    obj = load_or_404(db, Location, location_id, "Location")
    refuse_if_in_use(count_dependents(db, _LOCATION_DEPENDENTS, location_id), "Location", location_id)
    db.delete(obj)
    record_audit(db, u, "delete_location", "Location", location_id, details="deleted")
    db.commit()
    return None


# --- Cost centers ----------------------------------------------------------- #

@router.get("/cost-centers", response_model=list[CostCenterOut], operation_id="coreHrListCorehrcostcenters")
def list_cost_centers(db: Session = Depends(get_db), include_inactive: bool = False, u: User = Depends(require_roles(*ALL_ROLES))):
    query = db.query(CostCenter)
    if not include_inactive:
        query = query.filter(is_true(CostCenter.is_active))
    return query.order_by(CostCenter.code).all()


@router.post("/cost-centers", response_model=CostCenterOut, status_code=201, operation_id="coreHrCreateCorehrcostcenters")
def create_cost_center(payload: CostCenterCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    if payload.department_id is not None:
        ensure_reference(db, Department, payload.department_id, "Department")
    cc_code = (payload.code or "").strip() or next_code(db, CostCenter, CostCenter.code, "CC-")
    payload = payload.model_copy(update={"code": cc_code})
    ensure_unique_natural_key(db, CostCenter, CostCenter.code, cc_code, label="CostCenter")
    obj = CostCenter(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_cost_center", "CostCenter", obj.id, details=f"code={obj.code}"); db.commit()
    return obj


@router.get("/cost-centers/{cost_center_id}", response_model=CostCenterOut, operation_id="coreHrGetCostCenter")
def read_cost_center(cost_center_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ALL_ROLES))):
    return load_or_404(db, CostCenter, cost_center_id, "CostCenter")


@router.patch("/cost-centers/{cost_center_id}", response_model=CostCenterOut, operation_id="coreHrUpdateCostCenter")
def update_cost_center(cost_center_id: int, payload: CostCenterUpdate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Edit a cost centre, including restoring an archived one."""
    obj = load_or_404(db, CostCenter, cost_center_id, "CostCenter")
    changes = payload.model_dump(exclude_unset=True)
    refuse_null_updates(changes, ("code", "name", "is_active"), "CostCenter")
    if "department_id" in changes and changes["department_id"] is not None:
        ensure_reference(db, Department, changes["department_id"], "Department")
    if "code" in changes:
        ensure_unique_natural_key(
            db, CostCenter, CostCenter.code, changes["code"], exclude_id=cost_center_id, label="CostCenter"
        )
    for field, value in changes.items():
        setattr(obj, field, value)
    db.add(obj)
    record_audit(db, u, "update_cost_center", "CostCenter", obj.id, details=",".join(sorted(changes)) or "no change")
    db.commit(); db.refresh(obj)
    return obj


@router.delete("/cost-centers/{cost_center_id}", status_code=204, operation_id="coreHrDeleteCostCenter")
def delete_cost_center(cost_center_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = load_or_404(db, CostCenter, cost_center_id, "CostCenter")
    record_audit(db, u, "delete_cost_center", "CostCenter", cost_center_id, details="deleted")
    db.delete(obj); db.commit()
    return None


# --- Legal entities ----------------------------------------------------------- #
#
# LP-CORE-003/010: one installation holds many legal entities. The rows are
# tenant-scoped — a caller sees only their own tenant's entities — and
# deletion is a soft-deactivate: the row stays so that employees hired under
# it keep their history, while the forms stop offering it.

def _ensure_unique_legal_entity_code(
    db: Session, code: str, exclude_id: int | None = None
) -> None:
    """Refuse a second legal entity carrying the same code in one tenant.

    Tenant-scoped: the same code may exist in two tenants, but never twice
    in one. The comparison is case-insensitive. A NULL ``tenant_id``
    denotes a pre-backfill row belonging to the legacy default tenant, so
    a default-tenant request matches both NULL and ``"default"`` rows,
    while any other tenant matches only its own rows. A global check would
    leak existence across tenants (a 409 for a code the caller may not
    see); this check only ever compares within the caller's bucket.
    """
    if code is None:
        return
    wanted = str(code).strip()
    if not wanted:
        return
    query = (
        db.query(func.count())
        .select_from(LegalEntity)
        .filter(func.lower(LegalEntity.code) == func.lower(wanted))
    )
    if exclude_id is not None:
        query = query.filter(LegalEntity.id != exclude_id)
    tenant_id = tenant_id_for(db) or DEFAULT_TENANT_SLUG
    if tenant_id == DEFAULT_TENANT_SLUG:
        query = query.filter(
            or_(
                LegalEntity.tenant_id == tenant_id,
                LegalEntity.tenant_id.is_(None),
            )
        )
    else:
        query = query.filter(LegalEntity.tenant_id == tenant_id)
    if query.scalar():
        raise conflict(
            "duplicate_natural_key",
            f"LegalEntity already uses the code {wanted!r}. Codes are unique.",
            entity="legalentity",
            value=wanted,
        )


def _load_legal_entity(db: Session, entity_id: int) -> LegalEntity:
    """Load one legal entity, refusing another tenant's row fail-closed."""
    obj = load_or_404(db, LegalEntity, entity_id, "LegalEntity")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(obj, "tenant_id", None), tenant_id
    ):
        # The record exists but belongs to another tenant: refuse fail-closed
        # without confirming its existence.
        raise not_found("LegalEntity")
    return obj


@router.get("/legal-entities", response_model=list[LegalEntityOut], operation_id="coreHrListLegalEntities")
def list_legal_entities(db: Session = Depends(get_db), include_inactive: bool = False, u: User = Depends(require_roles(*ALL_ROLES))):
    """Legal entities, by code.

    Tenant-scoped: a caller sees only their own tenant's entities (plus
    pre-backfill rows for the legacy default tenant). `include_inactive`
    lets the maintenance list see a deactivated entity so it can restore it.
    """
    query = db.query(LegalEntity)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        query = query.filter(tenant_column_criterion(LegalEntity.tenant_id, tenant_id))
    if not include_inactive:
        query = query.filter(is_true(LegalEntity.is_active))
    return query.order_by(LegalEntity.code).all()


@router.post("/legal-entities", response_model=LegalEntityOut, status_code=201, operation_id="coreHrCreateLegalEntities")
def create_legal_entity(payload: LegalEntityCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    entity_code = (payload.code or "").strip() or next_code(db, LegalEntity, LegalEntity.code, "LE-")
    payload = payload.model_copy(update={"code": entity_code})
    _ensure_unique_legal_entity_code(db, entity_code)
    obj = LegalEntity(**payload.model_dump())
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not getattr(obj, "tenant_id", None):
        obj.tenant_id = tenant_id
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_legal_entity", "LegalEntity", obj.id, details=f"code={obj.code}"); db.commit()
    return obj


@router.get("/legal-entities/{legal_entity_id}", response_model=LegalEntityOut, operation_id="coreHrGetLegalEntity")
def read_legal_entity(legal_entity_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ALL_ROLES))):
    return _load_legal_entity(db, legal_entity_id)


@router.patch("/legal-entities/{legal_entity_id}", response_model=LegalEntityOut, operation_id="coreHrUpdateLegalEntity")
def update_legal_entity(legal_entity_id: int, payload: LegalEntityUpdate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Edit a legal entity, including restoring a deactivated one."""
    obj = _load_legal_entity(db, legal_entity_id)
    changes = payload.model_dump(exclude_unset=True)
    refuse_null_updates(changes, ("name", "code", "is_active"), "LegalEntity")
    if "code" in changes:
        _ensure_unique_legal_entity_code(
            db, changes["code"], exclude_id=legal_entity_id
        )
    for field, value in changes.items():
        setattr(obj, field, value)
    db.add(obj)
    record_audit(db, u, "update_legal_entity", "LegalEntity", obj.id, details=",".join(sorted(changes)) or "no change")
    db.commit(); db.refresh(obj)
    return obj


@router.delete("/legal-entities/{legal_entity_id}", status_code=204, operation_id="coreHrDeleteLegalEntities")
def delete_legal_entity(legal_entity_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Soft-deactivate a legal entity.

    The row is kept — employees hired under it keep their history — and only
    `is_active` flips to false, so the forms stop offering it. Restoring is
    `PATCH is_active: true`. Deactivating an already-inactive entity is a
    no-op success.
    """
    obj = _load_legal_entity(db, legal_entity_id)
    if is_true(obj.is_active):
        obj.is_active = False
        db.add(obj)
    record_audit(db, u, "deactivate_legal_entity", "LegalEntity", legal_entity_id, details="deactivated")
    db.commit()
    return None


# --- Positions -------------------------------------------------------------- #

@router.get("/positions", response_model=list[PositionOut], operation_id="coreHrListCorehrpositions")
def list_positions(db: Session = Depends(get_db), include_inactive: bool = False, u: User = Depends(require_roles(*ALL_ROLES))):
    query = db.query(Position)
    if not include_inactive:
        query = query.filter(is_true(Position.is_active))
    return query.order_by(Position.code).all()


@router.post("/positions", response_model=PositionOut, status_code=201, operation_id="coreHrCreateCorehrpositions")
def create_position(payload: PositionCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    ensure_reference(db, Job, payload.job_id, "Job")
    ensure_reference(db, Department, payload.department_id, "Department")
    if payload.location_id is not None:
        ensure_reference(db, Location, payload.location_id, "Location")
    pos_code = (payload.code or "").strip() or next_code(db, Position, Position.code, "POS-")
    payload = payload.model_copy(update={"code": pos_code})
    ensure_unique_natural_key(db, Position, Position.code, pos_code, label="Position")
    if payload.fte is not None and (float(payload.fte) <= 0 or float(payload.fte) > 1):
        raise validation(
            "validation_error",
            "fte must be greater than 0 and at most 1.",
            entity="Position",
            fields=["fte"],
            fte=float(payload.fte),
        )
    obj = Position(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_position", "Position", obj.id, details=f"code={obj.code}"); db.commit()
    return obj


@router.get("/positions/{position_id}", response_model=PositionOut, operation_id="coreHrGetPosition")
def read_position(position_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ALL_ROLES))):
    return load_or_404(db, Position, position_id, "Position")


@router.patch("/positions/{position_id}", response_model=PositionOut, operation_id="coreHrUpdatePosition")
def update_position(position_id: int, payload: PositionUpdate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Edit a position, including restoring an archived one."""
    obj = load_or_404(db, Position, position_id, "Position")
    changes = payload.model_dump(exclude_unset=True)
    refuse_null_updates(
        changes,
        ("code", "title", "job_id", "department_id", "fte", "is_active"),
        "Position",
    )
    if "job_id" in changes:
        ensure_reference(db, Job, changes["job_id"], "Job")
    if "department_id" in changes:
        ensure_reference(db, Department, changes["department_id"], "Department")
    if changes.get("location_id") is not None:
        ensure_reference(db, Location, changes["location_id"], "Location")
    if "code" in changes:
        ensure_unique_natural_key(
            db, Position, Position.code, changes["code"], exclude_id=position_id, label="Position"
        )
    if changes.get("reports_to_position_id") == position_id:
        raise validation(
            "validation_error",
            "A position may not report to itself.",
            entity="Position",
            fields=["reports_to_position_id"],
            id=position_id,
        )
    if changes.get("fte") is not None and (
        float(changes["fte"]) <= 0 or float(changes["fte"]) > 1
    ):
        raise validation(
            "validation_error",
            "fte must be greater than 0 and at most 1.",
            entity="Position",
            fields=["fte"],
            fte=float(changes["fte"]),
        )
    for field, value in changes.items():
        setattr(obj, field, value)
    db.add(obj)
    record_audit(db, u, "update_position", "Position", obj.id, details=",".join(sorted(changes)) or "no change")
    db.commit(); db.refresh(obj)
    return obj


@router.delete("/positions/{position_id}", status_code=204, operation_id="coreHrDeletePosition")
def delete_position(position_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Delete a position nothing reports to or plans succession for."""
    obj = load_or_404(db, Position, position_id, "Position")
    refuse_if_in_use(count_dependents(db, _POSITION_DEPENDENTS, position_id), "Position", position_id)
    db.delete(obj)
    record_audit(db, u, "delete_position", "Position", position_id, details="deleted")
    db.commit()
    return None


# --- Employee documents (LP-DOC-002: versioned, acknowledged, logged) ------ #

def _storage_key_for(storage_url: str | None, storage_key: str | None) -> str | None:
    """The opaque storage key for an upload.

    The caller may name the key outright. Otherwise it is derived from the
    stored URL by stripping the authorised ``/api/v1/files/`` prefix: that
    prefix is the route that serves the key, so whatever carries it names a
    key. A URL that carries no prefix names no key.
    """
    if storage_key and storage_key.strip():
        return storage_key.strip()
    if storage_url and storage_url.startswith(AUTHORISED_FILES_PREFIX):
        key = storage_url[len(AUTHORISED_FILES_PREFIX):].strip()
        return key or None
    return None


@router.get("/employee-documents", response_model=list[EmployeeDocumentOut], operation_id="coreHrListCorehremployeedocuments")
def list_employee_documents(employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(EmployeeDocument)
    q = apply_visibility(q, EmployeeDocument.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(EmployeeDocument.employee_id == employee_id)
    return q.order_by(EmployeeDocument.uploaded_at.desc()).all()


@router.post("/employee-documents", response_model=EmployeeDocumentOut, status_code=201, operation_id="coreHrCreateCorehremployeedocuments")
def create_employee_document(payload: EmployeeDocumentCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    data = payload.model_dump()
    key = _storage_key_for(payload.storage_url, payload.storage_key)
    data["storage_key"] = key
    data["current_version"] = 1
    obj = EmployeeDocument(**data)
    db.add(obj)
    db.flush()
    db.add(
        DocumentVersion(
            document_id=obj.id,
            version_no=1,
            file_name=obj.file_name,
            storage_key=key,
            storage_url=obj.storage_url,
            uploaded_by=u.username,
        )
    )
    db.commit(); db.refresh(obj)
    record_audit(db, u, "create_employee_document", "EmployeeDocument", obj.id); db.commit()
    return obj


@router.get(
    "/employee-documents/{document_id}/versions",
    response_model=list[DocumentVersionOut],
    operation_id="coreHrListDocumentVersions",
)
def list_document_versions(document_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    """The upload history of a document, oldest first.

    The first upload is version 1; every further upload appends the next
    number, so the rows behind a document are its ordered history.
    """
    doc = load_or_404(db, EmployeeDocument, document_id, "EmployeeDocument")
    ensure_can_view_employee(db, u, doc.employee_id)
    return (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_no.asc())
        .all()
    )


@router.post(
    "/employee-documents/{document_id}/versions",
    response_model=DocumentVersionOut,
    status_code=201,
    operation_id="coreHrCreateDocumentVersion",
)
def upload_document_version(document_id: int, payload: DocumentVersionCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Upload a new version of a document's content.

    Appends the next version row and moves the document onto it: the file
    name, URL and key always describe the newest upload, while the older
    rows stay as the history.
    """
    doc = load_or_404(db, EmployeeDocument, document_id, "EmployeeDocument")
    key = _storage_key_for(payload.storage_url, payload.storage_key)
    version_no = (doc.current_version or 0) + 1
    version = DocumentVersion(
        document_id=doc.id,
        version_no=version_no,
        file_name=payload.file_name,
        storage_key=key,
        storage_url=payload.storage_url,
        uploaded_by=u.username,
    )
    doc.current_version = version_no
    doc.file_name = payload.file_name
    doc.storage_url = payload.storage_url
    if key is not None:
        doc.storage_key = key
    db.add(version)
    db.add(doc)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent upload won the same version number (uq_docver_doc_ver).
        # Roll back so the session is usable, then refuse as a conflict.
        db.rollback()
        raise conflict(
            "version_conflict",
            f"Document {document_id} was modified concurrently. Reload and try again.",
            entity="DocumentVersion",
            document_id=document_id,
        )
    db.refresh(version)
    record_audit(db, u, "upload_document_version", "DocumentVersion", version.id, details=f"document={doc.id} version={version_no}"); db.commit()
    return version


@router.post(
    "/employee-documents/{document_id}/ack",
    response_model=DocumentAckOut,
    status_code=201,
    operation_id="coreHrAckDocument",
)
def acknowledge_document(document_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    """Acknowledge a document, once per account.

    A second acknowledgement by the same account is refused with 409: "I
    have read this" is one accountable event, not a counter.
    """
    doc = load_or_404(db, EmployeeDocument, document_id, "EmployeeDocument")
    ensure_can_view_employee(db, u, doc.employee_id)
    existing = (
        db.query(DocumentAck)
        .filter(
            DocumentAck.document_id == document_id,
            DocumentAck.acknowledged_by == u.username,
        )
        .first()
    )
    if existing is not None:
        raise conflict(
            "already_acknowledged",
            f"Document {document_id} was already acknowledged by {u.username}.",
            entity="DocumentAck",
            document_id=document_id,
        )
    ack = DocumentAck(document_id=doc.id, acknowledged_by=u.username)
    db.add(ack)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent acknowledgement by the same account won the race
        # (uq_docack_doc_user). Roll back so the session is usable, then
        # refuse exactly like the already-acknowledged check above.
        db.rollback()
        raise conflict(
            "already_acknowledged",
            f"Document {document_id} was already acknowledged by {u.username}.",
            entity="DocumentAck",
            document_id=document_id,
        )
    db.refresh(ack)
    record_audit(db, u, "acknowledge_document", "DocumentAck", ack.id, details=f"document={doc.id}"); db.commit()
    wf_service.record_mirror(
        db, actor=u, entity_type="document", entity_id=doc.id,
        action="APPROVE", stage="APPROVED",
        comment=f"Acknowledged by {u.username}.",
        recipient_user_id=notify.user_id_for_employee(db, doc.employee_id),
        audit_action="workflow_mirror_document_ack",
    )
    return ack


# --- The public intake ------------------------------------------------------ #

#: The budget for one address: a handful of messages in ten minutes.
#:
#: The endpoint is unauthenticated and it writes to the database, so the
#: rate limit is not an enhancement here: it is the control. The daily cap
#: underneath it is the second line, for a flood that is slow enough to
#: stay under the first one.
CONTACT_RATE_LIMIT = 5
CONTACT_RATE_WINDOW_SECONDS = 600
CONTACT_DAILY_LIMIT = 20
CONTACT_DAILY_WINDOW_SECONDS = 86_400

#: The largest body the intake accepts.
#:
#: Sixteen kilobytes is far more than the three fields need and far less
#: than a flood needs.
CONTACT_MAX_BODY_BYTES = 16_384

limiter.set_policy("contact", CONTACT_RATE_LIMIT, CONTACT_RATE_WINDOW_SECONDS)
limiter.set_policy("contact_daily", CONTACT_DAILY_LIMIT, CONTACT_DAILY_WINDOW_SECONDS)

#: The router for the public door.
#:
#: It is separate from the case queue's router because it is a different
#: thing: the queue is behind a token, this is not, and nothing about this
#: door reaches the queue's data.
public_router = APIRouter()


def _limit_the_body(request: Request) -> None:
    """Refuse a body that is larger than the intake accepts.

    This is a dependency and not part of the handler, because a dependency
    is resolved before the body is validated: a body that is too large is
    refused as too large, and not as a field that is too long.
    """
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > CONTACT_MAX_BODY_BYTES:
        raise ApiError(
            "payload_too_large",
            "The message is too large to accept.",
            ErrorCategory.VALIDATION,
            status_code=413,
        )


@public_router.post(
    "/contact",
    response_model=PublicContactAccepted,
    status_code=201,
    dependencies=[Depends(_limit_the_body)], operation_id="publicContact")
def public_contact(
    payload: PublicContactCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Receive a message from the public contact form.

    The form is on the marketing site, which has no token, so it cannot use
    the case queue's endpoint: that one is behind a bearer token and has
    answered 401 for every visitor since the role policy was applied. This
    is the door for the form instead, and it is deliberately narrow:

    * **three fields, and nothing else.** The schema is closed, so a
      request that carries an employee id, a tenant id, a case category or a
      comment is refused rather than quietly stored.
    * **no case of its own.** The message becomes a case in the intake
      state, with no employee, no category and no priority, so the queue
      can pick it up and it can never be mistaken for a case about a
      person.
    * **the rate limit is the control.** The endpoint is unauthenticated and
      writes to the database, so a flood is the expected failure rather
      than an exception.
    * **nothing personal in the logs.** The audit row records the case and
      the source; it records neither the address nor the message.
    """
    address = client_ip(request)
    limiter.check("contact", request, address)
    limiter.check("contact_daily", request, address)

    # Extra lead fields are folded into the stored message so the case
    # is self-contained without a schema migration for transient lead data.
    extra_lines: list[str] = []
    if payload.company:
        extra_lines.append(f"Company: {payload.company}")
    if payload.company_size:
        extra_lines.append(f"Size: {payload.company_size}")
    if payload.interest:
        extra_lines.append(f"Interest: {payload.interest}")
    if payload.phone:
        extra_lines.append(f"Phone: {payload.phone}")
    stored_message = payload.message
    if extra_lines:
        stored_message = "\n".join(extra_lines) + "\n\n" + payload.message

    case = HRCase(
        subject=payload.name[:200],
        category="Public Contact",
        priority="Medium",
        status="Intake",
        source="public_contact",
        sender_email=str(payload.email),
        message=stored_message,
    )
    db.add(case)
    db.flush()
    db.refresh(case)
    # The audit row names the case and the source. It does not name the
    # sender and it does not carry the message: the audit trail is read by
    # more people than the queue is.
    record_audit(
        db,
        None,
        "public_contact_received",
        "HRCase",
        case.id,
        details="source=public_contact",
    )
    db.commit()
    return PublicContactAccepted(received=True)


# --- HR cases (LP-SVC-001+003: helpdesk) -------------------------------------- #
#
# LP-SVC-001: cases carry a category, a priority, an assignee and a status.
# LP-SVC-002 (SLA measurement and escalation) is explicitly out of scope:
# ``sla_due`` is stored and returned, and nothing reads it.
# LP-SVC-003: a case is visible only to its participants — HR (and
# SuperAdmin) see every case, anyone else sees only cases about themselves
# (``employee_id``) or assigned to them (``assigned_to``). Anything else is
# refused with 404, never 403, so the response cannot confirm the case
# exists. Comments are append-only: there is no update or delete route for
# them, so the rows behind a case are its history.

#: The forward-only status machine (LP-SVC-001). One step at a time:
#: a case moves Open > InProgress > Resolved > Closed, and resolving
#: requires a resolution. ``Intake`` is the public form's lane, not a step
#: of this machine: nothing transitions into or out of it here.
CASE_NEXT_STATUS: dict[str, set[str]] = {
    "Open": {"InProgress"},
    "InProgress": {"Resolved"},
    "Resolved": {"Closed"},
    "Closed": set(),
    "Intake": set(),
}

#: The status rows written before the machine canonicalised the name.
#: Read as the canonical step so old rows can still move forward.
LEGACY_IN_PROGRESS = "In Progress"


def _is_helpdesk_admin(u: User) -> bool:
    """True when this account sees every case (LP-SVC-003).

    HR and SuperAdmin — the :data:`ADMIN_ROLES` set — work the whole queue.
    """
    return u.role in ADMIN_ROLES


def _ensure_can_access_case(u: User, case: HRCase) -> None:
    """Raise 404 unless `u` may read this case (LP-SVC-003).

    HR sees every case. Anyone else sees only a case about themselves or
    assigned to them. A 404 — not a 403 — avoids confirming that the case
    exists to someone who may not know about it.
    """
    if _is_helpdesk_admin(u):
        return
    if (
        u.employee_id is not None
        and case.employee_id is not None
        and case.employee_id == u.employee_id
    ):
        return
    if case.assigned_to and case.assigned_to == u.username:
        return
    raise HTTPException(status_code=404, detail="Case not found")


def _validate_case_attachment(payload: CaseCommentCreate) -> None:
    """Refuse a comment attachment that is half-formed or mis-pointed."""
    filename, key = payload.attachment_filename, payload.attachment_key
    if (filename is None) != (key is None):
        raise validation(
            "validation_error",
            "attachment_filename and attachment_key must be sent together.",
            entity="CaseComment",
            fields=["attachment_filename", "attachment_key"],
        )
    if key is None:
        return
    if not filename or not filename.strip():
        raise validation(
            "validation_error",
            "attachment_filename must not be blank when attachment_key is sent.",
            entity="CaseComment",
            fields=["attachment_filename"],
        )
    if not key.startswith(AUTHORISED_FILES_PREFIX):
        raise validation(
            "validation_error",
            f"attachment_key must name a key under {AUTHORISED_FILES_PREFIX}.",
            entity="CaseComment",
            fields=["attachment_key"],
        )


@router.get("/cases", response_model=list[HRCaseOut], operation_id="coreHrListCorehrcases")
def list_cases(status: str | None = None, employee_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    q = db.query(HRCase)
    if _is_helpdesk_admin(u):
        q = apply_visibility(q, HRCase.employee_id, u, db)
    else:
        # LP-SVC-003: anyone who is not HR sees only their own cases and
        # the ones assigned to them — never the queue, never a colleague's.
        clauses = [HRCase.assigned_to == u.username]
        if u.employee_id is not None:
            clauses.append(HRCase.employee_id == u.employee_id)
        q = q.filter(or_(*clauses))
        if employee_id is not None and employee_id != u.employee_id:
            raise HTTPException(status_code=404, detail="Case not found")
    if status:
        q = q.filter(HRCase.status == status)
    else:
        # The intake state holds the messages the public form sent. They are
        # not cases about an employee, so the queue does not show them among
        # its own; they are asked for by name.
        q = q.filter(HRCase.status != "Intake")
    if employee_id:
        if _is_helpdesk_admin(u):
            ensure_can_view_employee(db, u, employee_id)
        q = q.filter(HRCase.employee_id == employee_id)
    return q.order_by(HRCase.created_at.desc()).all()


@router.post("/cases", response_model=HRCaseOut, status_code=201, operation_id="coreHrCreateCorehrcases")
def create_case(payload: HRCaseCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    obj = HRCase(**payload.model_dump())
    if not _is_helpdesk_admin(u):
        # LP-SVC-003: a non-admin creates only a case about themselves. A
        # payload that asks for someone else is refused, not silently
        # rewritten, so the caller cannot think the case is about a
        # colleague. An account with no employee link cannot raise one.
        if u.employee_id is None:
            raise HTTPException(
                status_code=403,
                detail="Your account is not linked to an employee record",
            )
        if payload.employee_id is not None and payload.employee_id != u.employee_id:
            raise HTTPException(
                status_code=403,
                detail="You may only create a case about yourself",
            )
        obj.employee_id = u.employee_id
        # LP-SVC-003: routing and SLA are the helpdesk's to set. A
        # non-admin may not drop their case into a colleague's queue
        # (``assigned_to`` also grants visibility) or invent a deadline,
        # and self-service priority is capped at Medium.
        obj.assigned_to = None
        obj.sla_due = None
        if obj.priority not in ("Low", "Medium"):
            obj.priority = "Medium"
    elif payload.employee_id is not None:
        # HR and SuperAdmin may open a case for any employee in scope.
        ensure_can_view_employee(db, u, payload.employee_id)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_hr_case", "HRCase", obj.id); db.commit()
    return obj


@router.put("/cases/{case_id}", response_model=HRCaseOut, operation_id="coreHrUpdateCorehrcases")
def update_case(case_id: int, payload: HRCaseUpdate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = db.query(HRCase).filter(HRCase.id == case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    _ensure_can_access_case(u, obj)
    changes = payload.model_dump(exclude_unset=True)
    current = "InProgress" if obj.status == LEGACY_IN_PROGRESS else obj.status
    target = changes.get("status")
    if target is not None and target != obj.status and target != current:
        # LP-SVC-001: the machine moves forward one step at a time. The
        # Intake lane is not a step: nothing moves into or out of it here.
        if target not in CASE_NEXT_STATUS.get(current, set()):
            raise validation(
                "invalid_status_transition",
                f"Case cannot move from {current} to {target}.",
                entity="HRCase",
                fields=["status"],
                case_id=case_id,
            )
        if target == "Resolved":
            effective = changes.get("resolution", obj.resolution)
            if not effective or not str(effective).strip():
                raise validation(
                    "resolution_required",
                    "Resolving a case requires a resolution.",
                    entity="HRCase",
                    fields=["resolution"],
                    case_id=case_id,
                )
    for f, v in changes.items():
        setattr(obj, f, v)
    if obj.status in ("Resolved", "Closed") and not obj.resolved_at:
        from datetime import datetime, timezone
        obj.resolved_at = datetime.now(timezone.utc)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "update_hr_case", "HRCase", obj.id); db.commit()
    if changes.get("status") == "Resolved":
        wf_service.record_mirror(
            db, actor=u, entity_type="hr_case", entity_id=obj.id,
            action="APPROVE", stage="APPROVED",
            comment=(changes.get("resolution") or obj.resolution or "Case resolved.")[:500],
            due_at=obj.sla_due,
            recipient_user_id=notify.user_id_for_employee(db, obj.employee_id),
            audit_action="workflow_mirror_hr_resolve",
        )
    return obj


@router.post("/cases/{case_id}/comments", response_model=CaseCommentOut, status_code=201, operation_id="coreHrCreateCorehrcasescomments")
def add_case_comment(case_id: int, payload: CaseCommentCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    """Append a comment to a case (LP-SVC-001+003).

    Append-only: there is no update or delete route for comments, so a
    comment once written stays as written. Participants may comment on
    their own cases — the requester replying is the point of the queue —
    while anyone else is refused with 404.
    """
    case = db.query(HRCase).filter(HRCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _ensure_can_access_case(u, case)
    _validate_case_attachment(payload)
    obj = CaseComment(
        case_id=case_id,
        author=payload.author,
        comment=payload.comment,
        attachment_filename=payload.attachment_filename,
        attachment_key=payload.attachment_key,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "add_case_comment", "CaseComment", obj.id); db.commit()
    return obj


@router.get("/cases/{case_id}/comments", response_model=list[CaseCommentOut], operation_id="coreHrListCorehrcasescomments")
def list_case_comments(case_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))):
    case = db.query(HRCase).filter(HRCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _ensure_can_access_case(u, case)
    return db.query(CaseComment).filter(CaseComment.case_id == case_id).order_by(CaseComment.created_at).all()
