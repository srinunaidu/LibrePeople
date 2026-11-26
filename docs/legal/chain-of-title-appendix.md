# Chain-of-Title Appendix — EVIDENCE ONLY (PREPARED-ONLY, Tier 1)

> Status: **EVIDENCE RECORD ONLY. No legal effect.** Facts observed in-repo on
> branch `agent/legal/ownership-evidence` from main HEAD `d80c0cd`. Makes no
> determination of rights or title. Open items **require counsel and/or owner
> action** as routed in `docs/legal/final-ownership-decision-register.md`.

## §A — Full contributor list (`git log --format='%an <%ae>' | sort | uniq -c`)

Total commits in scope: **198** (`git rev-list --count HEAD`), dated 2026-11-25 (71) to 2026-11-26 (127).

| Commits | Author | Class (by naming rule: bot/agent/tier/coder = automation) |
|---|---|---|
| 193 | `srinivas <srinivas@example.com>` | Human-appearing (no automation marker in name; identity not otherwise verified here) |
| 2 | `tier-coder <tier-coder@local>` | **Automation** (`ed454ba` test move/regen 2026-11-26; `d9975d8` Team A detector fix 2026-11-25) |
| 2 | `LibrePeople Extraction <extraction@librepeople.local>` | **Automation** (`f8877a1` establish standalone repo; `62d741a` migrate verified HCM backend+frontend, both 2026-11-25) |
| 1 | `Agent E (Deployment+Ops) <agent-e@librepeople.local>` | **Automation** (`daddd21` standalone ops: compose, images, secrets-driven deploy, runbook, 2026-11-25) |

DCO signal: **zero** `Signed-off-by` trailers found across all 198 commit messages (`git log --format='%b' | grep -c` = 0). The DCO workflow is described in `CONTRIBUTING.md` / `docs/legal/contributor-dco-guidance.md`, but no sign-off is evidenced in history. Finding is factual; sufficiency **requires counsel**.

## §B — Top-10 files by size: first/last commit (`git log --follow`)

### backend/app (source files only; `__pycache__`/`.pyc` excluded)

