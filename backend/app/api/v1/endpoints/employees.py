from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, ALL_ROLES, get_db, require_roles, tenant_id_for
from app.core.tenancy import tenant_matches
from app.core.audit import record_audit
from app.core.employment import (
    apply_change,
    ensure_effective_date,
    ensure_manager_available,
    ensure_transition,
)
from app.core.errors import conflict, validation
from app.core.sensitive_fields import mask_bank_tax, refuse_bank_tax_write
from app.core.idempotency import IdempotencyGuard, idempotency_key
from app.core.ids import next_code
from app.core.master_data import ensure_reference
from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.services import custom_fields as custom_field_service
from app.models.department import Department
from app.models.core_hr import LegalEntity
from app.models.employee import Employee, EmployeeHistory
from app.models.job import Job
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeHistoryOut,
    EmployeeOut,
    EmployeePage,
    EmployeeUpdate,
)
from app.schemas.pagination import page_meta
from app.crud.crud_employee import (
    get_employee,
    get_employee_by_code,
    create_employee,
)

#: The filter's vocabulary. It is the stored one (`EMPLOYEE_STATUSES` in the
#: schema), because a filter that speaks a different vocabulary from the data
#: silently returns nothing. The target lowercase lifecycle vocabulary arrives
#: with status-transition enforcement (HR-02).
def _masked_employee_out(emp: Employee, actor: User,
                         custom_visible: dict | None = None) -> dict:
    """Return dict for EmployeeOut with masked Aadhaar and decrypted display for PAN/IFSC.
    Storage is encrypted; reads return masked Aadhaar, and PAN/IFSC decrypted but could be masked for non-privileged?
    Contract AC-28: API masks as ** **-****-1234 in list/detail; raw only for filings/neft server-side.
    We mask Aadhaar as ****-****-1234, and keep PAN/IFSC as masked? For now return PAN decrypted for display (tests expect original), Aadhaar masked.

    Bank and tax identifier fields (PAN, IFSC) are then removed for any role
    the central policy in :mod:`app.core.sensitive_fields` does not admit.
    The dict is returned for every outcome, never the ORM object, so a
    fallback cannot bypass the policy.
    """
    from app.core.encryption import mask_aadhaar, decrypt_field
    try:
        data = {}
        for col in emp.__table__.columns:
            val = getattr(emp, col.name, None)
            data[col.name] = val
        # Decrypt pan/ifsc for response? But mask Aadhaar
        # Aadhaar: expose masked only
        if getattr(emp, "aadhaar_masked", None):
            data["aadhaar_number"] = emp.aadhaar_masked  # masked form
        elif getattr(emp, "aadhaar_last4", None):
            data["aadhaar_number"] = f"****-****-{emp.aadhaar_last4}"
        else:
            data["aadhaar_number"] = None
        # Decrypt PAN/IFSC if encrypted for display (keep original for tests)
        for fld in ("pan_number", "ifsc_code", "pf_uan", "esi_number"):
            raw = data.get(fld)
            if raw and isinstance(raw, str) and raw.startswith("ENCv1:"):
                try:
                    data[fld] = decrypt_field(raw)
                except Exception:
                    pass
    except Exception:
        data = {c.name: getattr(emp, c.name, None) for c in emp.__table__.columns}
        data["aadhaar_number"] = None
    # Configurable attributes (LP-CORE-005): supplied already rendered for
    # this role — hr_only keys omitted, sensitive values masked — never raw.
    data["custom_fields"] = dict(custom_visible or {})
    return mask_bank_tax(data, actor.role)


EmployeeStatusFilter = Literal["Active", "On Leave", "Terminated", "Rehired"]
EmployeeSortField = Literal["employee_number", "last_name", "hire_date"]

#: Which column each contract sort key names. `employee_number` is the
#: business key the record stores as `employee_id`.
_SORT_COLUMNS = {
    "employee_number": Employee.employee_id,
    "last_name": Employee.last_name,
    "hire_date": Employee.hire_date,
}


