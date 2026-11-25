"""Asset custody business rules (LP asset tracking).

Every function here **stages** its changes on the session — including the
chained audit entry via :func:`app.core.audit.record_audit` — and never
commits. The calling endpoint commits exactly once, so the mutation and its
audit entry are atomic: a rollback removes both.

The state machine
-----------------
``in_stock -> assigned`` (assign), ``assigned -> in_stock|maintenance|lost``
(return, by condition), ``in_stock <-> maintenance`` (explicit maintenance
start/complete), ``in_stock|maintenance -> retired`` (retire). ``retired``
and ``lost`` are final. Every move outside this graph is a ``409
invalid_state_transition``; starting maintenance on an assigned asset is
likewise refused — custody must end (return or transfer) first.

Custody rules
-------------
* an asset may carry at most one **open** assignment;
* assignment requires an ``in_stock`` asset and a same-tenant ``Active``
  employee;
* a transfer closes the open spell and opens a new, unacknowledged one in
  the same transaction — the new holder must acknowledge afresh;
* only the assigned employee themselves may acknowledge (never an admin on
  their behalf);
* clearance is a read-only projection for offboarding: it reports the open
  spells an employee still holds and writes nothing.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.errors import conflict, forbidden, not_found, validation
from app.core.master_data import ensure_reference, load_or_404
from app.core.tenancy import tenant_column_criterion, tenant_id_for, tenant_matches
from app.models.assets import Asset, AssetAssignment
from app.models.employee import Employee
from app.models.user import User

#: The asset FSM, as data. Keys are the states a move may start from.
ASSET_STATUSES = ("in_stock", "assigned", "maintenance", "retired", "lost")

#: A return's condition decides the asset's next status.
CONDITION_TO_STATUS = {"good": "in_stock", "damaged": "maintenance", "lost": "lost"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_asset(db: Session, asset_id: int) -> Asset:
    """Load one asset, refusing another tenant's row fail-closed (404)."""
    obj = load_or_404(db, Asset, asset_id, "Asset")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(getattr(obj, "tenant_id", None), tenant_id):
        raise not_found("Asset")
    return obj


def load_assignment(db: Session, assignment_id: int) -> AssetAssignment:
    """Load one assignment, refusing another tenant's row fail-closed (404)."""
    obj = load_or_404(db, AssetAssignment, assignment_id, "AssetAssignment")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(getattr(obj, "tenant_id", None), tenant_id):
        raise not_found("AssetAssignment")
    return obj


def ensure_tag_unique(db: Session, tag: str, exclude_id: int | None = None) -> str:
    """Refuse a tag another asset of *this tenant* already carries.

    Uniqueness is per tenant, case-insensitive (two tags differing only in
    case read as the same tag to a person). The database additionally holds
    ``(tenant_id, tag)`` unique; this check gives the shared 409 envelope
    before the constraint would fire, and covers the legacy NULL-tenant
    rows the default tenant sees.
    """
    cleaned = (tag or "").strip()
    if not cleaned:
        raise validation("validation_error", "Asset tag is required.", entity="Asset", fields=["tag"])
    query = db.query(func.count()).select_from(Asset).filter(
        func.lower(Asset.tag) == cleaned.lower()
    )
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        query = query.filter(tenant_column_criterion(Asset.tenant_id, tenant_id))
    if exclude_id is not None:
        query = query.filter(Asset.id != exclude_id)
    if query.scalar():
        raise conflict(
            "duplicate_natural_key",
            f"Asset already uses the tag {cleaned!r} in this tenant. Tags are unique per tenant.",
            entity="asset",
            value=cleaned,
        )
    return cleaned


def ensure_assignable_employee(db: Session, employee_id: int) -> Employee:
    """The holder must exist in this tenant and be Active.

    A missing or foreign-tenant employee is a payload validation failure
    (the id does not resolve for this caller); an inactive employee is a
    state conflict — custody cannot be given to someone who has left.
    """
    person = ensure_reference(db, Employee, employee_id, "Employee")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(getattr(person, "tenant_id", None), tenant_id):
        raise validation(
            "reference_not_found",
            f"Employee {employee_id} does not exist.",
            entity="Employee",
            id=employee_id,
        )
    if person.status != "Active":
        raise conflict(
            "employee_not_active",
            f"Employee {employee_id} is {person.status}; assets may only be assigned to active employees.",
            id=employee_id,
            status=person.status,
        )
    return person