| File (size) | First commit (in this repo) | Last commit (in this repo) | Revisions |
|---|---|---|---|
| `backend/app/api/v1/endpoints/payroll.py` (78,984 B) | LibrePeople Extraction, 2026-11-25, migrate verified HCM | same (single revision) | 1 |
| `backend/app/core/presets/preset.schema.json` (78,241 B) | LibrePeople Extraction, 2026-11-25 | same | 1 |
| `backend/app/services/scheduling.py` (52,023 B) | LibrePeople Extraction, 2026-11-25 | same | 1 |
| `backend/app/services/forecasting.py` (45,646 B) | LibrePeople Extraction, 2026-11-25 | same | 1 |
| `backend/app/api/v1/endpoints/auth.py` (43,316 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-25, rebrand Karmathy→LibrePeople + DEFAULT_CURRENCY USD→INR | 2 |
| `backend/app/rules/engine.py` (42,093 B) | LibrePeople Extraction, 2026-11-25 | same | 1 |
| `backend/app/api/v1/endpoints/core_hr.py` (42,028 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-26, workflow-engine stage + migration 0050 | 2 |
| `backend/app/imports/analyse.py` (36,901 B) | LibrePeople Extraction, 2026-11-25 | same | 1 |
| `backend/app/core/presets/data/light_manufacturing.json` (32,776 B) | LibrePeople Extraction, 2026-11-25 | same | 1 |
| `backend/app/core/presets/data/healthcare_clinic.json` (32,772 B) | LibrePeople Extraction, 2026-11-25 | same | 1 |

### frontend/src

| File (size) | First commit | Last commit | Revisions |
|---|---|---|---|
| `frontend/src/pages/People.tsx` (82,302 B) | LibrePeople Extraction, 2026-11-25 | same | 1 |
| `frontend/src/pages/ess/ESSHub.tsx` (77,002 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-26, ux ds-unify b3 | 3 |
| `frontend/src/pages/RosterBuilder.tsx` (62,696 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-26, ux ds-unify b2 | 3 |
| `frontend/src/pages/performance/PerformanceHub.tsx` (60,366 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-26, ux ds-unify b3 | 3 |
| `frontend/src/index.css` (44,195 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-25, rebrand Karmathy→LibrePeople | 2 |
| `frontend/src/pages/admin/ComplianceCenter.tsx` (41,896 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-26, ux ds-unify b3 | 3 |
| `frontend/src/App.tsx` (41,463 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-26, feat(er) Employee Relations module | 5 |
| `frontend/src/pages/payroll/PayRunDetail.tsx` (40,528 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-26, ux ds-unify b3 | 2 |
| `frontend/src/types/index.ts` (40,479 B) | LibrePeople Extraction, 2026-11-25 | same | 1 |
| `frontend/src/pages/learning/LearningHub.tsx` (38,407 B) | LibrePeople Extraction, 2026-11-25 | srinivas, 2026-11-26, ux ds-unify b3 | 3 |

Pattern observed (factual): every top-20 file's first in-repo commit is the
Extraction migration of 2026-11-25; later revisions are by `srinivas`
(rebrand, design-system unification, new modules). Pre-extraction authorship is
not evidenced in this repository. Nothing here is asserted about rights.

## §C — Karmathy→LibrePeople transfer: extraction evidence (facts, no conclusions)

Evidence found in-repo:

1. **README provenance statement** (`README.md`, "Source provenance"):
   extracted from Karmathy, branch `feature/librepeople-production` at commit
   `5a6461ea0709911693cae7a4b7ff897bca8c2c13`, via `git archive HEAD`
   (tracked files only — no history mirror, no caches, no secrets, no local
   databases). The sibling `../Karmathy` working copy exists adjacent to this
   repo on the same machine (its HEAD observed at `c9ced0f` during this slice;
   Karmathy-side history was not audited — out of scope).
2. **Migration chain continuity**: `backend/migrations/versions/` holds 58
   files; `backend/migrations/proof/history.txt` records the chain narrative
   from early revisions through `0046_assets -> 0047_expense_category_tenant_code`
   (head). Chain text is present and internally sequential as recorded.
3. **First-commit contents**: `f8877a1` (standalone repo: `.gitignore` +
   `README.md`, incl. the "ownership NOT cleared" status line) then `62d741a`
   (bulk migrate of verified HCM backend+frontend). The README itself states
   "Licensing and ownership NOT cleared" and "No LICENSE published".
4. **Preserved Karmathy marks** (verbatim, not scrubbed): package names
   `karmathy-backend`/`karmathy-frontend`, `© 2026 Karmathy` footer,
   `karmathy:*` events, `signed_by: Karmathy Compliance`, Karmathy-titled
   schemas — locations per `docs/legal/provenance-evidence.md`.

What this evidence does and does not show (factual): the records above document
*how the files arrived* (archive-based extraction + in-repo continuation).
They do not include any grant, assignment, or authorisation. This appendix
records that distinction and routes it: **requires counsel/owner** (U1, U7–U10).

## §D — Transfer documentation: EXISTS vs MISSING

Search run: `git ls-files | grep -iE 'assign|transfer|deed|contribut|cla|copyright|license|notice|employment|contractor|waiver'` + root listing for
`LICENSE`/`COPYING`/`NOTICE`. (`node_modules` excluded from consideration.)

**EXISTS in-repo (factual list):**

- `CONTRIBUTING.md` — proposed contribution workflow referencing DCO sign-off (process description, not a signed instrument; zero sign-offs found in history).
- `docs/legal/contributor-dco-guidance.md` — DCO guidance; explicitly states no CLA exists.
- `docs/legal/LICENSE.AGPL-3.0.prepared` — stub noting the AGPL-3.0 text was NOT fetched (not effective).
- `docs/legal/ownership-and-provenance-register.md` + `provenance-evidence.md` + `decision-register.md` + `unresolved-blocker-register.md` + `legal-clearance-register.md` — prepared-only evidence registers (explicitly not rights claims).
- `README.md` provenance + status lines ("ownership NOT cleared", "No LICENSE published").

**MISSING (sought, not found — absence verified by the search above):**

- Signed IP assignment or transfer deed (Karmathy→LibrePeople).
- Employment agreements covering contributor work.
- Contractor / consultancy agreements with IP provisions.
- Contributor declarations or signed DCO/CLA records (no CLA per guidance; no DCO trailers in history).
- Copyright notices file (`NOTICE`), licence text (`LICENSE`/`COPYING`) — root has none (verified).
- Brand/trademark authorisation for Karmathy marks and `© 2026 Karmathy` footer.
- Relicensing authority for `signed_by: Karmathy Compliance` rule packs.
- Pre-extraction authorship records (expected absent: archive carried no history).

Each MISSING item maps to its U-item in the decision register and **requires
counsel/owner** to supply or determine.

## §E — Third-party / vendored / generated

- **Vendored directories**: none found. `find . -maxdepth 2` for
  `vendor*`/`third_party*`/`3rdparty*` (excluding `node_modules`) returned
  nothing. Dependencies resolve via `backend/requirements.txt` and
  `frontend/package-lock.json` (538 lock entries per prior register). If
  vendoring appears later it must be registered; reviewer to confirm.
- **Generated files**: repository `generated` artefacts previously recorded are
  machine-output inventories/SBOMs (`docs/legal/sbom-*.json`,
  `dependency-licence-inventory.json`, `docs/licensing/sbom/*`). A repo-wide
  grep for "generated / auto-generated / DO NOT EDIT" matched only ordinary
  docstrings (e.g. "Generates synthetic demo data", "Building the CSV
  template…") — i.e. prose containing the word "generat", not machine-generated
  file markers. No `SPDX-License-Identifier` headers were added by this slice
  (no source files touched).
- **Third-party surface** (pointers, not re-audited): dependency manifests,
  container base images (`python:3.11-slim`, `node:20-alpine`, `nginx:alpine`),
  Google Fonts link + `lucide-react` (ISC) + static assets under
  `frontend/public/`, fpdf2 lazy import in `backend/app/services/offer_letter.py`.
  Licence compatibility **requires counsel** (U2/U6/U11).

## §F — Seed / demo-data provenance

- `seed/dev/seed_dev.py` — header: "Karmathy HCM — deterministic synthetic seed
  generator … Generates synthetic demo data for a local or staging database.
  Refuses to run against a production target." Synthetic-data claim rests on
  this header text; no independent verification run in this slice.
- `seed/prod/seed_prod.py` — header: "Production seed script — loads seed data
  into the production Oracle database. Bypasses the seed_dev.py production
  guard by connecting directly to Oracle." The bypass of the dev guard is
  recorded here as an observed fact for owner/counsel attention (handling of
  this script **requires owner** designation of responsible party + counsel
  view before any production use).
- `rule_packs/demo-synthetic-draft.json` — filename asserts synthetic/draft;
  content provenance not verified here.
- No attestation file confirming absence of production/personal data was found
  (MISSING — requires owner attestation if seed ships).

## §G — Closure checklist for this appendix

- [ ] Owner identifies responsible parties currently marked UNKNOWN (employer(s) of `srinivas`; Karmathy rights holder; `Karmathy Compliance` signatory controller; seed attestor).
- [ ] Counsel confirms sufficiency of `git log` as authorship evidence and of the archive-based extraction record.
- [ ] Each MISSING instrument in §D either filed or formally waived by counsel with written record.
- [ ] This appendix and its companion register re-verified after any rebrand/rename (marks currently verbatim; any change needs prior U7–U10 closure).
