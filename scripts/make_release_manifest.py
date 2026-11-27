"""Generate a release manifest (update-system).

CI release job: validates VERSION == tag, db_head == the single Alembic
head, and artifact checksums; writes ``releases/manifest.json`` (in-repo
local copy) and prints the per-tag asset name (``manifest-<v>.json``).

Dev/test signing is keyless: ``key_id=dev-ephemeral`` and ``sig`` is the
manifest checksum itself, clearly marked. Production signing is an
owner-held offline minisign ceremony OUTSIDE this script (documented
runbook): the owner replaces the signature block with
``{"alg": "minisign", "key_id": "<pubkey id>", "sig": "<sig>"}`` and
re-runs ``scripts/verify_release.py``. This script never handles, logs,
or embeds a private key.

Usage:
    python scripts/make_release_manifest.py --tag v1.0.0 --channel rc [--dev]
    python scripts/make_release_manifest.py --tag v1.0.0 --channel stable --artifacts dist/app.tar.gz
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))


def canonical_bytes(body: dict) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def alembic_heads() -> list[str]:
    from app.core import migrations as _migrations

    from alembic import script as _script

    return list(
        _script.ScriptDirectory.from_config(_migrations._alembic_config()).get_heads()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a release manifest.")
    parser.add_argument("--tag", required=True, help="Release tag, e.g. v1.0.0")
    parser.add_argument("--channel", required=True, choices=["stable", "rc"])
    parser.add_argument("--dev", action="store_true",
                        help="Dev/test keyless signature (key_id dev-ephemeral).")
    parser.add_argument("--artifacts", nargs="*", default=[],
                        help="Artifact files to checksum into the manifest.")
    args = parser.parse_args()

    version = args.tag[1:] if args.tag.startswith("v") else args.tag

    from app.core.config import settings

    if settings.VERSION != version:
        print(
            f"FAIL: config VERSION={settings.VERSION!r} != tag version {version!r}. "
            "Bump app/core/config.py VERSION first.",
            file=sys.stderr,
        )
        return 1

    heads = alembic_heads()
    if len(heads) != 1:
        print(
            f"FAIL: expected exactly one Alembic head, found {len(heads)} "
            f"({', '.join(heads) or 'none'}).",
            file=sys.stderr,
        )
        return 1
    db_head = heads[0]

    try:
        git_sha = __import__("subprocess").check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:  # noqa: BLE001
        git_sha = "unknown"

    artifacts = []
    for raw in args.artifacts:
        path = Path(raw)
        if not path.is_file():
            print(f"FAIL: artifact not found: {raw}", file=sys.stderr)
            return 1
        artifacts.append({"name": path.name, "sha256": sha256_file(path)})

    body = {
        "version": version,
        "channel": args.channel,
        "released_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "app_version": settings.VERSION,
        "db_head_revision": db_head,
        "min_version": settings.VERSION,
        "breaking_changes": [],
        "notes_url": f"https://github.com/librepeople/librepeople/releases/tag/v{version}",
        "changelog": (
            "NOT A PRODUCTION RELEASE — synthetic dev seed manifest for the "
            "update-system slice. Production manifests carry an owner-held "
            "minisign signature." if args.dev else ""
        ),
        "artifacts": artifacts,
    }
    manifest_sha = hashlib.sha256(canonical_bytes(body)).hexdigest()
    manifest = {
        **body,
        "manifest_sha256": manifest_sha,
        "signature": (
            {"alg": "ephemeral-dev", "key_id": "dev-ephemeral", "sig": manifest_sha}
            if args.dev
            else {"alg": "minisign", "key_id": "OWNER-KEY-ID", "sig": "OWNER-SIGNS-HERE"}
        ),
    }

    out = REPO_ROOT / "releases" / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} (per-tag asset name: manifest-{version}.json)")
    print(f"version={version} db_head={db_head} sha={manifest_sha}")
    if args.dev:
        print("WARNING: dev-ephemeral signature — NOT A PRODUCTION RELEASE.")
    else:
        print("OWNER ACTION: replace the signature block via the offline "
              "minisign ceremony, then run scripts/verify_release.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
