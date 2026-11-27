"""Local release-manifest check + fail-closed pre-install gates (update-system).

Self-hosted, consent-gated, manual updates. This module never pulls code,
never migrates, never writes to the database, and never touches the
network unless the owner explicitly opted in (``UPDATE_CHECK_ALLOW_REMOTE``
*and* ``UPDATE_CHECK_REMOTE_URL`` *and* an owner-pinned host). The only
source consulted by default is the in-repo copy at
``UPDATE_MANIFEST_PATH`` (canonical: ``releases/manifest.json``).

Signing without embedded secrets: ``dev-ephemeral`` signatures are
keyless checksums for dev/test only (CI warns on them). Production uses
an owner-held offline minisign key; only pubkey IDs live in
``UPDATE_SIGNING_KEY_IDS``. Verification here is the checksum chain
(canonical JSON hash == ``manifest_sha256``) plus key-id allow-listing;
the full minisign verification is ``scripts/verify_release.py``.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Key id used by dev/test manifests. Never trusted silently: callers must
# surface the dev-ephemeral marking wherever the manifest is displayed.
DEV_EPHEMERAL_KEY_ID = "dev-ephemeral"

#: Free space (bytes) required by the disk-space gate. 1 GiB is enough for
#: a manifest + image pull staging on the single-instance deployment;
#: the gate names the actual free bytes in its remediation.
REQUIRED_FREE_BYTES = 1_073_741_824

#: Hosts the owner pinned for an opt-in remote manifest fetch. Empty means
#: "no remote host is trusted" (fail-closed default: no egress at all).
#: Populated from ``UPDATE_CHECK_REMOTE_HOSTS`` (comma-separated) at call
#: time so tests can override env without re-importing.
OWNER_PINNED_HOSTS_ENV = "UPDATE_CHECK_REMOTE_HOSTS"


def _repo_root() -> Path:
    # backend/app/services/update_manifest.py -> backend -> repo root.
    return Path(__file__).resolve().parent.parent.parent.parent


def manifest_path() -> Path:
    """Resolve ``UPDATE_MANIFEST_PATH`` against the repo root (additive)."""
    from app.core.config import settings

    raw = (settings.UPDATE_MANIFEST_PATH or "releases/manifest.json").strip()
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (_repo_root() / candidate).resolve()


def canonical_bytes(manifest: dict[str, Any]) -> bytes:
    """Canonical JSON of the manifest minus the ``signature`` block and the
    ``manifest_sha256`` field itself (the hash cannot cover itself)."""
    body = {k: v for k, v in manifest.items() if k not in ("signature", "manifest_sha256")}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_manifest_sha256(manifest: dict[str, Any]) -> str:
    """The checksum chain: sha256 of the canonical body."""
    return hashlib.sha256(canonical_bytes(manifest)).hexdigest()


def verify_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify schema shape + checksum chain + key-id allow-list.

    Returns ``{"ok": bool, "reasons": [str], "dev_signature": bool}``.
    Never raises on a malformed manifest: a bad manifest is data, not a
    crash — the gates below turn it into a named 409 remediation.
    """
    from app.core.config import settings

    reasons: list[str] = []
    required = [
        "version",
        "channel",
        "released_at",
        "git_sha",
        "app_version",
        "db_head_revision",
        "min_version",
        "breaking_changes",
        "notes_url",
        "changelog",
        "artifacts",
        "manifest_sha256",
        "signature",
    ]
    for field in required:
        if field not in manifest:
            reasons.append(f"missing field: {field}")
    sig = manifest.get("signature")
    if not isinstance(sig, dict):
        reasons.append("missing field: signature.{alg,key_id,sig}")
        sig = {}
    for field in ("alg", "key_id", "sig"):
        if field not in sig:
            reasons.append(f"missing field: signature.{field}")
    if manifest.get("channel") not in ("stable", "rc"):
        reasons.append("field channel must be stable|rc")
    if not isinstance(manifest.get("breaking_changes"), list):
        reasons.append("field breaking_changes must be a list")
    if not isinstance(manifest.get("artifacts"), list):
        reasons.append("field artifacts must be a list")

    dev_signature = sig.get("key_id") == DEV_EPHEMERAL_KEY_ID
    if reasons:
        return {"ok": False, "reasons": reasons, "dev_signature": dev_signature}

    # Checksum chain.
    expected = compute_manifest_sha256(manifest)
    if manifest.get("manifest_sha256") != expected:
        reasons.append("manifest_sha256 mismatch: manifest was edited after signing")

    # Key-id allow-list. dev-ephemeral is accepted but flagged; anything
    # else must be a pubkey ID the owner configured.
    key_id = str(sig.get("key_id") or "")
    allowed = {
        part.strip()
        for part in (settings.UPDATE_SIGNING_KEY_IDS or "").split(",")
        if part.strip()
    }
    if key_id != DEV_EPHEMERAL_KEY_ID and key_id not in allowed:
        reasons.append(
            f"signature key_id {key_id!r} is not dev-ephemeral and is not in "
            "UPDATE_SIGNING_KEY_IDS (owner-held pubkey IDs)"
        )
    return {"ok": not reasons, "reasons": reasons, "dev_signature": dev_signature}


