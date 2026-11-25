# Repository Visibility & Governance (Agent F — no clearance claimed)

Branch: `agent/ops/visibility-governance` from `2b7652f`. Scope: this file ONLY.
No `LICENSE`/`NOTICE`/`COPYING` created. No ownership claims made. Not legal advice.

## 1. Visibility check (verbatim, public endpoint, no auth)

Command (single call): `curl -s --retry 0 --max-time 20 https://api.github.com/repos/srinunaidu/LibrePeople`
Result: HTTP 200, `EXIT:0`, recorded 2026-11-25 (UTC).

| Field | Verbatim value |
|---|---|
| `private` | `false` |
| `visibility` | `"public"` |
| `default_branch` | `"main"` |
| `created_at` | `"2026-11-25T06:09:21Z"` |
| `pushed_at` | `"2026-11-25T09:49:36Z"` |

Full response archived in operator notes (id `1471346614`, `full_name: srinunaidu/LibrePeople`).

## 2. Interpretation (honest)

**PUBLIC.** `private:false` + `visibility:"public"` + HTTP 200 → repository is publicly readable.
Prior legal package marked visibility UNVERIFIED; this check supersedes it with a PUBLIC finding.
Immediate owner action: restrict access (GitHub Settings → change visibility to private, confirm collaborator list) and hold public release until statutory + legal clearance complete.

## 3. Consolidated owner actions

| # | What | Why | Who | Minimum action |
|---|---|---|---|---|
| 1 | Statutory reviewer appointment (handover pack `fy2627-reviewer-handover.md`: all 12 items PENDING) | No FY26-27 payroll values verified; engine refuses IN pay-runs until verified | Owner | Appoint qualified Indian payroll professional (CA / compliance analyst / labour-law counsel); hand over pack + SIGNOFF + skeleton JSON; collect per-rule sign-off forms + verifier commit |
| 2 | Legal clearance (`legal-review-package.md` + `legal-clearance-checklist.md`) | 9 backend SBOM rows UNVERIFIED; oracledb/oci/fpdf2 licence questions open; no NOTICE publishable | Owner + qualified counsel | Full licence scan, confirm oracledb/oci/fpdf2 terms for distribution model, record attribution wording, sign checklist |
| 3 | Visibility confirmation (this task) — PUBLIC | Public repo exposes uncleared payroll/legal surface | Owner | Set repo private now; re-verify via Settings UI; keep private until clearance |
| 4 | Docker Desktop or CI-build decision | Production container path must be reproducible + residency-clear (decision paper recommends Compose + self-managed PG) | Owner / Ops | Decide: local Docker Desktop builds vs CI-built pinned images; record in decision register |
| 5 | Firefox matrix — in progress | E2E 116/116 Chromium only; Firefox matrix pending per browser matrix / master register | Team C (Frontend/QA) | Run Firefox matrix per `deployment-browser-matrix.md`; file evidence; close register item |

## 4. Licence-file + ownership confirmation

- Glob `**/{LICENSE,NOTICE,COPYING}*` + `find -maxdepth 2 -iname` (2026-11-25): **no matches** — no `LICENSE`/`NOTICE`/`COPYING` in repo.
- This package creates none (forbidden) and makes **no ownership, authorship, or provenance claims**.
- Known residual marker (per legal package): `frontend/package.json` name still `karmathy-frontend`, footer `© 2026 Karmathy` — owner/counsel to resolve at rebrand close.