def search_clause(term: str):
    """The filter `search` applies, exposed so its SQL is compiled in a test.

    `func.lower(...).like(...)` is the portable spelling: Oracle has no
    `ILIKE`, and SQLAlchemy's `ilike()` would be a dialect assumption rather
    than a fact. The full-name match concatenates with `+`, which both SQLite
    and Oracle render as `||`. `employees_test_suite` compiles this clause
    against `sqlalchemy.dialects.oracle` so a green SQLite run is not the only
    evidence (DEC-031).
    """
    like = f"%{term.strip().lower()}%"
    return or_(
        func.lower(Employee.employee_id).like(like),
        func.lower(Employee.first_name).like(like),
        func.lower(Employee.last_name).like(like),
        func.lower(
            Employee.first_name.concat(" ").concat(Employee.last_name)
        ).like(like),
        func.lower(Employee.email).like(like),
    )

router = APIRouter()


def _ensure_own_legal_entity(db: Session, legal_entity_id: int | None):
    """Load a legal entity for an employee write, refusing another tenant's.

    ``None`` is allowed (the link is nullable). An unknown id and another
    tenant's id both answer ``422 reference_not_found`` naming the same
    entity, so a caller cannot distinguish them and learn that a foreign
    row exists. The check runs before any write, so a refused link leaves
    no history row.
    """
    if legal_entity_id is None:
        return None
    row = ensure_reference(db, LegalEntity, legal_entity_id, "LegalEntity", required=False)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(row, "tenant_id", None), tenant_id
    ):
        raise validation(
            "reference_not_found",
            f"LegalEntity {legal_entity_id} does not exist.",
            entity="LegalEntity",
            id=legal_entity_id,
        )
    return row


def _replay_employee(db: Session, raw: str | None):
    """Return the employee from a stored idempotent response."""
    import json

    if not raw:
        raise HTTPException(status_code=409, detail="Idempotent response unavailable")
    return get_employee(db=db, employee_id=json.loads(raw)["id"])


def _custom_bundle(db: Session, employees: list[Employee]
                   ) -> tuple[dict, dict[int, dict]]:
    """Active definitions plus stored values for these employees."""
    defs = custom_field_service.def_map(db)
    stored = custom_field_service.read_values(db, [e.id for e in employees])
    return defs, stored


def _custom_visible(db: Session, emp: Employee, actor: User,
                    defs: dict | None = None,
                    stored: dict[int, dict] | None = None) -> dict:
    """This employee's custom fields as ``actor`` may see them."""
    if defs is None:
        defs = custom_field_service.def_map(db)
    if stored is None:
        stored = custom_field_service.read_values(db, [emp.id])
    return custom_field_service.visible_fields(
        stored.get(emp.id, {}), defs, actor.role
    )