def load_local_manifest() -> tuple[dict[str, Any] | None, str | None]:
    """Read the local manifest copy. Returns (manifest, error)."""
    path = manifest_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"local manifest not found at {path} (UPDATE_MANIFEST_PATH)"
    except OSError as exc:
        return None, f"local manifest unreadable: {exc}"
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"local manifest is not valid JSON: {exc}"
    if not isinstance(manifest, dict):
        return None, "local manifest is not a JSON object"
    return manifest, None


def remote_fetch_allowed() -> tuple[bool, str]:
    """Whether an opt-in remote manifest fetch is permitted right now."""
    from app.core.config import settings

    if not settings.UPDATE_CHECK_ALLOW_REMOTE:
        return False, "remote check disabled (UPDATE_CHECK_ALLOW_REMOTE=false) — no egress"
    url = (settings.UPDATE_CHECK_REMOTE_URL or "").strip()
    if not url:
        return False, "remote check has no URL (UPDATE_CHECK_REMOTE_URL unset) — no egress"
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False, f"remote check URL does not parse: {url}"
    import os

    pinned = {
        part.strip().lower()
        for part in os.environ.get(
            OWNER_PINNED_HOSTS_ENV, settings.UPDATE_CHECK_REMOTE_HOSTS
        ).split(",")
        if part.strip()
    }
    if not host or host not in pinned:
        return False, (
            f"remote host {host!r} is not owner-pinned "
            "(UPDATE_CHECK_REMOTE_HOSTS) — refusing egress"
        )
    return True, ""


def _parse_version(raw: str) -> tuple[int, ...]:
    parts = []
    for piece in str(raw).strip().split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            break
    return tuple(parts) or (0,)


