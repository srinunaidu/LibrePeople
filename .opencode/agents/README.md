# The Karmathy HCM lanes as OpenCode agents

Nine agents, defined as OpenCode agents, so they can be triggered by name instead of by retyping a
charter.

| Agent | Mode | What it owns |
|---|---|---|
| `platform-security` | all | identity, access control, the audit trail, data protection, the CI security gates |
| `data-import` | all | the import engine, file handling, storage, the import contract |
| `onboarding-config` | all | the setup wizard, presets, module dependencies, the configuration assistant |
| `workforce-core` | all | employees, organisation, leave, time, approvals, the employee lifecycle |
| `planning` | all | forecasting, scenarios, the roster solver, workforce analytics |
| `payroll-rules` | all | payroll, the rule packs, reconciliation, reports |
| `frontend-design` | all | the design system, the app shell, every screen, accessibility |
| `qa-validation` | all | the journeys, the suites, the feature matrix, the seed, the load harness |
| `super` | all | the registry, the audit, the plan, the board, the merge queue, the release |

Each definition's body is the lane's operating instructions. **The charter itself lives in the
repository** at `agents/<lane>/PROMPT.md`, and the lane reads it first — so the charter, the queue
and the code never drift apart.

## The permissions are the point

Every lane's definition starts with:

```yaml
permissions:
  - action: "edit"
    resource: "*"
    effect: deny
  - action: "edit"
    resource: "backend/app/api/v1/endpoints/import_export.py"   # …and its own paths
    effect: allow
```

So a lane **cannot** write outside its owned paths — not because it was asked not to, but because
the tool call is refused. It has to ask the Super Agent for anything else, which is the rule the
board depends on. Two lanes cannot edit one file because neither of them is allowed to.

Two more permissions are global to every lane:

- `git push *` → **ask**. Pushing a branch is fine, but it is confirmed.
- `git push * main*` → **deny**. No lane can deploy to production. Not the Super Agent either.

## How to trigger a lane

### One shot, from a terminal (scriptable)

```bash
cd /Users/srinivas/LLM/Workforce/Karmathy

opencode run --agent data-import \
  "Work request DI-01. Read agents/requests/DI-01.md, then agents/data-import/PROMPT.md, \
   then agents/data-import/QUEUE.md. Work in your own worktree on branch \
   agent/data-import/DI-01-import-commit. Do not merge to main. Report in \
   agents/data-import/handoffs/2026-10-21-di-01.md when the acceptance criteria pass."
```

Add `--continue` to resume that lane's last session, or `--session <id>` for a specific one.
Add `--model provider/model#variant` to pin a model for the run.

### From the interactive TUI

```bash
cd /Users/srinivas/LLM/Workforce/Karmathy
opencode
```

Then pick the lane from the agent list. The lanes are `mode: all`, so each is selectable as the
session's main agent and is also launchable as a subagent.

### From the Super Agent's session

Ask for the lane by name and it runs as a child session with its own context and its own
permissions:

```
Use the data-import agent to work request DI-01.
Use the qa-validation agent to run QA-05 in its worktree.
```

The parent session's `subagent` permissions decide which lanes it may launch.

### Running several at once

They are separate sessions with separate worktrees, so they can genuinely run in parallel — as
long as they touch different files. The board's dependency rules say which pairs are safe.

```bash
opencode run --agent platform-security "Work request PS-05. ..." &
opencode run --agent payroll-rules      "Work request PR-01. ..." &
wait
```

## What a lane must do before it reports

1. Its own worktree and branch (`git worktree add ../karmathy-<lane> agent/<lane>/<request-id>-<slug>`).
2. Stage **exact paths** — never `git add .`, never `git add agents/`.
3. The full gate, in its own worktree: the backend suites, the secret scan, the OpenAPI merge
   check, the contract drift check, the frontend verify and the journeys.
4. Every new check confirmed to fail with the defect reintroduced.
5. A handoff in `agents/<lane>/handoffs/` with the exact test outcomes.

It never merges to `main`. The Super Agent merges, one request at a time, in dependency order.

## Adding a lane

Drop a markdown file in this directory, with `description`, `mode: all`, and the same permission
shape: deny `edit` on `*`, then allow its own paths. The body is its operating instructions, and
it should point at `agents/<lane>/PROMPT.md` for the charter and `agents/<lane>/QUEUE.md` for the
work. Keep the charter in the repository — the agent definition is the entry point, not the source
of truth.
