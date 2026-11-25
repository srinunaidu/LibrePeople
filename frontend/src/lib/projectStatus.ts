/**
 * Project Status — single source of truth.
 *
 * This file IS the project's truth. The dashboard page
 * `frontend/src/pages/ProjectStatus.tsx` renders it, and
 * `STATUS.md` mirrors it. Edit here; everything else follows.
 *
 * Ids are stable (p0_audit, ps_03 …). Status vocabulary:
 *   phase: done | running | pending
 *   task:  done | running | pending | open
 *   gate:  pass | open
 */

export type TaskStatus = "done" | "running" | "pending" | "open";
export type PhaseStatus = "done" | "running" | "pending";
export type GateStatus = "pass" | "open";

// ---------------------------------------------------------------------------
// Health — the 4 numbers that matter every day
// ---------------------------------------------------------------------------
export interface HealthRow {
  label: string;
  value: string;
  detail?: string;
}

export const HEALTH: HealthRow[] = [
  { label: "capabilities", value: "38 / 143 (26.6 %)", detail: "~53 partial · ~52 missing · 0 broken" },
  { label: "requests", value: "62 — 60 done · 2 partial · 0 not started", detail: "55 done at audit · +7 hubs in this phase" },
  { label: "defects", value: "3 low open", detail: "D-029 operationId · D-017 seed guard · D-045 picker search" },
  { label: "quality gate", value: "4 172 checks · 0 failed (33 suites)", detail: "1 779 security · 70 browser (54+16) · 69 staging / Oracle ×2" },
  { label: "frontend", value: "97 routes · 1.15 MB", detail: "tsc + routes + build green · 2 516+ modules" },
  { label: "contract drift", value: "314 matched · 36 planned · 0 failures", detail: "301 operationId warnings (cosmetic)" },
];

// ---------------------------------------------------------------------------
// Gates — must pass before the next phase starts
// ---------------------------------------------------------------------------
export interface Gate {
  id: string;
  label: string;
  status: GateStatus;
  detail: string;
}

export const GATES: Gate[] = [
  { id: "g0", label: "G0: audit & plan", status: "pass", detail: "Repo inventory, baseline 520 checks, 150-row matrix, 11 risks, plan — AUDIT_REPORT.md at 70a8745" },
  { id: "g1", label: "G1: security & data", status: "pass", detail: "No open Critical/High · DEC-000 closed · role matrix 1 730 checks · payroll gate 422" },
  { id: "g2", label: "G2: contracts & jobs", status: "pass", detail: "Drift 0 failures · 210 undeclared→0 · job lifecycle 44 checks · harness per-process DB" },
  { id: "g3", label: "G3: import & presets", status: "pass", detail: "Import journeys 504 checks · 6 presets validate · readiness check" },
  { id: "g4", label: "G4: core HCM", status: "pass", detail: "HR-12 / WC-04 done (85+64 checks) · leave ledger · J5–J7 pass" },
  { id: "g5", label: "G5: forecasting & scheduling", status: "pass", detail: "11 planning requests · CP-SAT solver · versioning · J8–J9 pass" },
  { id: "g6", label: "G6: payroll integrity", status: "pass", detail: "PY-03 + PY-10 implemented · reconciliation · bank export pending (revenue item, not gate-blocking)" },
  { id: "g7", label: "G7: experience & design", status: "pass", detail: "11/11 FD done + ESS + onboarding + ledger + Platform polish — all on main, 97 routes" },
  { id: "g9", label: "G9: release hardening", status: "open", detail: "Load smoke on staging · backup rehearsal · QA-07 negatives · SUP-04 hosted staging" },
];

// ---------------------------------------------------------------------------
// Phases — 0..9, every request mapped as a task
// ---------------------------------------------------------------------------
export interface Task {
  id: string;
  label: string;
  status: TaskStatus;
  detail: string;
}

