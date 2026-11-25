# R2 object storage integration

LibrePeople can store uploads, offer letters and onboarding documents in a
Cloudflare R2 bucket through its S3-compatible API
(`backend/app/storage/s3.py`, `S3CompatibleStorage` over `boto3`).

## Configuration

| Variable | Required | Meaning |
|---|---|---|
| `STORAGE_BACKEND` | yes | Set to `s3` to select this backend (`local` and `oci` unchanged). |
| `R2_ENDPOINT_URL` | yes | The bucket's S3 endpoint (`https://<account>.r2.cloudflarestorage.com`). |
| `R2_BUCKET` | yes | Bucket name. The bucket is assumed **private**. |
| `R2_ACCESS_KEY_ID` | yes | R2 API token access key. |
| `R2_SECRET_ACCESS_KEY` | yes | R2 API token secret. Never committed; env vars only. |
| `R2_REGION` | no | Defaults to `auto` (R2 ignores region for routing). |

With `STORAGE_BACKEND=s3` but any `R2_*` value missing, `get_storage()`
logs an error and falls back to local storage — boot never crashes.

## Contract

* `save` stores SHA-256 as S3 object metadata (`sha256`); `checksum` reads
  it via `HEAD` without downloading; inherited `save_verified` raises
  `ChecksumMismatch` on divergence.
* `url_for` returns a presigned `GET` URL (default 1 h expiry,
  `DEFAULT_URL_EXPIRY_SECONDS`), never a public URL.
* Uploads are validated before hitting the network: non-empty relative key,
  ≤ 25 MB (`MAX_OBJECT_BYTES`), valid content type.

## Tests

`backend/r2_storage_test_suite.py` (7 tests, moto in-memory S3, no network):
round-trip, checksum metadata + `save_verified`, mismatch path, delete/exists,
validation hooks, presigned URL, `get_storage` wiring incl. fallback.

## Live proof

Not yet run: no R2 endpoint/credentials are present in this environment
(`API.md` holds no R2 values; no `R2_*` env vars). Before production, run a
proof write under `librepeople-proof/<run-id>/` in the testing bucket only,
delete the files after, and record durations here.
