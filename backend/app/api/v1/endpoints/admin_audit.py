"""Audit-chain verification (PS-12).

The contract declares ``GET /admin/audit/verify`` in
``contracts/openapi/admin.yaml``. ``PS-04`` made the trail tamper-evident:
every entry carries the hash of the one before it, so an edited row breaks
the link at that row and a removed row breaks it at the next one. Until this
module existed the only way to run the check was
``python -m scripts.verify_audit_chain`` — a shell workaround, not a feature.

What this endpoint does
-----------------------
It walks the chain in id order, recomputes every entry's hash and compares
the last entry with the recorded head, then reports the verdict in the
contract's ``AuditVerification`` shape:

* ``verified`` — whether the whole chain holds;
* ``checked_entries`` — how many entries verified before the walk stopped;
* ``head`` / ``head_id`` — the head the walk compared against. Record the
  pair ``(checked_entries, head)`` outside the database; without an external
  anchor a full rewrite of every row and the head is internally consistent.
  The verification's own audit entry becomes the next head, as any audited
  action does, so the pair — not the head alone — is the anchor.
* ``first_broken`` — where the chain stopped holding, with a stable reason:
  ``hash_mismatch`` (a row was edited), ``missing_predecessor`` (a row was
  inserted, removed or reordered in the middle) or ``head_mismatch``
  (entries were removed from the tail, or the head was rewritten).

It is read only. It never repairs the chain: a product that silently
rewrites evidence is worse than one that reports the break.

The verification is itself audited. The row is staged after the walk, so the
answer describes the chain as it was read; the new entry becomes the new
head. On a tail removal the next walk reports the gap as
``missing_predecessor`` at that entry rather than ``head_mismatch`` — the
break is still found and named, which is what matters.

Cost
----
The walk reads every entry and is not paged. Verifying *part* of a chain
would let a caller believe the whole holds, so a bound would be a false
claim. On a pilot-sized log (tens of thousands of rows) the walk is a few
hundred milliseconds; on a multi-million-row log it is a deliberate,
operator-triggered cost, which is why the screen does not run it on page
load.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.audit_chain import ChainVerification, verify_chain
from app.models.user import User
from app.schemas.audit import AuditVerification

router = APIRouter()


def _first_broken(result: ChainVerification) -> dict[str, Any] | None:
    """The contract's ``first_broken`` object, or None on an intact chain.

    A ``head_mismatch`` has no broken row to name: the entry it reports is
    the last one that *did* verify, and the gap is after it. Naming that row
    would accuse an honest entry, so the id is null and the index is the
    first position that is missing.
    """
    if result.ok:
        return None
    return {
        "id": (
            None
            if result.failure_code == "head_mismatch" or result.failure_id is None
            else str(result.failure_id)
        ),
        "index": result.entries,
        "reason": result.failure_code or "hash_mismatch",
    }


@router.get("/verify", response_model=AuditVerification, operation_id="adminVerifyAudit")
def verify_audit(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Walk the audit chain and report whether it still holds."""
    result = verify_chain(db)
    verified_at = datetime.now(timezone.utc)

    record_audit(
        db,
        current_user,
        "verify_audit",
        "AuditLog",
        result.failure_id if not result.ok else result.head_id,
        details=(
            f"verified={str(result.ok).lower()} entries={result.entries} "
            f"head={result.head}"
            + (
                f" broken_at={result.failure_id} reason={result.failure_code}"
                if not result.ok
                else ""
            )
        ),
    )
    db.commit()

    return {
        "verified": result.ok,
        "checked_entries": result.entries,
        "head": result.head,
        "head_id": result.head_id,
        "first_broken": _first_broken(result),
        "verified_at": verified_at,
    }
