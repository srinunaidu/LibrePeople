# Data integrity constraints (NFR-014)

Status: **safe subset enforced by `0043_integrity_expand`** (head revision).
Deferred items (C1, C3, C10) remain application-checked; no `0044` exists yet.

NFR-014 requires the database — not just the API — to preserve financial,
employment, approval and audit history. The constraint catalogue has
thirteen candidates. Ten are safe to enforce on a database that already
holds data; three are deferred until their follow-up lands.

## The catalogue

| ID | Rule | Disposition |
|----|------|-------------|
| C1 | `employees.email` canonical form (lowercase, trimmed) | **DEFERRED** — needs the application normaliser + dedup job first; a bare CHECK would fail legacy mixed-case rows |
| C2 | `pay_slips` UNIQUE(`pay_run_id`, `employee_id`) | SAFE — enforced (retried/concurrent runs cannot double-write a slip) |
| C3 | `leave_balances.available_days >= 0` + ledger invariant | **DEFERRED** — needs the reconciliation job; the ledger sum is authoritative until then |
| C4 | `expense_claims.amount >= 0` | SAFE — enforced |
| C5 | `expense_claims.status` in the claim FSM | SAFE — enforced |
| C6 | `expense_claims.payment_status` in `('UNPAID','PAID')` | SAFE — enforced |
| C7 | `leave_requests.start_date <= end_date` | SAFE — enforced |
| C8 | `leave_requests.status` in the request FSM | SAFE — enforced |
| C9 | `leave_ledger.signed_days <> 0` | SAFE — enforced |
| C10 | `pay_runs.total_net = total_gross - total_deductions` | **DEFERRED** — cross-column arithmetic with legacy rounding risk; needs the rounding review |
| C11 | `employee_history.effective_to IS NULL OR >= effective_from` | SAFE — enforced |
| C12 | `pay_slips` money `>= 0` | SAFE — enforced |
| C13 | `expense_receipts.size_bytes >= 0` | SAFE — enforced |

Every safe name is at most 30 characters (Oracle limit). Every CHECK text
is plain comparison logic that compiles on Oracle, PostgreSQL and SQLite
(no `regexp_like`, no `GLOB`). The models (`app/models/*.py`) declare the
same names and texts as the migration — the two cannot disagree.

## No silent discard

`0043` quarantines before it repairs. Every touched row is recorded in
`integrity_quarantine` (`table_name`, `row_pk`, `reason`, pre-fix values
as JSON) and the migration log prints the backfill report: quarantined
counts and repaired counts per constraint. Repairs move only towards the
least-privileged safe value, mirroring the `0009` precedent:

* unknown statuses → the initial state (`DRAFT` / `Pending`; `UNPAID` for
  money — never mark paid by guess);
* negative money/size → quarantined with the old value, then zeroed;
* inverted leave dates → swapped (order preserved, nothing lost);
* inverted history dates → `effective_to` nulled (still in force);
* zero-effect ledger rows → quarantined with the full row, then removed
  (the ledger sum is unchanged by construction);
* duplicate payslips → later copies quarantined with the full row, then
  removed, keeping the earliest.

The downgrade drops the constraints and the indexes it created but
retains a **non-empty** `integrity_quarantine` (it is the evidence of
what the upgrade repaired); an empty quarantine is dropped so that
`downgrade base` remains a true empty schema.

## What the suite proves

`backend/integrity_test_suite.py`: FK refusal, concurrent-duplicate
payslips (exactly one row survives a two-writer race), partial-rollback
atomicity, one refusal per safe CHECK, audit append-only at the database
level (UPDATE/DELETE refused by the trigger), legacy adopt with
quarantine (upgrade 0042 → head with seeded violations), every repair
branch in-process, idempotent re-run, and the 30-character /
three-dialect discipline.
