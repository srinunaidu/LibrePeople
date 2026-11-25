# Audit Deliverables — Karmathy HCM

**Date:** 2026-10-19 · **Mode:** read-only analysis
**Target:** `feature/hcm-slack-revamp` — started at `75c3cc5`; frontend advanced to `91024a2` during the audit,
with 10 uncommitted frontend files at close. Backend unchanged across that range.

| File | What it contains | Start here if… |
|---|---|---|
| `AUDIT_REPORT.md` | Part A findings against `DOCUMENT.md`: inventory, backend, frontend, tests, deployment, claims, compliance. Every finding has evidence, severity and effort. | you want the evidence |
| `UPGRADE_PLAN.md` | Prioritized fix list (must/should/improve), frontend revamp phases with engineer-week ranges and dependencies, backend workstreams, rollout/rollback. | you want to plan the work |
| `FEASIBILITY.md` | Owner answers, capacity math, realistic dates, infrastructure limits, cost table, risk register, final recommendation. | you want the decision |
| `REVAMP_NOTES.md` | Smaller defects and documentation drift found during the audit, plus stale prior notes that should not be redone. | you are about to start the revamp |
| `commands_run.md` | Every command and output summary: inventory, tests, builds, audits, live checks, Lighthouse, contrast. | you want to reproduce a number |

**Headline:** the code is a working, broad HCM app, but object-level authorisation is missing on 73 reads and 7
writes; the documented default admin credential still works in production; production storage is ephemeral; there
are no schema migrations and no CI gate. Under the chosen single-tenant-per-customer model, the schema-wide
`tenant_id` project is avoided, but object-level authorisation remains Critical. A security-only pilot on the
existing UI is feasible in ~1.7–3.4 months at 30–40 h/week; a customer-facing revamp is not a 1–3 month project.
The five requested compliance regimes (SOC 2, ISO 27001, GDPR, CCPA, India statutory payroll) are not achievable
with one engineer and a $0 budget in that window.

No application code, configuration or data was modified by this audit.
