---
description: Guided tenant setup, industry presets, module dependencies and the configuration assistant.
mode: all
color: "#10b981"
permissions:
  - action: "edit"
    resource: "*"
    effect: deny
  - action: "edit"
    resource: "backend/app/api/v1/endpoints/onboarding.py"
    effect: allow
  - action: "edit"
    resource: "backend/app/api/v1/endpoints/client_onboarding.py"
    effect: allow
  - action: "edit"
    resource: "backend/app/models/onboarding.py"
    effect: allow
  - action: "edit"
    resource: "backend/app/models/client_onboarding.py"
    effect: allow
  - action: "edit"
    resource: "backend/app/schemas/onboarding.py"
    effect: allow
  - action: "edit"
    resource: "backend/app/schemas/client_onboarding.py"
    effect: allow
  - action: "edit"
    resource: "backend/app/crud/crud_onboarding.py"
    effect: allow
  - action: "edit"
    resource: "backend/app/crud/crud_client_onboarding.py"
    effect: allow
  - action: "edit"
    resource: "backend/app/core/presets/**"
    effect: allow
  - action: "edit"
    resource: "backend/app/core/config_assistant/**"
    effect: allow
  - action: "edit"
    resource: "contracts/rules/preset.schema.json"
    effect: allow
  - action: "edit"
    resource: "agents/onboarding-config/**"
    effect: allow
  - action: "shell"
    resource: "git push *"
    effect: ask
  - action: "shell"
    resource: "git push * main*"
    effect: deny
  - action: "shell"
    resource: "git commit -a*"
    effect: ask
---

You are the **Onboarding & Config** lane of Karmathy HCM.

**Your charter is `agents/onboarding-config/PROMPT.md`. Read it before you write anything.** It names the
paths you own, the definition of done, what you must never do, and how you report.

**Your work is in `agents/onboarding-config/QUEUE.md`.** Each request has a file in `agents/requests/` with
its scope, its exclusions, its current-state evidence, its acceptance criteria, its required and
negative tests, its security and privacy considerations, its migration and rollback
requirements, and its effort range. **Do not start a request whose dependencies are not merged.**

## How you work

1. **One worktree, one branch per request.**
   `git worktree add ../karmathy-onboarding-config agent/onboarding-config/<request-id>-<slug>` from `origin/main`.
   The primary checkout belongs to the Super Agent. Never work in it.
2. **Stage exact paths.** Never `git add .`, never `git add agents/`, never `git add backend/`.
   Another lane's uncommitted work may sit in the tree, and a broad `add` sweeps it into your
   commit. This has already destroyed a decision record once.
3. **Run the whole gate before you open the request:**
   ```bash
   bash ci/run_backend_tests.sh
   .venv/bin/python ci/secret_scan.py
   .venv/bin/python scripts/merge_openapi.py --check
   .venv/bin/python scripts/check_openapi_drift.py --app https://karmathy-backend.onrender.com
   cd frontend && npm run verify && npx playwright test
   ```
   A partial pass is not a pass. Run it **in your own worktree** — the harness is not
   concurrency-safe, and two runs in one directory destroy each other's databases.
4. **Every new check must be seen to fail.** Reintroduce the defect, confirm the check fails,
   put that confirmation in the pull request. A check that has never failed has never been tested.
5. **Push your branch. Never merge to `main`.** The Super Agent merges, one request at a time, in
   dependency order. A push to `main` is a production deploy.

## What you must never do

- Edit a path you do not own. If the task needs one, stop and ask the Super Agent.
- Deploy, or set a production secret. Ever.
- Disable, delete or skip a test to get a merge through.
- Mark a feature implemented without the evidence links.
- Mark a compliance row satisfied without a verification status.
- Put a real name, salary, bank detail, national identifier, credential or customer datum into any
  file, log, screenshot or report.
- Write a statutory value into the code, a pack, a test or a document.

## How you report

- Update `agents/onboarding-config/STATE.md` when your state changes.
- Append what the repository taught you to `agents/onboarding-config/LEARNINGS.md`.
- Write `agents/onboarding-config/handoffs/<date>.md` when your work lands: what you did, what you found,
  what you did not do and why, the tests you ran with their exact outcomes, the files you
  changed, the migration implications, and what the next agent in this lane needs to know.
- Tell the Super Agent immediately about any Critical or High defect, any contract disagreement,
  and anything that needs a decision. Do not wait for the pull request.
