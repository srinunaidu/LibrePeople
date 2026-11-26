# Legal Review Package — PREPARED-ONLY (Tier 1, `chore/licensing-transition`)

> Status: **PREPARED-ONLY**. This file creates no rights and no obligations.
> No effective licence is published by this package: there is no root
> `LICENSE` / `COPYING` / `NOTICE`, no source headers have been inserted
> (verified: `grep -ri "SPDX-License-Identifier" backend/app frontend/src`
> returns empty), and the official AGPL-3.0 text has NOT been fetched from
> `https://www.gnu.org/licenses/agpl-3.0.txt` (see
> `docs/legal/LICENSE.AGPL-3.0.prepared`, which states the text was NOT
> fetched). Nothing here is legal advice. All blockers U1–U12 remain
> **UNRESOLVED** and all clearance items L1–L17 remain
> **UNVERIFIED** / PROPOSED / DRAFT. No owner or date is asserted beyond what
> is sourced in the registers. No push, merge, release, or visibility change
> is performed or authorised by this file.

## How to cite evidence in this package

- Blocker register (questions + status): `docs/legal/unresolved-blocker-register.md` (U1–U12, all **UNRESOLVED**).
- Clearance register (reviewer questions): `docs/legal/legal-clearance-register.md` (L1–L17, all **UNVERIFIED** / PROPOSED / DRAFT).
- Package status (prepared-vs-withheld): `docs/legal/licensing-package-status.md` (U12 / L17 **WITHHELD**).
- Ownership register: `docs/legal/ownership-and-provenance-register.md` (22 rows, all **UNRESOLVED** / pending sign-off).
- Inventory: `docs/legal/dependency-licence-inventory.json` + `docs/legal/dependency-licence-inventory.md` (713 rows: 62 direct / 651 transitive).
- Triage: 575 Confirmed / 2 Review / 3 Blocked / 133 Unknown; full record in `spec/features/licensing-triage-remediation/triage-report.md`.
- SBOM: `docs/legal/sbom-20261126T043959Z.json` (generated 2026-11-26T04:39:59+00:00; matches the 713-row inventory; evidence only, grants no clearance).
- Scanner: `ci/check_licences.py --check-only` (report-only, exit 0) and `ci/check_licences.py --strict` (future enforcement dry-run; exits 1 on Blocked/Unknown; not enforced).
- Governance docs: `docs/legal/licensing-policy.md`, `docs/legal/governance-note.md`, `docs/legal/decision-register.md`, `docs/legal/commercial-open-source-strategy.md`, `docs/legal/compliance-ci.md` (triage compatibility notes), `docs/legal/contributor-dco-guidance.md`, `docs/legal/third-party-licences.md`, `docs/legal/licensing-transition-tracker.md`, `docs/legal/provenance-evidence.md`.
- Prepared-text placeholder: `docs/legal/LICENSE.AGPL-3.0.prepared` (staging placeholder only; must not be treated as an effective grant).

# Bucket 1 — engineering-complete

> What engineering has finished (report-only, docs-only). No effective
> licensing step was taken and none is claimed.

- Inventory built: 713 rows (62 direct / 651 transitive) in `docs/legal/dependency-licence-inventory.json` (+ `.md` summary).
- Triage recorded: 575 Confirmed / 2 Review / 3 Blocked / 133 Unknown; every non-Confirmed row carries `triage_verdict` / `triage_date` / `triage_evidence`; zero Unknown rows reclassified to Confirmed.
- Fresh SBOM written: `docs/legal/sbom-20261126T043959Z.json` (matches inventory).
- Scanner run report-only: `ci/check_licences.py --check-only` exits 0; `--strict` documented as future enforcement only (see `docs/legal/compliance-ci.md`).
- Ownership register completed as evidence: 22 rows, each with origin / holder / licence / history / evidence / relicensable / approval fields; transfer rows left **UNRESOLVED**.
- Registers extended: U12 and L17 appended for this packaging pass; U1–U11 and L1–L16 carried forward unchanged.
- Package-status file created: `docs/legal/licensing-package-status.md` (prepared-vs-withheld table + per-file blockers).
- Withholding verified: no root `LICENSE` / `COPYING` / `NOTICE`; no `SPDX-License-Identifier` under `backend/app` or `frontend/src`; official text NOT fetched.

