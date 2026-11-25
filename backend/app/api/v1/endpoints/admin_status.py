"""Administrator operational status (LP-ADM-005).

The contract declares ``GET /admin/status`` in
``contracts/openapi/admin.yaml``. It reports the upgrade status, the backup
status and the actionable operational warnings of this deployment.

Role gate: SuperAdmin only. HR, Manager and Associate get the shared 403
envelope before the handler ever runs.

Read only by construction: the handler calls the collectors in
:mod:`app.services.ops_status` (which never write), stages no audit row
and never commits. A status probe must not move the system it observes —
in particular it never triggers an upgrade, a migration or a backup. That
is why this endpoint deliberately does not write the audit entry the other
``admin`` endpoints write: an audited read would change the audit chain it
may be used to inspect.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.schemas.admin_status import AdminStatus
from app.services import ops_status

router = APIRouter()

#: SuperAdmin only. HR administers people and jobs, but upgrade and backup
#: state is a platform-operator concern.
require_superadmin = require_roles("SuperAdmin")


@router.get("", response_model=AdminStatus, operation_id="adminGetStatus")
def admin_get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin),
) -> Any:
    """Report upgrade status, backup status and operational warnings."""
    return ops_status.collect_status(db)
