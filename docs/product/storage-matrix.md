# Storage backend matrix (LP-DOC-003)

Status: **BLOCKED** — matrix recorded for traceability; scope/matrix approval pending per PRD §29
(supported deployment matrix, data residency/region, S3/licence decisions).
Recorded 2026-11-22 at HEAD `8beddae1ce5cd5e98427fee08f2d6c8ea70b7d86`.
Implementation: `backend/app/storage/backends.py` → `get_storage()`.

| Backend | Selection | Role | Notes |
|---|---|---|---|
| Local directory (`LocalStorage`, `settings.LOCAL_STORAGE_DIR`) | Default (incl. `STORAGE_BACKEND=local`; also OCI-config fallback) | Dev/test default; **ephemeral** on redeploy (local disk) | Path-traversal guard; atomic write+rename; read-back verified via `save_verified` |
| OCI Object Storage (`OCIObjectStorage`) | Prod opt-in (`STORAGE_BACKEND=oci` + `OCI_NAMESPACE` + `OCI_BUCKET_NAME`) | Production target (audit finding A5-02) | SHA-256 in object metadata; PAR-based `url_for`; falls back to local with error log if unavailable |
| S3 / GCS | Not supported | — | No S3/GCS backend exists in `backends.py`; requires §29 owner decision (region/residency/licence) |

Business logic is backend-agnostic: callers use the `StorageBackend` interface
(`save` / `save_verified` / `read` / `url_for` / `delete` / `exists` / `checksum`).
