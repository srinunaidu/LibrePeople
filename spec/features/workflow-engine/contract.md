# Feature: workflow-engine (minimum reusable capability)
## Behavior
One small stage core (PENDING→APPROVED|REJECTED|RETURNED, forward-only, comment required on reject/return) serving documents, assets, ER cases, and existing approvals via adapters. Supports assignment/reassignment, role-gated decisions, decision history (append-only), overdue/escalation query consumed by existing JobWorker lease pattern, notifications-hook emit, per-tenant isolation, and audit rows. Callers keep their own status columns; core records the decision trail, never owns domain state.
## Acceptance criteria
1. POST /workflows/{entity_type}/{entity_id}/decide {action,comment} enforces stage order, role gate (MANAGER_ROLES L1 / ADMIN_ROLES final), tenant match (fail-closed 404 cross-tenant), and writes audit; illegal transition → 409, wrong role → 403.
2. Reassignment POST .../reassign {to_user} restricted to admin roles, tenant-scoped, audited; overdue list GET /workflows/overdue?entity_type= returns only caller-tenant rows with due_at past.
3. Expense L1/final and HR-case resolve paths call the core (adapter, ~10 lines each) and keep current suites green; domain status columns remain source of truth (core mirrors, never mutates them directly).
4. Decision history GET /workflows/{entity_type}/{entity_id}/history is append-only, tenant-isolated, ordered; notifications hook fires once per decision (receipt/success/warning per LP-NOT-001 pattern).
5. Recovery: worker crash mid-decision leaves no half-write (single commit per decision); expired-lease pattern reused for escalation scans, no new daemon.
## Non-goals
No BPM/visual builder, parallel branches, conditional DSL, or SLA-timer engine; no migration of leave/timesheet/expenses onto the core; no changes to existing status-column semantics; no frontend in this slice.
## Interfaces / data
New: backend/app/workflows/{service,schemas,router}.py + backend/app/models/workflow_step.py (id, tenant_id, entity_type, entity_id, stage, action, actor_id, comment, due_at, created_at) + one additive migration for that table ONLY. Reuse: job_queue (escalation scans), hr_cases/expense_claims (untouched, adapters read them), audit + notifications emit. Backwards compatible: additive table + new /workflows/* routes only.
## Test plan
pytest backend/app/workflows/tests/ (machine, gates, reassignment); API suite: decide/reassign/history/overdue incl. 403/404/409 matrix; tenant-isolation probe (tenant B reads tenant A → 404); regression: leave expenses helpdesk suites green unchanged.
## Risk tier
2 (normal — additive table + new routes; no existing-table migration).
## Rollback
Drop /workflows router registration + new migration downgrade (single table); adapters are pass-through logging so removal restores hardcoded paths with no data loss.
## Open decisions
1. Entity allowlist for v1 — needs lead scope sign-off. 2. Escalation action: notify-only vs auto-reassign. 3. due_at source: caller-supplied vs per-type default.
## Lead decisions (2026-11-26)
D1. v1 allowlist = expenses + HR cases (adapters, tested now) + documents + assets (adapters, no behavior change).
D2. Escalation = notify-only (auto-reassign changes semantics; deferred).
D3. due_at = caller-supplied, nullable (NULL = never overdue).
