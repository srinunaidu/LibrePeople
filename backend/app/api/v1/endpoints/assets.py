"""Asset register and custody lifecycle.

Assets move only through explicit endpoints: no schema exposes ``status``,
so an asset can only travel the FSM in :mod:`app.services.assets_service`
and every illegal move is a ``409``. HR/Admin manage the register and all
custody moves; Associates see only their own custody (and acknowledge it
themselves — nobody may acknowledge on their behalf); Managers see their
reporting line. Every write stages its chained audit entry on the session
and commits once, so the mutation and its audit row are atomic. Every read
is tenant-scoped: another tenant's rows read as 404, and a client-supplied
tenant that conflicts with the resolved one is refused 409 by the shared
tenancy dependency before any handler runs.

The clearance endpoint is a read-only projection for offboarding: it never
writes, on this side or theirs.
"""
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    ADMIN_ROLES,
    MANAGER_ROLES,
    WORKFORCE_ROLES,
    get_db,
    require_roles,
    tenant_id_for,
)
from app.core.errors import not_found, validation
from app.core.master_data import refuse_null_updates
from app.core.tenancy import tenant_column_criterion
from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.models.assets import Asset, AssetAssignment
from app.models.user import User
from app.schemas.assets import (
    AssetAssign,
    AssetAssignmentOut,
    AssetClearanceOut,
    AssetCreate,
    AssetMaintenance,
    AssetOut,
    AssetRetire,
    AssetReturn,
    AssetTransfer,
    AssetUpdate,
)
from app.services import assets_service as svc

router = APIRouter()


def _visible_assets_query(db: Session, u: User):
    """Tenant-scoped asset query, narrowed for non-admin readers.

    An asset has no employee column of its own; a non-admin sees the assets
    that have been in the custody of an employee they may view (an
    Associate: themselves; a Manager: their reporting line). Admins see the
    whole tenant register.
    """
    query = db.query(Asset)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        query = query.filter(tenant_column_criterion(Asset.tenant_id, tenant_id))
    if u.role not in ADMIN_ROLES:
        visible = apply_visibility(
            db.query(AssetAssignment.asset_id), AssetAssignment.employee_id, u, db
        )
        query = query.filter(Asset.id.in_(visible))
    return query


def _ensure_asset_readable(db: Session, u: User, asset: Asset) -> None:
    if u.role in ADMIN_ROLES:
        return
    visible = apply_visibility(
        db.query(AssetAssignment.id), AssetAssignment.employee_id, u, db
    ).filter(AssetAssignment.asset_id == asset.id)
    if visible.first() is None:
        # 404 rather than 403: do not confirm the asset exists.
        raise not_found("Asset")


# --- Collections and static paths (declared before /{asset_id}) ------------- #