export interface Phase {
  id: string;        // p0 .. p9
  code: string;      // p0_audit …
  title: string;     // Audit and decisions …
  status: PhaseStatus;
  gate: string;      // one-line gate of the phase
  tasks: Task[];
}

export const PHASES: Phase[] = [
  {
    id: "p0", code: "p0_audit", title: "Phase 0 — Audit and decisions",
    status: "done",
    gate: "Repo inventory, baseline and plan approved — no code changed.",
    tasks: [
      { id: "audit_repo", label: "repo inventory", status: "done", detail: "259 ops, 26 models, 6 migrations, 8 lanes — AUDIT_REPORT.md §2 at 70a8745" },
      { id: "audit_baseline", label: "baseline results", status: "done", detail: "17 suites · 520 checks · secret scan · OpenAPI merge · journeys 10 pass — §4" },
      { id: "feature_registry", label: "feature registry", status: "done", detail: "FEATURE_CATALOG.md 143 caps + FEATURE_MATRIX.md 150 legacy rows" },
      { id: "decisions", label: "decisions & risks", status: "done", detail: "DECISIONS.md 16 decisions (incl. DEC-000) · 12 risks R1–R12 · pilot definition" },
      { id: "upgrade_plan", label: "upgrade plan", status: "done", detail: "UPGRADE_PLAN.md 9 phases, 29–47 ew, 7 broken caps flagged" },
    ],
  },
  {
    id: "p1", code: "p1_security", title: "Phase 1 — Security and data integrity",
    status: "done",
    gate: "No open Critical/High; DEC-000 closed; role matrix green; payroll gate enforced.",
    tasks: [
      { id: "ps_01", label: "ps_01 — admin reset guard", status: "done", detail: "ADMIN_RESET_PASSWORD ack gate · idempotent · audited — 0023_audit" },
      { id: "ps_02", label: "ps_02 — secret-scan allowlist", status: "done", detail: "11 findings → 0 · allowlist with reasons · CI green" },
      { id: "ps_03", label: "ps_03 — audit guarantee + missing events", status: "done", detail: "source_ip_hash · login_locked · unknown-user row · redacted details · same-txn — audit_test_suite 29 checks" },
      { id: "ps_04", label: "ps_04 — hash chain + append-only", status: "done", detail: "prev_hash/entry_hash · CAS head · DB triggers (DEC-027) · verify_audit_chain CLI — 57 checks" },
      { id: "ps_05", label: "ps_05 — central role policy", status: "done", detail: "300 ops (5 public) · ad-hoc removed · security_test_suite 1 730 checks" },
      { id: "ps_07", label: "ps_07 — denylist as digests", status: "done", detail: "SHA-256 · offset-independent · --self-test in CI" },
      { id: "ps_08", label: "ps_08 — migration Oracle portable", status: "done", detail: "3 round-trip cycles (upgrade→downgrade→upgrade)" },
      { id: "ps_09", label: "ps_09 — duplicate index fix", status: "done", detail: "duplicate lease_expires_at removed · create_all() on Oracle" },
      { id: "sup_03", label: "sup_03 — one worktree per lane", status: "done", detail: "worktree discipline · branch per request" },
      { id: "pr_01", label: "pr_01 — payroll gate (verified pack)", status: "done", detail: "422 rule_pack_not_verified · nothing written · payroll_test_suite 148 checks" },
      { id: "di_01", label: "di_01 — import commit actually commits", status: "done", detail: "atomic commit · counts from DB · audit row · import_test_suite" },
      { id: "di_02", label: "di_02 — token bound to result hash", status: "done", detail: "hash + TTL · reuse refused · cross-user 403" },
      { id: "py_01", label: "py_01 — salary per pay period", status: "done", detail: "engine + offer letter + import template all say per period" },
    ],
  },
  {
    id: "p2", code: "p2_contracts", title: "Phase 2 — Contracts, jobs and data integrity",
    status: "done",
    gate: "Contract drift green; job lifecycle proven; harness concurrency-safe.",
    tasks: [
      { id: "sup_02", label: "sup_02 — contract triage", status: "done", detail: "210 undeclared → 0 · merged OpenAPI up to date" },
      { id: "qa_05", label: "qa_05 — concurrency-safe harness", status: "done", detail: "per-process temp DB · 2 concurrent runs 25/25" },
      { id: "di_03", label: "di_03 — leave ledger + queued import as job", status: "done", detail: "ledger path proven · queued import executed by JobWorker" },
      { id: "ps_10", label: "ps_10 — jobs monitor API", status: "done", detail: "GET /admin/jobs (paged, filters) + /{id} + retry/discard · admin_jobs_test_suite 63 checks" },
      { id: "ps_11", label: "ps_11 — job queue worker", status: "done", detail: "0024_job_input_payload · claim/heartbeat/complete · permanent refusal → dead on attempt 1 · 42 checks" },
      { id: "ps_12", label: "ps_12 — audit chain verification endpoint", status: "done", detail: "GET /admin/audit/verify (ADMIN_ROLES) · {checked_entries, head, reason} · 39 checks" },
      { id: "di_04", label: "di_04 — import progress endpoint", status: "done", detail: "GET /import-export/.../progress/{job_id} · state/rows/batches/report · 35 checks" },
      { id: "di_05", label: "di_05 — migration 0007 re-runnable", status: "done", detail: "ix_import_dry_runs_token deduplicated (ORA-01408)" },
      { id: "di_06", label: "di_06 — cancel uncommitted import", status: "done", detail: "POST /cancel · owner-scoped · 409 if committed · 14 checks" },
    ],
  },
  {
    id: "p3", code: "p3_import_presets", title: "Phase 3 — Import, presets and onboarding",
    status: "done",
    gate: "Import journeys pass valid/invalid/idempotent/oversized; presets validate; setup resumable.",
    tasks: [
      { id: "oc_01", label: "oc_01 — presets + dependency graph + readiness", status: "done", detail: "6 presets · requires graph enforced · readiness check · provenance tracking" },
      { id: "pr_02", label: "pr_02 — tax band semantics", status: "done", detail: "banded lower_bound/upper_bound/rate · keyed-map percentage · band without rate → refused" },
      { id: "pr_03", label: "pr_03 — demo synthetic pack", status: "done", detail: "demo-synthetic-draft.json (draft, synthetic values)" },
      { id: "pr_04", label: "pr_04 — employer contribution column", status: "done", detail: "pay_slips.employer_contributions · reconciliation checks it" },
      { id: "pr_05", label: "pr_05 — reconciliation with employer contributions", status: "done", detail: "no request file — merged (payroll-rules)" },
      { id: "sup_01", label: "sup_01 — release gates + merge queue", status: "done", detail: "no request file — merged (super)" },
    ],
  },
  {
    id: "p4", code: "p4_core_hcm", title: "Phase 4 — Core HCM workflows",
    status: "done",
    gate: "Effective-dated history, leave ledger and lifecycle enforced — J5–J7 pass.",
    tasks: [
      { id: "wc_01", label: "wc_01 — public contact endpoint", status: "done", detail: "POST /public/contact · 3 fields · rate limit · Intake state" },
      { id: "wc_02", label: "wc_02 — leave ledger + derived balance", status: "done", detail: "leave_ledger · balance = SUM(rows) · 100 checks in leave_test_suite" },
      { id: "wc_03", label: "wc_03 — ledger reversal entry", status: "done", detail: "cancellation = reversal row (never deletion)" },
      { id: "wc_04", label: "wc_04 — employee directory contract", status: "done", detail: "GET /employees/ → {items, meta} · search/status/dept/manager/sort · 64 checks" },
      { id: "hr_13", label: "hr_13 — master data lifecycle", status: "done", detail: "edit/archive/guarded delete for 5 entities · 13 ops · 35 checks" },
      { id: "hr_12", label: "hr_12 — effective-dated history + lifecycle", status: "done", detail: "employee_history (7 fields) · close-and-append · FSM · 409 invalid_state_transition · 85 checks" },
    ],
  },
  {
    id: "p5", code: "p5_forecasting", title: "Phase 5 — Forecasting and scheduling",
    status: "done",
    gate: "Forecast accuracy reported; constraints tested; J8–J9 pass.",
    tasks: [
      { id: "an_01", label: "an_01 — demand forecast (history + driver CSV)", status: "done", detail: "seasonal-naive + Holt-Winters · confidence bands" },
      { id: "an_03", label: "an_03 — scenario forecasting", status: "done", detail: "scenario store + compare · compliance/scenarios" },
      { id: "an_04", label: "an_04 — cost forecast", status: "done", detail: "labour cost forecast" },
      { id: "an_05", label: "an_05 — versioned scenario builder", status: "done", detail: "versioned scenarios · compliance/scenarios" },
      { id: "an_06", label: "an_06 — forecast accuracy + sync", status: "done", detail: "MAPE/MASE on ForecastRun · input_hash/rule_version/window" },
      { id: "sc_01", label: "sc_01 — roster solver (OR-Tools CP-SAT)", status: "done", detail: "CP-SAT solver · hard constraints · scheduling/roster/generate" },
      { id: "sc_02", label: "sc_02 — roster publish", status: "done", detail: "POST /scheduling/roster/publish · confirmed action" },
      { id: "sc_03", label: "sc_03 — shift swaps", status: "done", detail: "POST /scheduling/swaps + approve/reject" },
      { id: "sc_04", label: "sc_04 — roster versioning", status: "done", detail: "versioned rosters" },
      { id: "sc_05", label: "sc_05 — attendance integration", status: "done", detail: "attendance → roster handoff" },
      { id: "sc_06", label: "sc_06 — leave → roster handoff", status: "done", detail: "approved leave blocks roster" },
    ],
  },
  {
    id: "p6", code: "p6_payroll", title: "Phase 6 — Payroll integrity",
    status: "done",
    gate: "Payroll calculation proven on verified pack; reconciliation ties totals to inputs.",
    tasks: [
      { id: "py_03", label: "py_03 — approved time/leave drives payslip", status: "done", detail: "only Approved rows consumed · overtime at derived rate · inputs_json served · 13 checks" },
      { id: "py_10", label: "py_10 — payroll blocked unless verified pack", status: "done", detail: "422 rule_pack_not_verified · one audit row recording refusal, no figure" },
      { id: "fd_08_payroll", label: "fd_08_payroll — pay-run lifecycle screens", status: "done", detail: "PayRuns / PayRunDetail (process/approve/finalize + reconciliation + payslips) / PayrollSetup — all on main at dfa853a" },
      { id: "py_followups", label: "payroll follow-ups — bank export, corrections, proration", status: "open", detail: "Roadmap #1 revenue item — not in current batch, queued after frontend complete" },
    ],
  },
  {
    id: "p7", code: "p7_experience", title: "Phase 7 — Experience and design system",
    status: "done",
    gate: "Every tab one product; every served backend verb has a caller; 97 routes green.",
    tasks: [
      { id: "fd_02", label: "fd_02 — import screen reads HTTP verdict", status: "done", detail: "dry-run counts · row-error CSV · token flow" },
      { id: "fd_06", label: "fd_06 — forecasting workspace", status: "done", detail: "forecast views · method/bands/window" },
      { id: "fd_07", label: "fd_07 — screen resilience + role truth", status: "done", detail: "per-call safe() · allSettled · role-truth empty states" },
      { id: "fd_11", label: "fd_11 — import follows job + Cancel", status: "done", detail: "polls progress every 2s · Cancel · removed when cancelled — e2e/import-queued" },
      { id: "fd_12", label: "fd_12 — screens tell truth about server answers", status: "done", detail: "failed list ≠ empty · payslip inputs_json + rule trace · job result · 5 journeys · 8 backend checks" },
      { id: "fd_13", label: "fd_13 — audit screen verifies chain", status: "done", detail: "GET /admin/audit/verify on request · names broken entry + reason · 4 journeys" },
      { id: "fd_14", label: "fd_14 — directory reads server pages/filters", status: "done", detail: "{items, meta} · search/status/dept · N of total · 7 pickers via fetchAllEmployees()" },
      { id: "fd_15", label: "fd_15 — employee panel shows/changes employment", status: "done", detail: "history table · change form · only changed fields · refusal with allowed moves · 1 journey" },
      { id: "phase_a_tokens", label: "phase_a — design tokens + identicality", status: "done", detail: "--teal/green/violet/warning-text + dark remaps · rounded-card · dark badge fills · ClientOnboarding token-clean · People PageHeader · window.prompt/confirm → dialogs — 1b21435" },
      { id: "fd_08_hubs", label: "fd_08 — performance / learning / benefits hubs", status: "done", detail: "PerformanceHub (6 cards) · LearningHub (5) · BenefitsHub (4) — all allSettled, role gates — 1cde738" },
      { id: "fd_09_10_admin", label: "fd_09_10 — admin hubs + Import enrichment", status: "done", detail: "IntegrationsHub · DataQuality · UserAdmin + Import columns/template/export — 1cde738" },
      { id: "ess_onboarding_ledger", label: "ess + onboarding config + leave ledger", status: "done", detail: "ESSHub (9 cards: profile/notifications/files/directory/org/alignments/feedback/announcements/checks) · OnboardingConfig (presets/readiness) · LeaveLedger (timeline/reconciliation/payroll-input) — 95d9cbd" },
    ],
  },
  {
    id: "p8", code: "p8_ai", title: "Phase 8 — AI capabilities",
    status: "pending",
    gate: "Only approved capabilities land, and the 13 controls land with the first one.",
    tasks: [
      { id: "ai_controls", label: "ai_controls — 13 mandatory AI controls", status: "open", detail: "permission-aware retrieval · no PII in prompts · injection defence · tool allowlists · human approval · traceability · evaluation datasets — AI-12/AI-13" },
      { id: "ai_tier_a", label: "tier_a — policy search, classification, drafting", status: "open", detail: "AI-01..AI-05 — HR policy search with citations, classification, help drafting" },
      { id: "ai_tier_b", label: "tier_b — forecast/schedule/skills analysis", status: "open", detail: "AI-06..AI-10 — forecast explanation, schedule recommendations, skills-gap analysis" },
      { id: "ai_tier_c", label: "tier_c — draft-then-approve actions", status: "open", detail: "AI-11 — draft change, permission check, impact, approval, execute, record" },
      { id: "ai_prohibitions", label: "prohibitions — no autonomous rejection/termination", status: "open", detail: "AI-13 — autonomous rejection, eligibility, termination, compensation changes forbidden" },
    ],
  },
  {
    id: "p9", code: "p9_release", title: "Phase 9 — Integration, validation, release",
    status: "pending",
    gate: "No open Critical/High; all evidence published; human go/no-go recorded.",
    tasks: [
      { id: "qa_07", label: "qa_07 — contract + cross-tenant negatives", status: "open", detail: "schema-alignment fixed · negative tests not written — partial" },
      { id: "sup_04", label: "sup_04 — hosted staging service", status: "open", detail: "local KARMA_STAGE exists · hosted Render staging pending (free-tier constraint) — partial" },
      { id: "load_smoke", label: "load smoke on staging", status: "open", detail: "harness built · in CI · not yet executed on live staging" },
      { id: "backup_rehearsal", label: "backup & restore rehearsal", status: "open", detail: "no backup script yet — AD-08 · STORAGE_BACKEND=local ephemeral" },
      { id: "fd_01", label: "fd_01 — monorepo split (api-client/tokens/theme)", status: "open", detail: "packages/api-client + tokens + tenant-theme on main · packages/ui + Turborepo deferred (DEC-013) — partial" },
      { id: "operation_ids", label: "operationId publishing (D-029)", status: "open", detail: "301 operationId warnings — contract IDs ≠ app route names (cosmetic)" },
      { id: "picker_search", label: "picker search (D-045)", status: "open", detail: "7 employee pickers read all pages, no server-side search" },
    ],
  },
];