def run_gates(
    manifest: dict[str, Any], *, now: datetime | None = None
) -> list[dict[str, Any]]:
    """Run the fail-closed pre-install gates. All must pass.

    Each gate returns ``{"gate": name, "passed": bool, "remediation": str}``.
    Read-only: no migration runs, nothing writes, no network.
    """
    from app.core import migrations as _migrations
    from app.core.config import settings
    from app.services import ops_status as _ops

    gates: list[dict[str, Any]] = []
    checked = now or datetime.now(timezone.utc)

    # G1 compat: installed version >= manifest min_version.
    installed = _parse_version(settings.VERSION)
    minimum = _parse_version(manifest.get("min_version") or "0")
    if installed >= minimum:
        gates.append({"gate": "compat", "passed": True, "remediation": ""})
    else:
        gates.append(
            {
                "gate": "compat",
                "passed": False,
                "remediation": (
                    f"installed {settings.VERSION} is older than the manifest's "
                    f"min_version {manifest.get('min_version')}: upgrade through "
                    "the intermediate release first"
                ),
            }
        )

    # G2 single-head assert: exactly one Alembic head (linear history).
    try:
        from alembic import script as _script

        heads = _script.ScriptDirectory.from_config(
            _migrations._alembic_config()
        ).get_heads()
    except Exception as exc:  # noqa: BLE001 — gate fails, loudly
        heads = []
        gates.append(
            {
                "gate": "single_head",
                "passed": False,
                "remediation": f"could not enumerate Alembic heads: {exc}",
            }
        )
    else:
        if len(heads) == 1:
            gates.append({"gate": "single_head", "passed": True, "remediation": ""})
        else:
            gates.append(
                {
                    "gate": "single_head",
                    "passed": False,
                    "remediation": (
                        f"expected exactly one Alembic head, found {len(heads)} "
                        f"({', '.join(heads) or 'none'}): merge the migration "
                        "branches before updating"
                    ),
                }
            )

    # G3 disk-space check.
    try:
        free = shutil.disk_usage(manifest_path().parent).free
    except OSError as exc:
        gates.append(
            {
                "gate": "disk_space",
                "passed": False,
                "remediation": f"could not measure free disk space: {exc}",
            }
        )
    else:
        if free >= REQUIRED_FREE_BYTES:
            gates.append({"gate": "disk_space", "passed": True, "remediation": ""})
        else:
            gates.append(
                {
                    "gate": "disk_space",
                    "passed": False,
                    "remediation": (
                        f"only {free} bytes free, "
                        f"{REQUIRED_FREE_BYTES} required: free disk space "
                        "before updating"
                    ),
                }
            )

    # G4 backup freshness: stale or unarranged backup is a HARD BLOCK (D4).
    backup = _ops.collect_backup(now=checked)
    if backup.get("configured") and backup.get("stale") is False:
        gates.append({"gate": "backup_fresh", "passed": True, "remediation": ""})
    elif not settings.BACKUP_ENABLED:
        gates.append(
            {
                "gate": "backup_fresh",
                "passed": False,
                "remediation": (
                    "BACKUP_ENABLED=false: no backup is arranged — arrange a "
                    "named pre-deploy backup snapshot before updating"
                ),
            }
        )
    elif backup.get("last_success_at") is None:
        gates.append(
            {
                "gate": "backup_fresh",
                "passed": False,
                "remediation": (
                    "BACKUP_LAST_SUCCESS_AT is unset: take a named pre-deploy "
                    "backup snapshot before updating"
                ),
            }
        )
    else:
        gates.append(
            {
                "gate": "backup_fresh",
                "passed": False,
                "remediation": (
                    f"last backup {backup.get('last_success_at')} is older than "
                    f"BACKUP_MAX_AGE_HOURS={settings.BACKUP_MAX_AGE_HOURS}: take "
                    "a fresh named pre-deploy backup snapshot before updating"
                ),
            }
        )

    # G5 migration dry-run: report status + plan, change nothing.
    current = _migrations.database_revision()
    if current is None:
        current = (_migrations.MIGRATION_STATE or {}).get("current_revision")
    head = _migrations.head_revision()
    if head is None:
        head = (_migrations.MIGRATION_STATE or {}).get("head_revision")
    if current and head:
        if current == head:
            gates.append(
                {"gate": "migration_plan", "passed": True, "remediation": ""}
            )
        else:
            gates.append(
                {
                    "gate": "migration_plan",
                    "passed": True,
                    "remediation": "",
                    "plan": f"database at {current}, code head at {head}: "
                    "`python -m scripts.migrate upgrade` will advance it "
                    "(run only with a named backup snapshot)",
                }
            )
    else:
        gates.append(
            {
                "gate": "migration_plan",
                "passed": False,
                "remediation": (
                    "migration state unknown (current or head revision "
                    "unreadable): run `python -m scripts.migrate status` and "
                    "resolve it before updating"
                ),
            }
        )

    return gates


#: In-process install-attempt log. The durable record is the audit chain
#: (every check/install stages an audit row); this list backs the admin
#: history view for the current process.
UPDATE_HISTORY: list[dict[str, Any]] = []


def record_history(entry: dict[str, Any]) -> dict[str, Any]:
    """Append an install-attempt entry (additive, in-memory + audit)."""
    stamped = {
        **entry,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    UPDATE_HISTORY.append(stamped)
    return stamped