def open_assignment(db: Session, asset_id: int) -> AssetAssignment | None:
    """The asset's single open custody spell, if any."""
    return (
        db.query(AssetAssignment)
        .filter(AssetAssignment.asset_id == asset_id, AssetAssignment.status == "open")
        .first()
    )


def require_status(asset: Asset, allowed: tuple[str, ...], target: str) -> None:
    """Refuse a move that is not on the asset state machine (409)."""
    if asset.status not in allowed:
        raise conflict(
            "invalid_state_transition",
            f"Cannot move asset from '{asset.status}' to '{target}'. "
            f"Allowed from: {list(allowed)}.",
            id=asset.id,
            from_state=asset.status,
            to_state=target,
        )


def _new_assignment(db: Session, u: User, asset: Asset, employee_id: int, notes: str | None) -> AssetAssignment:
    assignment = AssetAssignment(
        asset_id=asset.id,
        employee_id=employee_id,
        status="open",
        notes=notes,
        assigned_by=u.id,
        assigned_at=_utcnow(),
        tenant_id=asset.tenant_id,
    )
    db.add(assignment)
    return assignment


def _close_assignment(db: Session, u: User, assignment: AssetAssignment, reason: str, condition: str | None = None) -> None:
    assignment.status = "closed"
    assignment.close_reason = reason
    assignment.return_condition = condition
    assignment.closed_by = u.id
    assignment.closed_at = _utcnow()
    db.add(assignment)


def create_asset(db: Session, u: User, data: dict) -> Asset:
    tag = ensure_tag_unique(db, data["tag"])
    obj = Asset(**{**data, "tag": tag}, status="in_stock", created_by=u.id)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not getattr(obj, "tenant_id", None):
        obj.tenant_id = tenant_id
    db.add(obj)
    db.flush()  # the id, without committing: audit shares this transaction
    record_audit(db, u, "create_asset", "Asset", obj.id, details=f"tag={obj.tag}")
    return obj


def update_asset(db: Session, u: User, asset: Asset, changes: dict) -> Asset:
    if "tag" in changes:
        changes["tag"] = ensure_tag_unique(db, changes["tag"], exclude_id=asset.id)
    for field, value in changes.items():
        setattr(asset, field, value)
    db.add(asset)
    record_audit(db, u, "update_asset", "Asset", asset.id, details=",".join(sorted(changes)) or "no change")
    return asset


def assign_asset(db: Session, u: User, asset: Asset, employee_id: int, notes: str | None) -> AssetAssignment:
    require_status(asset, ("in_stock",), "assigned")
    if open_assignment(db, asset.id) is not None:
        raise conflict(
            "asset_already_assigned",
            f"Asset {asset.id} already has an open assignment; an asset may be held by only one employee at a time.",
            id=asset.id,
        )
    ensure_assignable_employee(db, employee_id)
    assignment = _new_assignment(db, u, asset, employee_id, notes)
    asset.status = "assigned"
    db.add(asset)
    db.flush()
    record_audit(db, u, "assign_asset", "Asset", asset.id, details=f"employee={employee_id},assignment={assignment.id}")
    return assignment


def transfer_asset(db: Session, u: User, asset: Asset, employee_id: int, notes: str | None) -> AssetAssignment:
    """Close the open spell and open a new one — atomically, re-ack required."""
    require_status(asset, ("assigned",), "assigned (transfer)")
    current = open_assignment(db, asset.id)
    if current is None:
        raise conflict(
            "asset_not_assigned",
            f"Asset {asset.id} has no open assignment to transfer.",
            id=asset.id,
        )
    if current.employee_id == employee_id:
        raise conflict(
            "asset_transfer_same_employee",
            f"Asset {asset.id} is already held by employee {employee_id}.",
            id=asset.id,
            employee_id=employee_id,
        )
    ensure_assignable_employee(db, employee_id)
    _close_assignment(db, u, current, "transferred")
    assignment = _new_assignment(db, u, asset, employee_id, notes)
    db.flush()
    record_audit(
        db, u, "transfer_asset", "Asset", asset.id,
        details=f"from={current.employee_id},to={employee_id},closed={current.id},opened={assignment.id}",
    )
    return assignment