@router.get("", response_model=list[AssetOut], operation_id="assetsListAssets")
def list_assets(
    status: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """The asset register, scoped to the caller's tenant and visibility."""
    query = _visible_assets_query(db, u)
    if status:
        query = query.filter(Asset.status == status)
    if category:
        query = query.filter(Asset.category == category)
    return query.order_by(Asset.tag).all()


@router.post("", response_model=AssetOut, status_code=201, operation_id="assetsCreateAsset")
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    obj = svc.create_asset(db, u, payload.model_dump())
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/assignments", response_model=list[AssetAssignmentOut], operation_id="assetsListAssignments")
def list_assignments(
    asset_id: int | None = None,
    employee_id: int | None = None,
    status: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Custody spells, scoped to the caller's visibility and tenant.

    ``mine=true`` selects the caller's own spells (the My Assets view);
    an Associate's list is own-only regardless.
    """
    query = apply_visibility(db.query(AssetAssignment), AssetAssignment.employee_id, u, db)
    if mine:
        if u.employee_id is None:
            raise validation(
                "employee_profile_required",
                "This account has no employee record, so it holds no assets.",
                entity="User",
                id=u.id,
            )
        query = query.filter(AssetAssignment.employee_id == u.employee_id)
    if asset_id is not None:
        query = query.filter(AssetAssignment.asset_id == asset_id)
    if employee_id is not None:
        query = query.filter(AssetAssignment.employee_id == employee_id)
    if status:
        query = query.filter(AssetAssignment.status == status)
    return query.order_by(AssetAssignment.id.desc()).all()


@router.post(
    "/assignments/{assignment_id}/ack",
    response_model=AssetAssignmentOut,
    operation_id="assetsAcknowledgeAssignment",
)
def acknowledge_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    """Acknowledge receipt — self-only, including against admins."""
    obj = svc.load_assignment(db, assignment_id)
    svc.acknowledge_assignment(db, u, obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get(
    "/clearance/{employee_id}",
    response_model=AssetClearanceOut,
    operation_id="assetsClearance",
)
def asset_clearance(
    employee_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Read-only asset clearance toward offboarding: the open custody
    spells this employee must settle. Writes nothing anywhere."""
    ensure_can_view_employee(db, u, employee_id)
    return svc.clearance(db, employee_id)


# --- One asset --------------------------------------------------------------- #


@router.get("/{asset_id}", response_model=AssetOut, operation_id="assetsGetAsset")
def read_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    obj = svc.load_asset(db, asset_id)
    _ensure_asset_readable(db, u, obj)
    return obj


@router.patch("/{asset_id}", response_model=AssetOut, operation_id="assetsUpdateAsset")
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Metadata only. ``status`` is not a field here: lifecycle moves are
    the explicit endpoints below."""
    obj = svc.load_asset(db, asset_id)
    changes = payload.model_dump(exclude_unset=True)
    refuse_null_updates(changes, ("tag", "name", "category"), "Asset")
    svc.update_asset(db, u, obj, changes)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{asset_id}/assign", response_model=AssetAssignmentOut, operation_id="assetsAssignAsset")
def assign_asset(
    asset_id: int,
    payload: AssetAssign,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Give custody of an in-stock asset to a same-tenant active employee.
    The new assignment starts unacknowledged."""
    obj = svc.load_asset(db, asset_id)
    assignment = svc.assign_asset(db, u, obj, payload.employee_id, payload.notes)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{asset_id}/transfer", response_model=AssetAssignmentOut, operation_id="assetsTransferAsset")
def transfer_asset(
    asset_id: int,
    payload: AssetTransfer,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Move custody: close the open spell and open a new unacknowledged
    one for the new holder, in one transaction."""
    obj = svc.load_asset(db, asset_id)
    assignment = svc.transfer_asset(db, u, obj, payload.employee_id, payload.notes)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{asset_id}/return", response_model=AssetAssignmentOut, operation_id="assetsReturnAsset")
def return_asset(
    asset_id: int,
    payload: AssetReturn,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Take the asset back. The recorded condition decides its next
    status: good -> in_stock, damaged -> maintenance, lost -> lost."""
    obj = svc.load_asset(db, asset_id)
    assignment = svc.return_asset(db, u, obj, payload.condition, payload.notes)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post(
    "/{asset_id}/maintenance/start",
    response_model=AssetOut,
    operation_id="assetsStartMaintenance",
)
def start_maintenance(
    asset_id: int,
    payload: AssetMaintenance,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Send an in-stock asset to maintenance. Blocked (409) while the
    asset is assigned: custody must end first."""
    obj = svc.load_asset(db, asset_id)
    svc.start_maintenance(db, u, obj, payload.notes)
    db.commit()
    db.refresh(obj)
    return obj


@router.post(
    "/{asset_id}/maintenance/complete",
    response_model=AssetOut,
    operation_id="assetsCompleteMaintenance",
)
def complete_maintenance(
    asset_id: int,
    payload: AssetMaintenance,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    obj = svc.load_asset(db, asset_id)
    svc.complete_maintenance(db, u, obj, payload.notes)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{asset_id}/retire", response_model=AssetOut, operation_id="assetsRetireAsset")
def retire_asset(
    asset_id: int,
    payload: AssetRetire,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Retire an in-stock or maintenance asset. Final."""
    obj = svc.load_asset(db, asset_id)
    svc.retire_asset(db, u, obj, payload.reason)
    db.commit()
    db.refresh(obj)
    return obj