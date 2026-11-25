# Audit Deliverables — Karmathy HCM

**Current:** Phase 0 audit — 2026-10-21 — see the files below.
**Superseded:** the 2026-10-19 audit, kept verbatim in `archive/2026-10-19/`.

| File | What it contains |
|---|---|
| [`AUDIT_REPORT.md`](AUDIT_REPORT.md) | The verified baseline: repository and agent inventory, test and build results, security and incident status, findings with evidence, the ten highest-priority risks. |
| [`UPGRADE_PLAN.md`](UPGRADE_PLAN.md) | The delivery plan: phases, dependency graph, task breakdown with effort ranges and parallelisation, rollout and rollback. |
| [`FEASIBILITY.md`](FEASIBILITY.md) | Feasibility against the confirmed team, time, budget and infrastructure, with the pilot recommendation and its exclusions. |
| [`REVAMP_NOTES.md`](REVAMP_NOTES.md) | Unresolved discrepancies, documentation drift, and findings that are explicitly out of scope. |
| [`commands_run.md`](commands_run.md) | Every command run in Phase 0, with its exact outcome. Reproducible. |
| [`archive/2026-10-19/`](archive/2026-10-19/) | The previous audit, verbatim. It audited `feature/hcm-slack-revamp` at `75c3cc5`–`91024a2`. Its findings about authorisation, the published credential, ephemeral storage and the missing CI gate were **acted on** by Gate 0 and the iterations of 2026-10-20; where it is wrong today, the 2026-10-21 report says so. |

## Where the product's status of record lives

| Question | File | Owner |
|---|---|---|
| What should the product do? | `docs/product/FEATURE_CATALOG.md` | Super Agent |
| What does the product do now? | `docs/product/FEATURE_MATRIX.md` | Super Agent |
| What is the evidence for each row? | `docs/validation/FEATURE_MATRIX.md` | QA & Validation |
| What is the work? | `agents/TASK_BOARD.md` | Super Agent |
| What is blocked and who must decide? | `agents/ESCALATIONS.md`, `agents/DECISIONS.md` | Super Agent proposes, the human decides |
| What is the state of the programme? | `agents/PROGRESS.md` | Super Agent |
| What is the production state? | `agents/handoffs/` | Super Agent |

`docs/validation/FEATURE_MATRIX.md` (150 rows, the brief's IDs) and
`docs/product/FEATURE_MATRIX.md` (142 rows, the mandate's capability IDs) are **two views of one
registry**, not two registries. The mapping column in the product matrix says which legacy row
each capability came from. They must not diverge: when a legacy row is re-verified, the product
matrix moves with it.

## Status labels used in these documents

Per mandate §2.3, every finding is labelled:

- **Verified** — supported by code, command output, tests or observable system behaviour.
- **Inferred** — a reasoned conclusion with supporting evidence and stated uncertainty.
- **Proposed** — a design recommendation not yet implemented.
- **Not verified** — evidence unavailable or a test could not be completed.
- **Blocked** — requires a decision, a credential, a dependency or an approval.

No application code, configuration, production system or production data was modified to produce
this audit.