def return_asset(db: Session, u: User, asset: Asset, condition: str, notes: str | None) -> AssetAssignment:
    require_status(asset, ("assigned",), CONDITION_TO_STATUS[condition])
    current = open_assignment(db, asset.id)
    if current is None:
        raise conflict(
            "asset_not_assigned",
            f"Asset {asset.id} has no open assignment to return.",
            id=asset.id,
        )
    _close_assignment(db, u, current, "returned", condition)
    if notes:
        current.notes = (current.notes + "\n" if current.notes else "") + f"return: {notes}"
    asset.status = CONDITION_TO_STATUS[condition]
    db.add(asset)
    record_audit(
        db, u, "return_asset", "Asset", asset.id,
        details=f"employee={current.employee_id},condition={condition},status={asset.status}",
    )
    return current


def start_maintenance(db: Session, u: User, asset: Asset, notes: str | None) -> Asset:
    """Blocked while assigned: custody must end before the workshop takes it."""
    require_status(asset, ("in_stock",), "maintenance")
    asset.status = "maintenance"
    db.add(asset)
    record_audit(db, u, "start_asset_maintenance", "Asset", asset.id, details=(notes or "")[:200] or None)
    return asset


def complete_maintenance(db: Session, u: User, asset: Asset, notes: str | None) -> Asset:
    require_status(asset, ("maintenance",), "in_stock")
    asset.status = "in_stock"
    db.add(asset)
    record_audit(db, u, "complete_asset_maintenance", "Asset", asset.id, details=(notes or "")[:200] or None)
    return asset


def retire_asset(db: Session, u: User, asset: Asset, reason: str | None) -> Asset:
    require_status(asset, ("in_stock", "maintenance"), "retired")
    asset.status = "retired"
    db.add(asset)
    record_audit(db, u, "retire_asset", "Asset", asset.id, details=(reason or "")[:200] or None)
    return asset


def acknowledge_assignment(db: Session, u: User, assignment: AssetAssignment) -> AssetAssignment:
    """Self-only: the assigned employee acknowledges receipt, nobody else."""
    if u.employee_id is None or u.employee_id != assignment.employee_id:
        raise forbidden("Only the assigned employee may acknowledge receipt of an asset.")
    if assignment.status != "open":
        raise conflict(
            "assignment_closed",
            f"Assignment {assignment.id} is closed and can no longer be acknowledged.",
            id=assignment.id,
        )
    if assignment.acknowledged_at is not None:
        raise conflict(
            "assignment_already_acknowledged",
            f"Assignment {assignment.id} was already acknowledged.",
            id=assignment.id,
        )
    assignment.acknowledged_at = _utcnow()
    db.add(assignment)
    record_audit(db, u, "acknowledge_asset", "AssetAssignment", assignment.id, details=f"asset={assignment.asset_id}")
    return assignment


def clearance(db: Session, employee_id: int) -> dict:
    """Read-only asset clearance toward offboarding.

    Reports the open custody spells the employee still holds. It writes
    nothing — neither here nor on any offboarding row — so the offboarding
    module can consume it freely.
    """
    person = ensure_reference(db, Employee, employee_id, "Employee")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(getattr(person, "tenant_id", None), tenant_id):
        raise validation(
            "reference_not_found",
            f"Employee {employee_id} does not exist.",
            entity="Employee",
            id=employee_id,
        )
    rows = (
        db.query(AssetAssignment, Asset)
        .join(Asset, Asset.id == AssetAssignment.asset_id)
        .filter(AssetAssignment.employee_id == employee_id, AssetAssignment.status == "open")
        .order_by(AssetAssignment.id)
        .all()
    )
    outstanding = [
        {
            "assignment_id": a.id,
            "asset_id": asset.id,
            "tag": asset.tag,
            "name": asset.name,
            "assigned_at": a.assigned_at,
            "acknowledged_at": a.acknowledged_at,
        }
        for a, asset in rows
    ]
    return {
        "employee_id": employee_id,
        "clear": not outstanding,
        "outstanding_count": len(outstanding),
        "outstanding": outstanding,
    }