// ---------------------------------------------------------------------------
// Deploys — last 5 (PROGRESS.md §8)
// ---------------------------------------------------------------------------
export interface DeployRow {
  time: string;
  commit: string;
  backendDeploy?: string;
  frontendDeploy?: string;
  notes: string;
}

export const DEPLOYS: DeployRow[] = [
  { time: "2026-10-27 06:23", commit: "95d9cbd", backendDeploy: "dep-dbg45nfs8m70", frontendDeploy: "dep-dbg45nfs8mk0", notes: "Code in production — 0026_employment_history applied · drift 314/36/0" },
  { time: "2026-10-27 06:26", commit: "0706fd5 (docs)", backendDeploy: "dep-dbg479brjlhs73couc60", frontendDeploy: "unchanged", notes: "Docs-only · worker restarted" },
  { time: "2026-10-27 09:xx", commit: "1b21435", notes: "Phase A design identicality — tokens, dialogs, headers" },
  { time: "2026-10-27 09:xx", commit: "1cde738", notes: "Phase B — 6 hubs (performance/learning/benefits/admin) + Import enrichment" },
  { time: "2026-10-27 10:xx", commit: "95d9cbd", notes: "ESS + OnboardingConfig + LeaveLedger + Platform polish — Phase 7 done" },
];