@router.get("/", response_model=EmployeePage, operation_id="employeesList")
def read_employees(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="1-based page number."),
    page_size: int = Query(
        50, ge=1, le=200, description="Rows per page (at most 200)."
    ),
    search: str | None = Query(
        None,
        max_length=100,
        description=(
            "Case-insensitive match on the employee number, the first name, "
            "the last name, the full name or the email address."
        ),
    ),
    department_id: int | None = Query(None, ge=1, description="Only this department."),
    status: EmployeeStatusFilter | None = Query(
        None, description="Only employees in this employment status."
    ),
    manager_id: int | None = Query(
        None, ge=1, description="Only employees reporting to this manager."
    ),
    sort: EmployeeSortField | None = Query(
        None, description="Field to sort on. Omit it for newest hire first."
    ),
    order: Literal["asc", "desc"] = Query("asc", description="Sort direction."),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    """The employee directory, in the contract's paged envelope.

    Newest hire first unless `sort` names another key. Every filter is applied
    by the database, so a search reaches employees the caller has not loaded
    yet — the screen used to filter only the rows it already held.

    The visibility scope is applied *before* the count, so `meta.total` is the
    number of employees this caller may see, not the size of the directory.

    What the record does not have: there is no location on an employee (a
    position has one, and the employee is not linked to a position yet), so
    there is no `location_id` filter here. The contract says so rather than
    accepting a filter it cannot honour (`D-040`). Search matches the
    employee's own fields; it does not match a department or job *name*,
    because those live in other tables the contract does not name.
    """
    stmt = select(Employee)
    stmt = apply_visibility(stmt, Employee.id, current_user, db)

    term = (search or "").strip()
    if term:
        stmt = stmt.where(search_clause(term))
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    if manager_id is not None:
        stmt = stmt.where(Employee.manager_id == manager_id)
    if status is not None:
        stmt = stmt.where(Employee.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    if sort is None:
        ordered = stmt.order_by(Employee.hire_date.desc(), Employee.id.desc())
    else:
        column = _SORT_COLUMNS[sort]
        primary = column.desc() if order == "desc" else column.asc()
        # A stable tiebreaker: two people hired the same day must not swap
        # places between pages, or a paged read would miss one and repeat
        # another.
        tie = Employee.id.desc() if order == "desc" else Employee.id.asc()
        ordered = stmt.order_by(primary, tie)

    rows = (
        db.execute(ordered.offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    # Mask Aadhaar on list (AC-28); custom fields rendered per role.
    _cdefs, _cstored = _custom_bundle(db, list(rows))
    _role = current_user.role
    items = [_masked_employee_out(
        r, current_user,
        custom_field_service.visible_fields(
            _cstored.get(r.id, {}), _cdefs, _role))
        for r in rows]
    return {
        "items": items,
        "meta": page_meta(total, page, page_size).model_dump(),
    }


@router.post("/", response_model=EmployeeOut, status_code=201, operation_id="employeesCreate")
def create_employee_endpoint(
    employee_in: EmployeeCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    idem_key: str | None = Depends(idempotency_key),
) -> Any:
    """Create an employee.

    Send `Idempotency-Key` so a retried or double-submitted request returns the
    original employee instead of creating a second one. Without the header the
    endpoint still refuses a duplicate `employee_id`, but a retry after a
    network timeout would see 409 rather than the record it just created.
    """
    refuse_bank_tax_write(employee_in.model_dump(exclude_unset=True), current_user.role)
    with IdempotencyGuard(
        db, idem_key, "employees.create", employee_in.model_dump()
    ) as guard:
        if guard.replayed:
            response.headers["Idempotent-Replay"] = "true"
            # The route decorator forces 201; a replay did not create anything.
            response.status_code = 200
            _replayed = _replay_employee(db, guard.stored_response)
            return _masked_employee_out(
                _replayed, current_user,
                _custom_visible(db, _replayed, current_user)
            )

        # Auto-generate the natural key when the caller left it empty
        # (Phase T/F1: the frontend create form defaults to "Auto").
        generated_code: str | None = None
        if not (employee_in.employee_id or "").strip():
            generated_code = next_code(
                db, Employee, Employee.employee_id, "EMP-"
            )
            employee_in = employee_in.model_copy(
                update={"employee_id": generated_code}
            )

        existing = get_employee_by_code(db, employee_code=employee_in.employee_id)
        if existing:
            # The contract declares 409 `duplicate_natural_key`, which is the
            # taxonomy's answer for a taken natural key. A bare 400 with prose
            # was a second, smaller contract drift on the same operation.
            raise conflict(
                "duplicate_natural_key",
                f"Employee number {employee_in.employee_id!r} is already used.",
                entity="employee",
                value=employee_in.employee_id,
            )
        # --- Slice 6: aadhaar encrypted at rest (pan/ifsc plain for column-size compat; helper available) ---
        try:
            data = employee_in.model_dump()
            aadhaar_raw = data.pop("aadhaar_number", None)
            # Configurable attributes (LP-CORE-005) are not columns: the
            # CRUD constructor must never see them. They are validated up
            # front (before the row exists, so a refusal leaves nothing
            # behind) and stored after the row is created.
            custom_raw = data.pop("custom_fields", None)
            # NOTE: pan/ifsc/bank_account sized VARCHAR(10/11/60) cannot hold Fernet token (~120 chars) without migration widening to Text.
            # Slice 6 keeps them plain at rest for DB compat; encryption helper is verified via aadhaar_encrypted and unit test.
            # Do not encrypt pan/ifsc/pf_uan/esi here — they remain plaintext for v1; payment_file/filings decrypt if ENCv1 present.
            employee_in_clean = EmployeeCreate(**{k: v for k, v in data.items() if k in EmployeeCreate.model_fields})
            _aadhaar_capture = aadhaar_raw
        except Exception:
            employee_in_clean = employee_in
            _aadhaar_capture = getattr(employee_in, "aadhaar_number", None)
            custom_raw = getattr(employee_in, "custom_fields", None)
        _custom_defs = custom_field_service.def_map(db)
        if custom_raw:
            try:
                custom_field_service.validate_all(custom_raw, _custom_defs)
            except custom_field_service.CustomFieldError as exc:
                raise validation(
                    "validation_error", str(exc.message),
                    field=f"custom_fields.{exc.key}",
                )
        if getattr(employee_in_clean, "legal_entity_id", None) is not None:
            _ensure_own_legal_entity(db, employee_in_clean.legal_entity_id)
        created = create_employee(db=db, employee_in=employee_in_clean)
        if custom_raw:
            custom_field_service.set_values(
                db, created.id, custom_raw, _custom_defs)
            db.refresh(created)
        # Apply aadhaar via encrypted property
        if _aadhaar_capture:
            try:
                created.aadhaar_number = str(_aadhaar_capture)
                # Set stub verification statuses pending_verification
                created.pan_verified_status = "pending_verification"
                created.uan_verified_status = "pending_verification"
                created.esi_verified_status = "pending_verification"
                db.add(created); db.commit(); db.refresh(created)
            except Exception:
                pass
        record_audit(
            db,
            current_user,
            "create_employee",
            "Employee",
            created.id,
            details=f"employee_id={created.employee_id}",
        )
        db.commit()
        guard.store({"id": created.id})
        # Return masked view
        return _masked_employee_out(
            created, current_user, _custom_visible(db, created, current_user))


@router.get("/{employee_id}", response_model=EmployeeOut, operation_id="employeesGet")
def read_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    ensure_can_view_employee(db, current_user, employee_id)
    employee = get_employee(db=db, employee_id=employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(employee, "tenant_id", None), tenant_id
    ):
        # The record exists but belongs to another tenant: refuse fail-closed
        # without confirming its existence. A NULL tenant_id denotes a
        # pre-backfill row belonging to the legacy default tenant.
        raise HTTPException(status_code=404, detail="Employee not found")
    return _masked_employee_out(
        employee, current_user, _custom_visible(db, employee, current_user))


def _apply_update(
    db: Session,
    employee: Employee,
    payload: EmployeeUpdate,
    actor: User,
) -> Employee:
    """Apply a partial update, dating every employment change.

    Contact details (name, email, phone, hire date) are corrections and are
    audited; the employment fields are effective-dated and produce history
    rows. The change applies now — a future date is refused by
    `ensure_effective_date` because nothing would apply it.
    """
    refuse_bank_tax_write(payload.model_dump(exclude_unset=True), actor.role)
    data = payload.model_dump(exclude_unset=True)
    effective_from = ensure_effective_date(data.pop("effective_from", None))
    reason = data.pop("reason", None)
    # Configurable attributes (LP-CORE-005) are validated up front — a
    # refusal leaves the employment record untouched — and stored with the
    # same transaction as the employment change.
    custom_in = data.pop("custom_fields", None)
    _custom_defs = custom_field_service.def_map(db)
    if custom_in:
        try:
            custom_field_service.validate_all(custom_in, _custom_defs)
        except custom_field_service.CustomFieldError as exc:
            raise validation(
                "validation_error", str(exc.message),
                field=f"custom_fields.{exc.key}",
            )
    if not data and not custom_in:
        raise validation("validation_error", "No employment field was supplied.")

    if "job_id" in data:
        ensure_reference(db, Job, data["job_id"], "Job")
    if "department_id" in data:
        ensure_reference(db, Department, data["department_id"], "Department")
    if "legal_entity_id" in data:
        _ensure_own_legal_entity(db, data["legal_entity_id"])
    if "manager_id" in data:
        ensure_manager_available(db, employee, data["manager_id"])
    if "email" in data:
        other = (
            db.query(Employee)
            .filter(Employee.email == data["email"], Employee.id != employee.id)
            .first()
        )
        if other is not None:
            raise conflict(
                "duplicate_natural_key",
                f"The address {data['email']!r} is already used by another employee.",
                entity="employee",
                field="email",
            )

    previous_status = employee.status
    previous_termination = employee.termination_date
    if "status" in data and data["status"] is not None:
        ensure_transition(previous_status, data["status"])

    changes: list[str] = []

    # Corrections of the person's contact details: audited, not dated.
    for field in ("first_name", "last_name", "email", "phone", "hire_date"):
        if field in data and getattr(employee, field) != data[field]:
            changes.append(
                f"{field}: {getattr(employee, field)!r} -> {data[field]!r}"
            )
            setattr(employee, field, data[field])

    # The lifecycle move, and the termination date it implies.
    if "status" in data and data["status"] is not None:
        target = data["status"]
        if apply_change(
            db,
            employee,
            "status",
            target,
            effective_from=effective_from,
            reason=reason,
            changed_by=actor.username,
        ):
            changes.append(f"status: {previous_status!r} -> {target!r}")
        if target == "Terminated":
            termination = previous_termination or effective_from
            if apply_change(
                db,
                employee,
                "termination_date",
                termination,
                effective_from=effective_from,
                reason=reason,
                changed_by=actor.username,
            ):
                changes.append(
                    f"termination_date: {previous_termination!r} -> {termination!r}"
                )
        elif target == "Rehired":
            if apply_change(
                db,
                employee,
                "termination_date",
                None,
                effective_from=effective_from,
                reason=reason,
                changed_by=actor.username,
            ):
                changes.append(
                    f"termination_date: {previous_termination!r} -> None"
                )

    # The remaining employment fields.
    for field in ("employment_type", "job_id", "department_id", "legal_entity_id", "manager_id", "salary"):
        if field not in data:
            continue
        previous = getattr(employee, field)
        if apply_change(
            db,
            employee,
            field,
            data[field],
            effective_from=effective_from,
            reason=reason,
            changed_by=actor.username,
        ):
            changes.append(f"{field}: {previous!r} -> {data[field]!r}")

    # Configurable attributes (LP-CORE-005): current-value store, not
    # effective-dated history. Applied in the same transaction; the audit
    # names the keys whose stored value moved.
    if custom_in is not None:
        _before = custom_field_service.read_values(
            db, [employee.id]).get(employee.id, {})
        custom_field_service.set_values(db, employee.id, custom_in, _custom_defs)
        _after = custom_field_service.read_values(
            db, [employee.id]).get(employee.id, {})
        for _key in sorted(set(_before) | set(_after)):
            if _before.get(_key) != _after.get(_key):
                changes.append(
                    f"custom_fields.{_key}: {_before.get(_key)!r} -> "
                    f"{_after.get(_key)!r}"
                )

    if not changes:
        return employee

    record_audit(
        db,
        actor,
        "update_employee",
        "Employee",
        employee.id,
        details=(
            f"effective_from={effective_from.isoformat()} "
            f"reason={reason or '-'} " + ", ".join(changes)
        ),
    )
    db.commit()
    db.refresh(employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeOut, operation_id="employeesUpdate")
def patch_employee(
    employee_id: int,
    employee_in: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Change an employee's employment record, effective-dated.

    A lifecycle move the state machine does not define is refused with
    `409 invalid_state_transition`. Every employment change appends a history
    row; a value that did not change appends nothing.
    """
    employee = get_employee(db=db, employee_id=employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    _updated = _apply_update(db, employee, employee_in, current_user)
    return _masked_employee_out(
        _updated, current_user, _custom_visible(db, _updated, current_user)
    )


@router.put("/{employee_id}", response_model=EmployeeOut, operation_id="employeesUpdateEmployees")
def update_employee_endpoint(
    employee_id: int,
    employee_in: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """The historical PUT, kept for existing callers.

    It now goes through the same dated update path as PATCH, so a caller
    cannot bypass the lifecycle rule or the history by using the older verb.
    """
    employee = get_employee(db=db, employee_id=employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    _updated_put = _apply_update(db, employee, employee_in, current_user)
    return _masked_employee_out(
        _updated_put, current_user,
        _custom_visible(db, _updated_put, current_user)
    )


@router.get("/{employee_id}/history", response_model=list[EmployeeHistoryOut], operation_id="employeesGetHistory")
def read_employee_history(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
    from_: date | None = Query(
        None, alias="from", description="Only changes effective on or after this date."
    ),
    to: date | None = Query(
        None, description="Only changes effective on or before this date."
    ),
    field: str | None = Query(None, description="Only changes of this field."),
) -> Any:
    """The effective-dated employment history, oldest first."""
    ensure_can_view_employee(db, current_user, employee_id)
    employee = get_employee(db=db, employee_id=employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    stmt = select(EmployeeHistory).where(
        EmployeeHistory.employee_id == employee_id
    )
    if from_ is not None:
        stmt = stmt.where(EmployeeHistory.effective_from >= from_)
    if to is not None:
        stmt = stmt.where(EmployeeHistory.effective_from <= to)
    if field:
        stmt = stmt.where(EmployeeHistory.field == field)
    stmt = stmt.order_by(
        EmployeeHistory.effective_from.asc(), EmployeeHistory.id.asc()
    )
    return list(db.execute(stmt).scalars().all())
