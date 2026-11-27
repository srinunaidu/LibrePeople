"""Consent-gated update check (update-system).

Additive endpoints, SuperAdmin only. Read-only except ``install``, which
records history and returns operator instructions — the actual code deploy
stays operator-driven (Render rollback / previous image) and this process
never overwrites itself.

* ``GET /current`` — installed version + migration state.
* ``GET /available`` — the LOCAL ``releases/manifest.json`` copy, verified
  before display. A remote fetch happens only with the double opt-in
  (flag + URL) from an owner-pinned host; both default off, so no egress.
* ``POST /check`` — fail-closed pre-install gates + audit row. ``409``
  with a named remediation per failed gate.
* ``POST /install`` — re-runs the gates non-dry-run, records
  ``update_history`` (in-memory + audit row), refuses on any gate fail.
* ``GET /history`` — the in-process install-attempt log (audit chain is
  the durable record).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.audit import record_audit
from app.core.config import settings
from app.models.user import User
from app.services import update_manifest as _updates

router = APIRouter()

#: SuperAdmin only: upgrade state is a platform-operator concern.
require_superadmin = require_roles("SuperAdmin")


class CheckRequest(BaseModel):
    dry_run: bool = True


class InstallRequest(BaseModel):
    manifest_sha256: str


def _current() -> dict[str, Any]:
    from app.core import migrations as _migrations

    current = _migrations.database_revision()
    if current is None:
        current = (_migrations.MIGRATION_STATE or {}).get("current_revision")
    head = _migrations.head_revision()
    if head is None:
        head = (_migrations.MIGRATION_STATE or {}).get("head_revision")
    return {
        "app_version": settings.VERSION,
        "project": settings.PROJECT_NAME,
        "current_revision": current,
        "head_revision": head,
        "up_to_date": bool(current) and current == head,
    }


@router.get("/current")
def updates_current(_: User = Depends(require_superadmin)) -> Any:
    """Report the installed version and migration state (read only)."""
    return _current()


@router.get("/available")
def updates_available(_: User = Depends(require_superadmin)) -> Any:
    """Report the local release manifest, verified before display."""
    manifest, error = _updates.load_local_manifest()
    if error is not None or manifest is None:
        raise HTTPException(status_code=404, detail=error or "manifest unavailable")
    verification = _updates.verify_manifest(manifest)
    if not verification["ok"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "local manifest failed verification and is not shown",
                "reasons": verification["reasons"],
                "remediation": "regenerate it with scripts/make_release_manifest.py",
            },
        )
    allowed, reason = _updates.remote_fetch_allowed()
    return {
        "manifest": manifest,
        "verified": True,
        "dev_signature": verification["dev_signature"],
        "dev_warning": (
            "dev-ephemeral signature: NOT A PRODUCTION RELEASE — "
            "production manifests carry an owner-held minisign signature"
            if verification["dev_signature"]
            else None
        ),
        "remote": {"allowed": allowed, "reason": reason or "remote fetch permitted"},
    }


@router.post("/check")
def updates_check(
    body: CheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin),
) -> Any:
    """Run the pre-install gates. Any fail → 409 + named remediation."""
    manifest, error = _updates.load_local_manifest()
    if error is not None or manifest is None:
        raise HTTPException(status_code=404, detail=error or "manifest unavailable")
    verification = _updates.verify_manifest(manifest)
    if not verification["ok"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "manifest verification failed",
                "reasons": verification["reasons"],
                "remediation": "regenerate it with scripts/make_release_manifest.py",
            },
        )
    gates = _updates.run_gates(manifest)
    record_audit(
        db,
        current_user,
        "update.check",
        "release_manifest",
        None,
        f"dry_run={body.dry_run} version={manifest.get('version')} "
        f"passed={all(g['passed'] for g in gates)}",
    )
    db.commit()
    failed = [g for g in gates if not g["passed"]]
    if failed:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "pre-install gates failed — install refused",
                "gates": gates,
                "dry_run": body.dry_run,
            },
        )
    return {
        "version": manifest.get("version"),
        "channel": manifest.get("channel"),
        "gates": gates,
        "dry_run": body.dry_run,
        "dev_signature": verification["dev_signature"],
    }


@router.post("/install")
def updates_install(
    body: InstallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin),
) -> Any:
    """Record an update install attempt (operator deploys; never self-overwrites)."""
    manifest, error = _updates.load_local_manifest()
    if error is not None or manifest is None:
        raise HTTPException(status_code=404, detail=error or "manifest unavailable")
    verification = _updates.verify_manifest(manifest)
    if not verification["ok"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "manifest verification failed — install refused",
                "reasons": verification["reasons"],
            },
        )
    if body.manifest_sha256 != manifest.get("manifest_sha256"):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "manifest_sha256 does not match the local manifest — "
                "install refused",
                "remediation": "re-run POST /check to see the current manifest hash",
            },
        )
    gates = _updates.run_gates(manifest)
    failed = [g for g in gates if not g["passed"]]
    entry = _updates.record_history(
        {
            "version": manifest.get("version"),
            "manifest_sha256": manifest.get("manifest_sha256"),
            "actor": current_user.username,
            "dry_run": False,
            "accepted": not failed,
            "gates": gates,
        }
    )
    record_audit(
        db,
        current_user,
        "update.install",
        "release_manifest",
        None,
        f"version={manifest.get('version')} accepted={entry['accepted']} "
        f"sha={manifest.get('manifest_sha256')}",
    )
    db.commit()
    if failed:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "pre-install gates failed — install refused, attempt logged",
                "gates": gates,
                "history_id": len(_updates.UPDATE_HISTORY) - 1,
            },
        )
    return {
        "accepted": True,
        "version": manifest.get("version"),
        "operator_action": (
            "deploy the release yourself (Render dashboard → Deploys → deploy "
            "the tagged image, or compose previous/next image); this process "
            "never overwrites its own code. Run `python -m scripts.migrate "
            "upgrade` only with the named pre-deploy backup snapshot."
        ),
        "history_id": len(_updates.UPDATE_HISTORY) - 1,
    }


@router.get("/history")
def updates_history(_: User = Depends(require_superadmin)) -> Any:
    """List install attempts recorded by this process (audit chain is durable)."""
    return {"entries": list(_updates.UPDATE_HISTORY)}