# Bucket 2 — evidence-complete

> What evidence the reviewer can rely on as present in the repo (presence,
> not sufficiency — sufficiency is the reviewer's call).

1. `docs/legal/unresolved-blocker-register.md` — exact questions U1–U12 with file-level evidence pointers; all **UNRESOLVED**.
2. `docs/legal/legal-clearance-register.md` — reviewer questions L1–L17 with evidence pointers; all **UNVERIFIED** / PROPOSED / DRAFT.
3. `docs/legal/dependency-licence-inventory.json` + `.md` — 713 rows; triage split 575 / 2 / 3 / 133 recorded per row.
4. `docs/legal/sbom-20261126T043959Z.json` — SBOM matching the inventory.
5. `spec/features/licensing-triage-remediation/triage-report.md` — triage method, scanner stdout, per-row remediation notes.
6. `ci/check_licences.py` — scanner source; `--check-only` report-only behaviour and `--strict` future-enforcement rationale (comment-only, no logic change to the Confirmed set: MIT, Apache-2.0, ISC, BSD-2-Clause, BSD-3-Clause, 0BSD, BlueOak-1.0.0).
7. `docs/legal/ownership-and-provenance-register.md` — 22-row ownership and provenance evidence with per-row evidence pointers.
8. `docs/legal/licensing-package-status.md` — prepared-vs-withheld table and per-file publication blockers (U12 / L17 **WITHHELD**).
9. Governance docs — `licensing-policy.md`, `governance-note.md`, `decision-register.md` (D1–D10), `commercial-open-source-strategy.md`, `compliance-ci.md`, `contributor-dco-guidance.md`, `third-party-licences.md`, `licensing-transition-tracker.md`, `provenance-evidence.md`.
10. `docs/legal/LICENSE.AGPL-3.0.prepared` — placeholder whose own text confirms the official AGPL-3.0 text was NOT fetched.

# Bucket 3 — legal-review

> Index of the ten review items. Each item below is stated in full under its
> numbered section (§1–§10): an exact question for the legal reviewer plus
> the evidence pointer the reviewer should open. Status of every item:
> **UNRESOLVED** / **UNVERIFIED** — reviewer determination required; this
> package asserts no answer.

- §1 Ownership → reviewer question on authorship/provenance gaps (U4; ownership 22 rows) — see §1.
- §2 Karmathy extraction rights → reviewer question on transfer instrument and signatory authority (U1, U7–U10; L12, L13) — see §2.
- §3 Third-party obligations → reviewer question on 133 UNVERIFIED backend rows, fpdf2, Oracle mix, MPL-2.0 test-only, ISC lucide-react (U2, U6, U11; L1–L5, L8–L11, L15, L16; 713-row inventory; 575/2/3/133; `sbom-20261126T043959Z.json`; scanner `--strict`) — see §3.
- §4 Contributor rights → reviewer question on contributor authorship and DCO posture (U4; governance `contributor-dco-guidance.md`, `decision-register.md`) — see §4.
- §5 Holder identity → reviewer question on prospective holder wording (U12; L17; package-status **WITHHELD**; no NOTICE text) — see §5.
- §6 AGPL suitability → reviewer question on AGPL-3.0-or-later fit given UNVERIFIED rows and missing official text (U2, U5, U6, U11, U12; L1–L5, L8–L11, L15–L17; `LICENSE.AGPL-3.0.prepared` NOT fetched) — see §6.
- §7 Docs licensing → reviewer question on CC BY 4.0 scope for original docs only (U3; L6) — see §7.
- §8 Trademark/brand → reviewer question on Karmathy mark retention vs rename and whose authority governs (U1, U7, U8; L14; ownership rows 7–8, 12) — see §8.
- §9 Commercial/dual strategy → reviewer question on dual/commercial strategy compatibility (U2, U6, U11, U12; L1–L5, L8–L11, L15–L17; `commercial-open-source-strategy.md`) — see §9.
- §10 Distribution/publication authorisation → reviewer question on what, if anything, may be published and when (U12; L17; package-status per-file **WITHHELD**: no root LICENSE/COPYING/NOTICE, no headers, no official text) — see §10.

# Bucket 4 — owner-decisions

> Owner-decision list: every item below is **OPEN** — awaiting explicit human
> owner sign-off together with legal reviewer input. No decision below has
> been concluded; none is marked as final and no publication follows from
> this package.

| # | Owner-decision (open question) | Evidence to open before deciding | Status |
|---|--------------------------------|----------------------------------|--------|
| O1 | Holder identity: what prospective holder wording, if any, may appear in a future LICENSE/NOTICE, and who signs it? (Lead must ask a human before any LICENSE/NOTICE text is drafted.) | Ownership 22 rows (holders **UNRESOLVED**); U1, U4, U7–U10; L12, L13; `licensing-package-status.md` (NOTICE **WITHHELD**) | **OPEN** — awaiting owner + legal reviewer sign-off |
| O2 | AGPL adoption: is AGPL-3.0-or-later adopted as the code posture, and with what copyright line wording? (Owner + legal reviewer decision, not engineering.) | U2, U5, U6, U11, U12; L1–L5, L8–L11, L15–L17; 713-row inventory (575/2/3/133); `sbom-20261126T043959Z.json`; scanner `--strict` notes in `compliance-ci.md`; `LICENSE.AGPL-3.0.prepared` (text NOT fetched) | **OPEN** — awaiting owner + legal reviewer sign-off |
| O3 | Dual/commercial strategy: is a dual or commercial licensing strategy pursued, and on what terms? (Owner + legal reviewer decision, not engineering.) | `commercial-open-source-strategy.md` (draft); U2, U6, U11; L1–L5, L8–L11, L15, L16; governance `decision-register.md`, `licensing-policy.md` | **OPEN** — awaiting owner + legal reviewer sign-off |
| O4 | Publication authorisation: when, if ever, may withheld files (root LICENSE/COPYING/NOTICE, official AGPL text, source headers, third-party notice changes) be created? (Explicit owner + legal sign-off required; currently blocked by U1–U12 / L1–L17.) | `licensing-package-status.md` (per-file **WITHHELD**); U12; L17; U1–U11 / L1–L16 | **OPEN** — awaiting owner + legal reviewer sign-off |
| O5 | Trademark use: retain, rebrand, or rename Karmathy marks (package names, event namespace, UI brand, SEO/schema metadata), and under whose authority? (No trademark assignment is claimed in this package.) | U1, U7, U8; L14; ownership rows 7–8, 12; `frontend/src/lib/seo.ts`; `frontend/e2e/redesign-e2e.spec.ts:96-109` | **OPEN** — awaiting owner + legal reviewer sign-off |

# Bucket 5 — publication blockers

> Every blocker below is **UNRESOLVED** / **UNVERIFIED**. Per-file withholding
> applies: no root `LICENSE` / `COPYING` / `NOTICE` exists, no source headers
> exist, the official AGPL-3.0 text has NOT been fetched, and no third-party
> notice has been added, removed, or modified.

## U-series (unresolved-blocker register) — all UNRESOLVED

| ID | Question (summary) | Withheld consequence |
|----|--------------------|----------------------|
| U1 | By what written instrument and signatory authority were Karmathy assets transferred to the LibrePeople project? | Package/brand names (`karmathy-backend`, `karmathy-frontend`), PublicLayout brand/footer — publication **WITHHELD**. |
| U2 | Are the 19 direct / 114 transitive backend licences plus fpdf2, Oracle mix, MPL-2.0 test-only, ISC lucide-react compatible with the proposed posture? | Third-party licence posture — publication **WITHHELD**. |
| U3 | What is the exact scope of "original docs" for the PROPOSED CC BY 4.0 docs grant? | Any docs licence grant — publication **WITHHELD**. |
| U4 | What are the authorship dates and contributors for each `unclear` ownership row? | Authorship-dependent headers/notices — publication **WITHHELD**. |
| U5 | Has the official AGPL-3.0 text been fetched from gnu.org and verified? | Official text and any root LICENSE/COPYING — publication **WITHHELD** (NOT fetched). |
| U6 | Slice-2 inventory (713 rows: 62 direct / 651 transitive) confirms U2 still open (fpdf2, Oracle, MPL-2.0, ISC rows UNVERIFIED). | Third-party clearance — publication **WITHHELD**. |
| U7 | By what instrument may the Karmathy brand UI surface be relicensed, rebranded, or retained? | Brand UI files (PublicLayout, DashboardFallback, ProductMockup, Thread, seo.ts, TenantContext, brand assets) — publication **WITHHELD**. |
| U8 | By what instrument may the `karmathy:*` event namespace and package/service/URL names be renamed or retained? | Event names, package names, index.html, sitemap, robots, .env.example — publication **WITHHELD**. |
| U9 | By what instrument may Karmathy-derived backend core/main and contracts/rules artefacts be relicensed? | `backend/app/main.py`, `backend/app/core/*`, contracts/rules, rule packs, test fixtures — publication **WITHHELD**. |
| U10 | By what instrument may Karmathy-referencing render/docker/makefile/scripts and the historical notice be relicensed or modified? | render.yaml, docker-compose.yml, Dockerfiles, Makefile, ci scripts, backend/scripts — publication **WITHHELD**. |
| U11 | Triage pass (575/2/3/133; 138 rows with verdicts; fresh `sbom-20261126T043959Z.json`; `--check-only` exit 0) — does triage change any clearance status? (No: evidence-gathering only.) | All 133 Unknown rows stay UNVERIFIED — publication **WITHHELD**. |
| U12 | Packaging pass (PREPARED-ONLY, `licensing-package-status.md`): why must root LICENSE/COPYING/NOTICE, official text, headers, and notice changes stay **WITHHELD** while U1–U11 remain open? | Entire prepared package — publication **WITHHELD**. |

## L-series (legal-clearance register) — all UNVERIFIED / PROPOSED / DRAFT

| ID | Question (summary) | Status |
|----|--------------------|--------|
| L1 | 19-direct / 114-transitive backend set vs future AGPL grant (114 rows UNVERIFIED). | **UNVERIFIED** — reviewer determination required |
| L2 | fpdf2 LGPL-3.0-only boundary (lazy, unmodified, unvendored use). | **UNVERIFIED** — reviewer determination required |
| L3 | Oracle UPL/Apache-2.0 mix deploy paths and posture compatibility. | **UNVERIFIED** — reviewer determination required |
| L4 | MPL-2.0 test-only confinement to test paths. | **UNVERIFIED** — reviewer determination required |
| L5 | ISC lucide-react frontend-bundle compatibility. | **UNVERIFIED** — reviewer determination required |
| L6 | CC BY 4.0 PROPOSED scope (which docs count as "original"). | PROPOSED — scope confirmation required |
| L7 | No-endorsement / no-assignment wording sufficiency. | DRAFT — reviewer to confirm |
| L8 | Slice-2 fpdf2 rows UNVERIFIED; boundary + redistributed text questions. | **UNVERIFIED** — reviewer determination required |
| L9 | Slice-2 oracledb/oci rows UNVERIFIED; deploy paths + compatibility. | **UNVERIFIED** — reviewer determination required |
| L10 | Slice-2 MPL-2.0 `@axe-core/playwright` rows; test-path confinement. | **UNVERIFIED** — reviewer determination required |
| L11 | Slice-2 ISC lucide-react rows; bundle compatibility. | **UNVERIFIED** — reviewer determination required |
| L12 | Karmathy-derived files: express grant or all-rights-reserved? | **UNVERIFIED** — reviewer determination required |
| L13 | Karmathy-derived code vs PROPOSED AGPL posture absent a transfer instrument. | **UNVERIFIED** — reviewer determination required |
| L14 | Karmathy mark retention vs rename, and whose authority (no assignment claimed). | **UNVERIFIED** — reviewer determination required |
| L15 | Triage 2 Review + 3 Blocked + 133 Unknown rows correctly left without reclassification. | **UNVERIFIED** — reviewer determination required |
| L16 | Scanner allowlist rationale suppresses nothing; fresh SBOM matches 713-row inventory. | **UNVERIFIED** — reviewer determination required |
| L17 | Packaging pass publishes nothing effective; publication must wait for U1–U12 clearance with written evidence. | **UNVERIFIED** — reviewer determination required |

## Per-file withholding summary

- Root `LICENSE` (absent) — **WITHHELD** (U5, U12; L17).
- Root `COPYING` (absent) — **WITHHELD** (U5, U12; L17).
- Root `NOTICE` (absent) — **WITHHELD** (U7–U10, U12; L12, L14, L17).
- `docs/legal/LICENSE.AGPL-3.0.prepared` as effective text — **WITHHELD** (U5; L17; placeholder only).
- Source headers under `backend/app`, `frontend/src` — **WITHHELD** (U1, U7–U10, U12; L12–L14, L17; empty grep verified).
- Karmathy-derived components (§2 file list) — **WITHHELD** (U1, U7–U10, U12; L12–L14, L17).
- Third-party notices / dependency licence texts — **WITHHELD**, unchanged (U2, U6, U11, U12; L1–L5, L8–L11, L15–L17).
- `README.md` / docs scope for any CC BY 4.0 grant — **WITHHELD** (U3, U4, U12; L6, L17).

# 1. Ownership

**Exact question for the legal reviewer:** Which files have sourced authorship
and provenance sufficient to support a future licensing grant, and which
remain `unclear` or Karmathy-derived pending a transfer instrument — in
particular the `unclear` rows (`README.md`, Dockerfiles text,
compose/render/workflow configs, `Makefile`, `ci/run_backend_tests.sh`,
app-code authorship) whose dates and contributors are not yet extracted?

**Evidence pointer:** `docs/legal/ownership-and-provenance-register.md`
(22 rows, each with origin / holder / licence / history / evidence /
relicensable / approval; transfer and contributor-authorship rows
**UNRESOLVED**); blocker U4 (authorship dates/contributors; `git log` intact
but per-file authorship not extracted); `docs/legal/provenance-evidence.md`;
governance `docs/legal/licensing-transition-tracker.md`. Status of this item:
**UNRESOLVED** — reviewer determination required; no owners or dates asserted
beyond sourced register entries. Shared evidence base: 713-row inventory,
`sbom-20261126T043959Z.json`, triage 575/2/3/133,
`spec/features/licensing-triage-remediation/triage-report.md`, scanner
`ci/check_licences.py --check-only` / `--strict` (see `compliance-ci.md`),
governance docs listed above, and `licensing-package-status.md` (U12/L17
**WITHHELD**).

# 2. Karmathy extraction rights

**Exact question for the legal reviewer:** By what written instrument and
signatory authority, if any, may Karmathy-derived assets — package names
(`karmathy-backend` in `backend/pyproject.toml:2`, `karmathy-frontend` in
`frontend/package.json:2`), the `© 2026 Karmathy` footer/brand in
`frontend/src/components/PublicLayout.tsx` (~105, ~172, ~198, ~202), brand UI
(DashboardFallback, ProductMockup, Thread design element, `seo.ts` SITE_NAME,
tenant branding fallbacks, og-image/favicon assets), the `karmathy:*` event
namespace, backend core/main (`backend/app/main.py`, `backend/app/core/*`),
contracts/rules artefacts (Karmathy-titled schemas, `signed_by: Karmathy
Compliance` packs such as `backend/rule_packs/in-standard.json:609`, test
fixtures), and render/docker/makefile/scripts (`render.yaml`,
`docker-compose.yml`, Dockerfiles, `Makefile`, `ci/run_backend_tests.sh`,
`backend/scripts/`) — be extracted, relicensed, rebranded, renamed, or
retained under the LibrePeople project, and who may sign the grant?

**Evidence pointer:** Blockers U1, U7, U8, U9, U10 (transfer/rename/relicense
instruments: none on file; all **UNRESOLVED**); clearance L12 (express grant
vs all-rights-reserved), L13 (Karmathy-derived code vs PROPOSED AGPL posture);
ownership register rows 3–12, 19–20 (Karmathy-transferred, **UNRESOLVED**);
`licensing-package-status.md` §3 isolation list (non-publishable, unchanged by
this package). Status: **UNRESOLVED** / **UNVERIFIED** — no removal, scrub,
rename, or relicensing performed. Shared evidence base: 713-row inventory,
`sbom-20261126T043959Z.json`, triage 575/2/3/133, scanner `--strict` notes in
`compliance-ci.md`, governance docs, and U12/L17 **WITHHELD**.

# 3. Third-party obligations

**Exact question for the legal reviewer:** What redistribution, attribution,
and copyleft-boundary obligations attach to the third-party set — the 133
UNVERIFIED backend rows (19 direct + 114 transitive), fpdf2 (LGPL-3.0-only per
upstream, UNVERIFIED locally; lazy import in
`backend/app/services/offer_letter.py`), the Oracle UPL/Apache-2.0 mix
(oracledb 26.0.1 + oci 2.192.0; lazy `import oci` in
`backend/app/storage/backends.py`), MPL-2.0 test-only components
(`@axe-core/playwright` dev-direct + transitive, `axe-core` transitive;
confinement unconfirmed), ISC `lucide-react` (compatibility unconfirmed), the
2 Review rows (`argparse` Python-2.0, `caniuse-lite` CC-BY-4.0), and the 3
Blocked rows — and are those terms compatible with the proposed posture?

**Evidence pointer:** Blockers U2, U6, U11 (all **UNRESOLVED**); clearance
L1–L5, L8–L11, L15, L16 (all **UNVERIFIED**); `docs/legal/dependency-licence-inventory.json`
+ `.md` (713 rows: 62 direct / 651 transitive; triage 575 Confirmed / 2
Review / 3 Blocked / 133 Unknown with per-row `triage_verdict` /
`triage_date` / `triage_evidence`); `docs/legal/sbom-20261126T043959Z.json`
(matches inventory); `spec/features/licensing-triage-remediation/triage-report.md`;
scanner `ci/check_licences.py --check-only` (exit 0, report-only) and
`--strict` (future enforcement; see `docs/legal/compliance-ci.md` triage
compatibility notes); `docs/licensing/copyleft-and-proprietary.md` (fpdf2 and
Oracle sections); governance `docs/legal/third-party-licences.md`,
`licensing-policy.md`; ownership register third-party rows; U12/L17
(`licensing-package-status.md`) — third-party notices unchanged and
**WITHHELD**. Status: **UNVERIFIED** — reviewer determination required; triage
is evidence-gathering only and changes no clearance status.

# 4. Contributor rights

**Exact question for the legal reviewer:** Apart from the sourced register
entries, who holds contributor authorship claims over this tree, under what
terms did any contributor participate (DCO or otherwise), and is the current
contributor-authorship evidence sufficient to support a future licensing
grant?

**Evidence pointer:** Blocker U4 (per-file authorship/dates not extracted;
contributor-authorship rows left unknown / **UNRESOLVED** by mandate, not
sourced from `git log`); governance `docs/legal/contributor-dco-guidance.md`,
`docs/legal/decision-register.md` (D1–D10), `docs/legal/governance-note.md`;
ownership register contributor-authorship rows (**UNRESOLVED**). Status:
**UNRESOLVED** — reviewer determination required; no contributor grant
asserted. Shared evidence base: 713-row inventory,
`sbom-20261126T043959Z.json`, triage 575/2/3/133, scanner `--strict` notes,
and `licensing-package-status.md` (U12/L17 **WITHHELD**).

# 5. Holder identity

**Exact question for the legal reviewer:** What holder identity and copyright
line wording, if any, may be used in a future LICENSE/NOTICE — is the
prospective "LibrePeople project" label sufficient, and who signs the holder
statement given that all transfer rows are UNRESOLVED?

**Evidence pointer:** Blocker U12 and clearance L17
(`docs/legal/licensing-package-status.md`: NOTICE **WITHHELD**; no notice
text has been reviewed for publication); blockers U1, U4, U7–U10 and clearance
L12, L13 (holder questions **UNRESOLVED** / **UNVERIFIED**); ownership
register (22 rows; holders **UNRESOLVED**; "LibrePeople project" used only as
a prospective label, not a rights claim); governance
`docs/legal/licensing-policy.md`, `governance-note.md`. Owner decision O1 is
**OPEN** — the lead must ask a human before any LICENSE/NOTICE text is
drafted. Status: **UNRESOLVED** — no holder or date asserted beyond sourced
entries; no NOTICE published.

# 6. AGPL suitability

**Exact question for the legal reviewer:** Is AGPL-3.0-or-later a suitable
and compatible posture for this tree given the 133 UNVERIFIED backend rows,
the fpdf2 LGPL-3.0-only boundary question, the Oracle UPL/Apache-2.0 mix, the
MPL-2.0 test-only confinement question, ISC `lucide-react`, the Karmathy
transfer gaps, and the fact that the official AGPL-3.0 text has NOT been
fetched or verified?

**Evidence pointer:** Blockers U2, U5, U6, U11, U12 (all **UNRESOLVED**);
clearance L1–L5, L8–L11, L15–L17 (all **UNVERIFIED**);
`docs/legal/LICENSE.AGPL-3.0.prepared` (placeholder; text NOT fetched from
gnu.org; must not be treated as an effective grant); 713-row inventory with
triage 575/2/3/133; `sbom-20261126T043959Z.json`; scanner `--strict` rationale
in `ci/check_licences.py` and `docs/legal/compliance-ci.md`; governance
`licensing-policy.md`, `decision-register.md`. Owner decision O2 is **OPEN**
(owner + legal reviewer decision, not engineering). Status: **UNVERIFIED** —
AGPL-3.0-or-later remains PROPOSED only; no effective grant exists (no root
LICENSE/COPYING, no headers).

# 7. Docs licensing

**Exact question for the legal reviewer:** What is the exact scope of
"original docs" for the PROPOSED CC BY 4.0 docs grant — does it include
`README.md`, `docs/licensing/`, this `docs/legal/` package, or a narrower
set — and is that scope sufficient to support the grant?

**Evidence pointer:** Blocker U3 (scope statement: none on file beyond the
human constraint "original docs only"; **UNRESOLVED**); clearance L6
(PROPOSED — scope confirmation required); `README.md`, `docs/licensing/`,
this `docs/legal/` package as the candidate scope. Owner decision: scope
confirmation is **OPEN** — awaiting owner + legal reviewer sign-off. Status:
**UNRESOLVED** / PROPOSED — no docs grant is effective. Shared evidence base:
ownership 22 rows, 713-row inventory, `sbom-20261126T043959Z.json`, triage
575/2/3/133, scanner `--strict` notes, governance docs, and U12/L17
**WITHHELD** (`licensing-package-status.md`: README/docs scope
**WITHHELD**).

# 8. Trademark/brand

**Exact question for the legal reviewer:** May the LibrePeople project retain
the Karmathy mark in the `karmathy:*` event names, the `karmathy-backend` /
`karmathy-frontend` package, service, and hosted-URL names, schema titles,
and SEO metadata — or must these be renamed — and under whose authority, given
that no trademark assignment is claimed in this package?

**Evidence pointer:** Blockers U1, U7, U8 (rename/retain authority
**UNRESOLVED**; transfer instrument: none on file); clearance L14
(**UNVERIFIED**); ownership register rows 7–8, 12 (rename authority
unverified); `frontend/src/lib/seo.ts:5,19`,
`frontend/e2e/redesign-e2e.spec.ts:96-109`, `backend/pyproject.toml:2`,
`frontend/package.json:2`, `frontend/index.html:25-26,33`,
`frontend/public/sitemap.xml`, `frontend/public/robots.txt:34`,
`frontend/.env.example:3`; governance `licensing-policy.md`,
`governance-note.md` (no endorsement claim; wording DRAFT per L7). Owner
decision O5 is **OPEN**. Status: **UNRESOLVED** / **UNVERIFIED** — no rename,
no scrub, no assignment claimed.

# 9. Commercial/dual strategy

**Exact question for the legal reviewer:** Is a dual or commercial licensing
strategy viable for this tree given the UNVERIFIED third-party set (133
backend rows, fpdf2, Oracle mix, MPL-2.0, ISC), the Karmathy transfer gaps,
and the PROPOSED-only AGPL posture — and what terms, if any, could support
it?

**Evidence pointer:** `docs/legal/commercial-open-source-strategy.md` (draft
posture; already on file, not rewritten by this package); blockers U2, U6,
U11, U12 (**UNRESOLVED**); clearance L1–L5, L8–L11, L15–L17
(**UNVERIFIED**); 713-row inventory (575/2/3/133);
`sbom-20261126T043959Z.json`; scanner `--strict` notes
(`compliance-ci.md`); governance `decision-register.md`,
`licensing-policy.md`. Owner decision O3 is **OPEN** (owner + legal reviewer
decision, not engineering). Status: **UNVERIFIED** — strategy remains draft;
no commercial terms offered or concluded by this package.

# 10. Distribution/publication authorisation

**Exact question for the legal reviewer and the owner:** What, if anything,
in the prepared package may be distributed or published, and when — i.e. do
U1–U12 and L1–L17 permit creation of root LICENSE/COPYING/NOTICE, vendoring
of the official AGPL-3.0 text, insertion of source headers, or any
third-party notice change at this time?

**Evidence pointer:** Blocker U12 and clearance L17
(`docs/legal/licensing-package-status.md`: prepared-vs-withheld table and
per-file blockers — every publishable-effect file class **WITHHELD**);
blockers U1–U11 and clearance L1–L16 (all **UNRESOLVED** / **UNVERIFIED**);
withholding facts: no root `LICENSE` / `COPYING` / `NOTICE` exists; no
`SPDX-License-Identifier` under `backend/app` or `frontend/src`; official
text NOT fetched (`LICENSE.AGPL-3.0.prepared` placeholder accurate; no full
grant text vendored under `docs/legal/`); Karmathy-derived components isolated
as non-publishable (U1, U7–U10; L12–L14); third-party terms unchanged. Owner
decision O4 is **OPEN** — explicit owner + legal sign-off required before any
withheld file is created; currently blocked by U1–U12 / L1–L17. Status:
**UNRESOLVED** / **UNVERIFIED** — nothing in this package authorises
publication.

---

## Change log for this file

- Created 2026-11-26 on `chore/licensing-transition` (Tier 1 PREPARED-ONLY):
  10 review sections (§1–§10) + 5-bucket separation (engineering-complete,
  evidence-complete, legal-review, owner-decisions, publication blockers).
- Did: gave the legal reviewer exact questions + evidence pointers and the
  owner exact open decisions (O1–O5), with blockers U1–U12 / L1–L17 recorded
  as UNRESOLVED/UNVERIFIED and per-file withholding stated.
- Did not: publish any effective licence; fetch gnu.org text; insert any
  header; modify any Karmathy-derived or third-party notice; change any
  production, dependency, or CI file; push, merge, or release.