// ---------------------------------------------------------------------------
// References — where the truth lives on disk
// ---------------------------------------------------------------------------
export interface Reference {
  label: string;
  path: string;
  desc: string;
}

export const REFERENCES: Reference[] = [
  { label: "Feature catalog", path: "docs/product/FEATURE_CATALOG.md", desc: "143 capabilities — target state (not what exists)" },
  { label: "Feature matrix (status of record)", path: "docs/product/FEATURE_MATRIX.md", desc: "143 rows with status + evidence + lane + priority" },
  { label: "Validation matrix", path: "docs/validation/FEATURE_MATRIX.md", desc: "150 legacy rows — row-level evidence annex" },
  { label: "Task board", path: "agents/TASK_BOARD.md", desc: "62 requests — board of record (mirrors GitHub Issues when available)" },
  { label: "Progress & deploy log", path: "agents/PROGRESS.md", desc: "Headline, §2 feature table, §8 production actions — historical record" },
  { label: "Status tracker (this page's mirror)", path: "STATUS.md", desc: "Human-readable tracker — rendered from this file" },
  { label: "Decisions", path: "agents/DECISIONS.md", desc: "16 decisions DEC-000..DEC-032 — owner decides" },
  { label: "Audit report", path: "docs/audit/AUDIT_REPORT.md", desc: "Phase 0 report — 7 broken caps, 11 risks R1–R12" },
  { label: "Upgrade plan", path: "docs/audit/UPGRADE_PLAN.md", desc: "9 phases, 29–47 ew, dependency graph" },
  { label: "Feasibility", path: "docs/audit/FEASIBILITY.md", desc: "Effort & timeline estimates" },
];

// ---------------------------------------------------------------------------
// Derived helpers
// ---------------------------------------------------------------------------
export function allTasks(): Task[] {
  return PHASES.flatMap((p) => p.tasks);
}

export function tasksByStatus(status: TaskStatus): Task[] {
  return allTasks().filter((t) => t.status === status);
}

export function phasesByStatus(status: PhaseStatus): Phase[] {
  return PHASES.filter((p) => p.status === status);
}
