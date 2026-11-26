# Feature: licensing-governance-docs

## Behavior
Adds PREPARED-ONLY Phase 2 governance docs (no legal effect, no publish, no push): contribution, conduct, security, issue/PR templates, README licence section, commercial strategy, DCO guidance. AGPL-3.0-or-later described only as PROPOSED/INTENDED.

## Acceptance criteria
1. `ls CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md` succeeds; none existed on base.
2. `grep -qi "Contributor Covenant" CODE_OF_CONDUCT.md && grep -q "2\.1" CODE_OF_CONDUCT.md` passes.
3. `grep -qi "Supported Versions" SECURITY.md && grep -qi "report" SECURITY.md` passes; policy defines disclosure rule without inventing owner/date.
4. `ls .github/ISSUE_TEMPLATE/bug_report.md .github/ISSUE_TEMPLATE/feature_request.md .github/ISSUE_TEMPLATE/documentation.md .github/PULL_REQUEST_TEMPLATE.md` succeeds.
5. Each template in (4) greps positive for `testing`, `security`, `licensing`, and `docs`/documentation checklist items.
6. `grep -qi "AGPL.*PROPOSED\|PROPOSED.*AGPL\|INTENDED" README.md` passes; README covers AGPL-intent + self-host + commercial hosting/implementation/support/customisation, with explicit no-clearance disclaimer.
7. `ls docs/legal/commercial-open-source-strategy.md` succeeds; `grep -qi "pure AGPL\|managed hosting" <file> && grep -qi "dual\|rights reserved" <file>` passes.
8. Strategy doc distinguishes copyright vs licence vs patent vs trademark (grep each term, case-insensitive).
9. CONTRIBUTING or `docs/legal/contributor-dco-guidance.md` documents DCO sign-off (`Signed-off-by`) with no CLA invented; `grep -qi "DCO\|Signed-off-by"` passes.
10. Guards pass: `test ! -f LICENSE`; `grep -rqi karmathy README.md docs/legal/commercial-open-source-strategy.md`; `grep -qi "People.Time.Pay.Connected\|Open by design" README.md`; `git status --porcelain` shows only allowed new docs + README/strategy edits, excluding harness task input under spec/features/ and uncommitted sibling-slice paths on same branch (documented stacked work); `git rev-parse --abbrev-ref HEAD` != `main`.

## Non-goals
No root LICENSE publication; no licence-header insertion; no dependency/package changes; no CI workflow changes; no repo-visibility change; no push/merge to main; no legal clearance claimed; no invented owners/dates; no GNU endorsement; existing technical docs untouched.

## Interfaces / data
Docs-only. New: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, 3 issue templates, 1 PR template, docs/legal/commercial-open-source-strategy.md, contributor/DCO guidance (in CONTRIBUTING or standalone). Modified: README licence section only. No schemas, migrations, config, or API changes. Backwards-compatible.

## Test plan
`ls` checks per criteria 1/4; `grep` guards per 2/3/5/6/7/8/9/10; every new/edited `.md` has H1 (`grep '^# ' file`); `make -n test` inspected (no CI/behavior change); markdown/yaml lint if configured (e.g. `npx --yes markdownlint-cli '**/*.md'` / `yamllint .github/`), else H1+grep suffices. New tests: none (docs-only).

## Risk tier
2 (normal, docs-only PREPARED-ONLY; reversible, no legal effect, no push).

## Rollback
`git checkout -- README.md && git clean -fd CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md .github/ISSUE_TEMPLATE/bug_report.md .github/ISSUE_TEMPLATE/feature_request.md .github/ISSUE_TEMPLATE/documentation.md .github/PULL_REQUEST_TEMPLATE.md docs/legal/commercial-open-source-strategy.md` (plus DCO file if standalone); verify with `git status --porcelain`.

## Open decisions
1. Security reporting contact + CoC enforcement contact (no placeholder owner to invent)?
2. AGPL-3.0-or-later final approver and clearance date/authority?
3. Commercial entity/offering owner for hosting/implementation/support/customisation?
4. DCO-only vs future CLA, and dual-licensing decision maker?
