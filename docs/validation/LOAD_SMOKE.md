# Load Smoke Harness

**Request:** `QA-03` · **Lane:** qa-validation · **Feature ID:** `AD-10`

---

## 1. Purpose

The pilot gate requires a **load smoke result** for every release candidate. This harness measures the staging environment's capacity against the Render free tier's actual limits (512 MB memory, no static outbound IP, ephemeral disk).

The load smoke runs against the **staging environment** (local deployment against a real Oracle schema), not production. It simulates the critical user journeys and finds the maximum sustained concurrency where:
- p95 latency on the dashboard (`GET /`) and employee list (`GET /employees/`) stays under **2 seconds**
- Error rate stays below **1%**

---

## 2. Files

| File | Purpose |
|------|---------|
| `locustfile.py` | Locust harness simulating the four critical journeys |
| `ci/load_smoke.sh` | Runner script implementing the ramp profile and pass/fail logic |
| `.github/workflows/ci.yml` | CI job `load-smoke` that runs on `release/*` branches |

---

## 3. Critical Journeys Simulated

| Journey | Weight | Endpoints Exercised |
|---------|--------|---------------------|
| Sign in → dashboard → employee list → leave request → sign out | 40% | `POST /auth/login`, `GET /`, `GET /employees/`, `GET /leave/types`, `POST /leave/requests`, `POST /auth/logout` |
| Payroll run (dry run) → reconciliation view | 20% | `GET /payroll/periods`, `GET /payroll/components`, `POST /payroll/runs`, `GET /leave/reconciliation` |
| Import dry run → commit | 20% | `GET /import/template/departments`, `POST /import/departments?dry_run=true`, `POST /import/departments/commit` |
| Schedule generation | 20% | `GET /scheduling/shift-templates`, `GET /employees/`, `POST /scheduling/roster/generate`, `GET /scheduling/roster` |

All journeys use the seeded `admin` / `E2e!Bootstrap#2026` credentials from the staging environment.

---

## 4. Ramp Profile

The `ci/load_smoke.sh` script implements a four-phase ramp:

| Phase | Users | Spawn Rate | Duration | Purpose |
|-------|-------|------------|----------|---------|
| 1. Warm-up | 1 | 1/s | 1m | Let the JVM/container warm up |
| 2. Ramp up | 1 → 20 (step 2) | 1/s | 2m/step | Find the breaking point |
| 3. Sustained | *max passing* | 0 | 5m | Hold at highest passing concurrency |
| 4. Cool down | 1 | 1/s | 30s | Graceful shutdown |

The **sustained concurrency** is the highest user count where both criteria hold:
- p95 latency < 2000ms on `GET /` and `GET /employees/`
- Error rate < 1% on those endpoints

---

## 5. Pass/Fail Criteria

The harness **passes** if, during the 5-minute sustained phase:
1. p95 latency on `GET /` (dashboard) ≤ 2000ms
2. p95 latency on `GET /employees/` (employee list) ≤ 2000ms
3. Error rate on both endpoints ≤ 1%

Any violation → **FAIL** (non-zero exit code).

---

## 6. Running Locally

### Prerequisites

1. Staging environment running:
   ```bash
   bash scripts/staging/run.sh
   ```
   This starts the API on port 8011 and frontend on 4173 against the `KARMA_STAGE` Oracle schema.

2. Locust installed:
   ```bash
   pip install locust==2.15.1
   ```

### Quick smoke test (30 seconds, 5 users)
```bash
bash ci/load_smoke.sh --quick
```

### Single concurrency test (5 minutes)
```bash
bash ci/load_smoke.sh --concurrency 10
```

### Full ramp profile
```bash
bash ci/load_smoke.sh
```

### Direct Locust run (for debugging)
```bash
locust -f locustfile.py \
  --host=http://127.0.0.1:8011/api/v1 \
  --users=10 --spawn-rate=1 --run-time=5m --headless
```

---

## 7. CI Integration

The `load-smoke` job in `.github/workflows/ci.yml` runs:
- On every push to `release/*` branches (release candidates)
- On manual trigger (`workflow_dispatch`)
- After `backend`, `contracts`, and `frontend` jobs pass
- Requires a pre-running staging environment (see §8)

The result is appended to `agents/PROGRESS.md` and uploaded as an artifact.

---

## 8. Staging Environment for CI

The CI job assumes the staging environment is already running. In practice, this means:

1. **Option A (Recommended):** A scheduled workflow starts staging nightly, runs the load smoke, and tears it down.

2. **Option B:** The release manager runs `scripts/staging/run.sh` locally, then triggers the `load-smoke` workflow manually via `workflow_dispatch`.

3. **Option C (Future):** A self-hosted runner with the Oracle wallet configured runs the full staging bring-up as part of the job.

The free tier on Render has no room for a second hosted service, so staging is local. The CI runner must have network access to the Oracle Autonomous Database wallet.

---

## 9. Result Recording

On test completion, the harness appends to `agents/PROGRESS.md`:

```markdown
## Load Smoke Result

- **Date**: 2026-10-23 14:32:15
- **Sustained concurrency**: 8
- **Pass/Fail**: PASS
- **Per-endpoint p95 latency (ms) and error rate**:
  - `GET /`: p95=1240ms, err=0.00%, n=1247
  - `GET /employees/`: p95=1580ms, err=0.00%, n=1198
  - `POST /auth/login`: p95=340ms, err=0.00%, n=89
  ...
```

The release candidate must cite this result in the pilot gate.

---

## 10. Thresholds and the Free Tier

| Resource | Free Tier Limit | Harness Target |
|----------|-----------------|----------------|
| Memory | 512 MB | p95 < 2s at sustained load |
| CPU | Shared | Error rate < 1% |
| Disk | Ephemeral | No persistent state between runs |
| Outbound IP | Dynamic | N/A (staging is local) |

The harness measures **real** limits, not a local SQLite database. The Oracle schema (`KARMA_STAGE`) exercises the same engine production uses: identifier folding, reserved words, implicit DDL commits.

---

## 11. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| All requests fail with 401 | Staging not seeded with admin user | Re-run `scripts/staging/run.sh` |
| Connection refused | Staging API not running | Check `scripts/staging/run.sh` output |
| p95 > 2s at 1 user | Database cold / missing indexes | Run migrations, check schema drift |
| High error rate on import | Duplicate `code` in CSV | Ensure random codes in `journey_import_dryrun_commit` |
| Locust not found | Not installed | `pip install locust==2.15.1` |

---

## 12. Extending the Harness

To add a new journey:
1. Add a method to `KarmathyUser` in `locustfile.py`
2. Decorate with `@task(weight)`
3. Use `catch_response=True` and `response.success()`/`failure()`
4. Add the endpoint to `critical_endpoints` in `LoadSmokeState.check_criteria()` if it should gate the result
5. Update this document

---

## 13. Security & Privacy

- Uses only synthetic test accounts (`admin`, `firstlogin`, `pendingchange`)
- No real personal data, salaries, or credentials
- Runs against `KARMA_STAGE` schema (no customer data)
- Credentials are test fixtures, not production secrets
