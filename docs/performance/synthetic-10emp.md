# Synthetic perf smoke: 10-employee SQLite (TestClient, in-process)

Date (UTC): 2026-11-22. Branch: `feature/librepeople-production`. Base commit: `9abc572`.
No Postgres, no Oracle, no prod data. Synthetic SQLite only (`/tmp/synth10.db`, deleted after run).

## HW / runtime / DB / dataset

- HW: Apple Silicon arm64 Mac, macOS 27.2.1 (local dev machine, shared tenancy, not isolated).
- Runtime: Python 3.15.0, FastAPI via `TestClient` (in-process ASGI, no sockets/TLS/network).
- DB: SQLite 3.54 file DB, NullPool (one connection per checkout), full schema via `Base.metadata.create_all`.
- Dataset: 1 dept + 1 job + 10 employees (SYN000-009, hire 2024-01-02, tenant `default`); visibility via Manager user linked to SYN000 with other 9 as direct reports.

## Method

Loop `GET /` (unauth, 100x) + `GET /api/v1/employees/` (Manager bearer token, 100x) = 200 requests, sequential, same process. Latency = client-measured ms per request. Error = HTTP 5xx or exception.

## Results (n=200, errors=0)

| Endpoint | n | 5xx/err | p50 | p95 | mean | min | max |
|---|---|---|---|---|---|---|---|
| `GET /` | 100 | 0 | 2.06 ms | 2.66 ms | 3.76 ms | 1.83 ms | 166.61 ms (first-request cold start) |
| `GET /employees/` (auth, 10 rows) | 100 | 0 | 7.15 ms | 8.45 ms | 7.22 ms | 6.27 ms | 11.75 ms |

Unauthenticated `GET /employees/` correctly returns 401 (not counted above; auth path exercised instead).

## Notes / limits

- In-process smoke only: no network, no concurrency, no PG/Oracle. NOT an NFR verification.
- Oracle Locust harness (Class C deferred): full load/Soak testing against Oracle ADB is deferred until the Locust harness + Oracle test tenancy exist; this file is only a local SQLite sanity baseline.
- NFR Performance remains NOT VERIFIED (needs harness + acceptance criteria).
