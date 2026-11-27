# Update / Version Management Architecture — LibrePeople (self-hosted)
## 1. Principles
Self-hosted, consent-gated, manual updates. No phoning home, no auto-update daemon, no forced upgrades, no private keys in repo, no auto-migration without backup. GitHub Releases is the distribution point; the installed system never pulls code by itself.
## 2. Version surface (verified today)
PROJECT_NAME="LibrePeople", VERSION in config; / returns version; /health public liveness; /health/db SuperAdmin-only migration status; /admin/status read-only (never migrates); single linear Alembic head; runner stamps legacy baseline then upgrades head; release CLI scripts/migrate.py status|upgrade|downgrade|history; CI asserts exactly one head; deploy preDeployCommand runs migrate upgrade; image runs migrate before uvicorn; backup/restore scripts exist (pg_dump custom format, restore destructive w/ snapshot-first).
## 3. Release manifest (new, in-repo)
Location: releases/manifest.json (local copy shipped per release) + per-tag asset manifest-<version>.json on GitHub Release. JSON schema checked in CI (releases/manifest.schema.json). Fields: version (semver), channel (stable|rc), released_at, git_sha, app_version, db_head_revision, min_version, breaking_changes[], notes_url, changelog, artifacts[] {name, sha256}, manifest_sha256 (chain: hash of canonical JSON minus signature block), signature {alg, key_id, sig}. Generation: scripts/make_release_manifest.py (CI release job); validates VERSION == tag, db_head == alembic head, artifact checksums.
## 4. Client update check (consent-gated)
New additive endpoints (SuperAdmin only, read-only except install): GET /api/v1/admin/updates/current; GET /api/v1/admin/updates/available (reads LOCAL releases/manifest.json; remote fetch ONLY if UPDATE_CHECK_ALLOW_REMOTE=true AND UPDATE_CHECK_REMOTE_URL set, owner-pinned host allowlist, signature-verify before trust; default both off — no egress); POST /api/v1/admin/updates/check {dry_run:true} (pre-install gates, audit row); POST /api/v1/admin/updates/install {manifest_sha256} (re-runs gates non-dry-run, records update_history; actual code deploy stays operator-driven, never self-overwriting). Config: UPDATE_CHECK_ALLOW_REMOTE=false, UPDATE_CHECK_REMOTE_URL="", UPDATE_MANIFEST_PATH="releases/manifest.json", UPDATE_SIGNING_KEY_IDS="" (pubkey IDs only).
## 5. Pre-install gates (fail-closed, all must pass)
Compat (version >= min_version), single-head assert, disk-space check, backup freshness (BACKUP_ENABLED && last_success within BACKEND_MAX_AGE... within BACKUP_MAX_AGE_HOURS), migration dry-run (migrate status + upgrade --sql plan, no write). Any fail → 409 + named remediation; install refuses.
## 6. Signing without embedded secrets
Dev/test: keyless/ephemeral signatures (clearly marked key_id: dev-ephemeral, CI warns). Production: owner-held offline key ceremony (documented runbook; pubkey IDs in repo config, private key never in repo/CI secrets beyond opaque signer). Manifest checksum chain verified by scripts/verify_release.py and by the available endpoint before display. Algorithm: minisign (owner-held key).
## 7. Migration safety + rollback
Forward-only. No auto-downgrade. Install requires named pre-deploy backup snapshot. Rollback = (a) code revert (Render rollback / compose previous image); (b) optional data restore ONLY with fresh target snapshot + owner approval. Downgrades never automatic (restore-from-backup, not downgrade base).
## 8. Admin UI surface (new page, wired)
Route /admin/updates (SuperAdmin): version panel, changelog view, checks list, install button (enabled only when all gates pass; dry-run first), history log. UI only; no router changes to existing endpoints.
## 9. CI/CD changes (additive)
CI: manifest-validate (schema+checksums), sbom, sign-verify (dev-signature round-trip), single-head gate retained. Release workflow (new, on stable tag v*): build images, SBOM, generate manifest, owner-sign step (manual approval env), create GitHub Release with manifest+SBOM+checksums. Deploy workflow unchanged except recording manifest sha in deploy record.
## 10. §14 A-M mapping
A manifest format; B local+opt-in remote check; C pre-install gates; D signatures w/o embedded keys; E migration safety; F manual + notified via admin warnings; G rollback procedure; H admin UI; I CI/CD + GitHub Release; J notifications/history audit; K compat/min-version; L backup-before-migrate; M docs/runbooks. Deferred with reason: auto-download/apply, SaaS push/fleet rollout, in-app DB downgrade as rollback.
## 11. NO-GO list
No SaaS requirement. No private keys in repo/CI logs. No auto-migration without named backup. No forced upgrades. No destructive rollback claims.
## 12. Test plan
scripts/verify_release.py on releases/manifest.json; alembic single head; new update_system_test_suite.py (manifest gates fail-closed, remote-off default, signature verify, RBAC 403); frontend typecheck + build for /admin/updates.
## Open decisions — RESOLVED by lead 2026-11-27
D1 manifest path = releases/manifest.json canonical. D2 minisign, owner-held key. D3 owner-pinned hosts only. D4 stale backup = hard block.
