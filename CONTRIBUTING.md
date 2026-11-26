# Contributing to LibrePeople

> PREPARED-ONLY note: this document describes a **proposed** contribution
> workflow. The intended licence direction is **AGPL-3.0-or-later (PROPOSED,
> not yet granted)** — no licence has been published (no root `LICENSE` file)
> and no legal clearance is claimed. See `docs/legal/` and the README
> "License" section before distributing anything.

## Workflow overview

1. Pick or file an issue describing the change and its scope.
2. Create a short-lived feature branch from the current default branch.
3. Make small, focused commits; keep docs and tests alongside code.
4. Open a pull request using `.github/PULL_REQUEST_TEMPLATE.md`.
5. Address review feedback; a maintainer merges when checks and
   acceptance criteria pass.

## Branch conventions

- `feature/<short-topic>` — new behaviour or docs slices.
- `fix/<short-topic>` — bug fixes.
- `chore/<short-topic>` — maintenance with no behaviour change.
- `docs/<short-topic>` — documentation-only changes.
- Never commit directly to `main`; never push or merge to `main` without
  human instruction and review.

## Pull-request conventions

- One logical change per PR; link the issue it closes.
- Fill in the whole PR template: summary, testing, security, licensing,
  and docs checklists.
- CI must be green (or explain why a check does not apply to a docs-only PR).
- Keep the diff limited to the slice; no opportunistic refactors or
  unrelated files.

## Coding standards

- Follow the existing language style in the touched area (Python: PEP 8 /
  `ruff` where configured; TypeScript: existing ESLint/Prettier config).
- No secrets, credentials, or local database dumps in commits.
- India-first product scope: payroll/statutory changes need explicit
  verification evidence (see `docs/validation/`).

## Tests

- Add or update tests that prove each acceptance criterion of your slice.
- Run the documented test command and paste the result into the PR
  (e.g. `make test`, or the scoped command named in the contract).
- Docs-only changes: verify with the `ls`/`grep` checks named in the
  contract's test plan instead of inventing coverage.

## Documentation

- Update the relevant docs alongside code (validation notes, runbooks,
  registers) rather than in a follow-up PR.
- Every new or edited Markdown file starts with a top-level (`# `) heading.
- Do not edit existing technical docs outside your slice's scope.

## Security process

- Do **not** file public issues for suspected vulnerabilities.
- Follow `SECURITY.md` for reporting and disclosure (contact TBD —
  see that file).
- Call out any security-sensitive change explicitly in the PR
  (auth, crypto, PII, payroll data, dependencies).

## Licence expectations

- **No licence has been granted yet.** The direction under review is
  AGPL-3.0-or-later as PROPOSED/INTENDED only.
- Do not add licence headers to source files.
- Do not publish a root `LICENSE` file or distribute releases until
  ownership and dependency clearance are recorded in `docs/legal/`.
- Preserve existing provenance notices (including Karmathy attribution
  lines) — do not remove or rewrite them.

## Third-party rules

- No new dependency without recording its licence in the inventory
  (`docs/legal/dependency-licence-inventory.md`) and checking
  compatibility per `docs/legal/licensing-policy.md`.
- Prefer permissively-licensed or already-cleared dependencies; flag any
  copyleft, commercial-only, or unknown-licence package as a blocker.
- Vendor only what the build requires; never commit caches, binaries,
  or generated SBOM artefacts by hand.

## DCO sign-off (no CLA)

- This project uses a Developer Certificate of Origin (DCO) process.
- No Contributor Licence Agreement (CLA) exists or is required.
- Sign every commit with `Signed-off-by`:

  ```sh
  git commit -s -m "scope: concise description"
  ```

  which appends e.g. `Signed-off-by: Your Name <you@example.com>`.
- By signing off you assert you wrote the change or have the right to
  contribute it under the project's (proposed) terms, per the DCO text
  referenced in `docs/legal/contributor-dco-guidance.md`.
- PRs with missing sign-offs will be asked to re-push with `git commit -s`.
