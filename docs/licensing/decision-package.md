# Licensing decision package (RECOMMENDED — not decided)

Status: **PROPOSAL ONLY**. No licence is granted by this document. No
`LICENSE`/`COPYING`/`NOTICE`/`CONTRIBUTING`/`CODE_OF_CONDUCT`/`SECURITY.md`
file is created by this slice — drafts below are **document contents only**.
Official licence texts are **not included**; canonical links only. Anything
that could be legal advice is labelled **requires counsel**.

## 1. Recommended application licence: AGPL-3.0-or-later (RECOMMENDED)

Reasoning: the repo already stages an AGPL posture (`docs/legal/*`,
`ci/check_licences.py` allowlist treats the dependency set as
GPL-family-compatible, `LICENSE.AGPL-3.0.prepared` stub exists but text not
fetched). AGPL-3.0-or-later matches a networked HR application (SaaS use
triggers the network clause, closing the ASP loophole MIT/Apache leave open)
and aligns with the LibrePeople project name. Alternatives rejected:
MIT/Apache-2.0 (permissive — would not preserve copyleft intent already
socialised in `docs/legal/decision-register.md` D3); GPL-3.0-only (misses
network use). **Whether AGPL is compatible with the UNVERIFIED backend set
and Oracle UPL components — requires counsel (see §3).**

- Copyright holder: **TBD OWNER** (no holder assigned; Karmathy→LibrePeople
  transfer unresolved per `docs/legal/unresolved-blocker-register.md` U1).
- Canonical text: https://www.gnu.org/licenses/agpl-3.0.html (SPDX:
  `AGPL-3.0-or-later`). Do not copy text into the repo without counsel + owner sign-off.

## 2. Recommended documentation licence: CC-BY-4.0 (RECOMMENDED)

Reasoning: docs (`docs/`, marketing copy) are not code; CC-BY-4.0 is the
standard for open documentation and is already the proposed docs expression
in the parallel slice. Code stays under §1; third-party terms unchanged —
**no relicensing of third-party work is proposed or effected**.

- Canonical text: https://creativecommons.org/licenses/by/4.0/ (SPDX: `CC-BY-4.0`).

## 3. Compatibility analysis vs the inventory (`l1-l17-review.md`)

| Group | Compatibility with §1/§2 (informational) |
|---|---|
| Frontend MIT/ISC/Apache-2.0/BSD/0BSD/BlueOak-1.0.0/Python-2.0 (lock-citable) | Permissive sets are one-way compatible with AGPL distribution (keep their notices) — **requires counsel** to confirm. |
| MPL-2.0 test-only (axe-core) | Segregated from shipped bundle; file-level copyleft does not attach to app output — **requires counsel**. |
| CC-BY-4.0 data (caniuse-lite) | Data, not code; keep attribution — **requires counsel** on notice wording. |
| LGPL-3.0-only (fpdf2, UNVERIFIED) | Lazy import, no modification — boundary question — **requires counsel** before any AGPL grant claims coverage. |
| Oracle UPL / UPL+Apache-2.0 (oci, oracledb — UNVERIFIED) | Largest risk: copyleft grant over code that imports UPL SDK/driver — **requires counsel**; commercial-licence need unresolved. |
| Backend UNVERIFIED remainder (114 transitive, 21 direct) | **No compatibility conclusion possible** until licence metadata is collected — release blocker. |
| AGPL presence | None ships today, so §1 creates no immediate self-conflict. |

## 4. NOTICE / attribution file CONTENTS (prepared text, not a committed file)

```text
THIRD-PARTY NOTICES (DRAFT — prepared only, not published as NOTICE)

This application incorporates third-party components under their own licences.
This draft lists licence identifiers citable to frontend/package-lock.json;
backend identifiers are UNVERIFIED until package metadata is collected.

- MIT / ISC / Apache-2.0 / BSD-2-Clause / BSD-3-Clause / 0BSD /
  BlueOak-1.0.0 / Python-2.0 components: see frontend/package-lock.json
  "license" fields (335 top-level node_modules entries verified carrying a field).
- CC-BY-4.0: caniuse-lite 1.0.30001816 (via browserslist) — data set.
- MPL-2.0 (test-only, not shipped): @axe-core/playwright 4.14.0, axe-core 4.14.0.
- PENDING COUNSEL: fpdf2 (LGPL-3.0-only, upstream-declared, unverified locally),
  oci (UPL-1.0, upstream-declared, unverified locally),
  oracledb 26.0.1 (UPL-1.0 and/or Apache-2.0, upstream-declared, unverified locally).
- Full licence texts are those published by the respective projects;
  canonical references: https://opensource.org/licenses,
  https://www.gnu.org/licenses/, https://creativecommons.org/licenses/by/4.0/.

Copyright holder: TBD OWNER. Historical notice preserved:
"© 2026 Karmathy. All rights reserved." (frontend/src/components/PublicLayout.tsx).
```

## 5. Appendix A — licensing policy (draft)

1. No licence is effective until owner + counsel sign the decision register.
2. Default posture until then: all rights reserved; no `LICENSE`/`COPYING`/`NOTICE` published.
3. SPDX identifiers (`AGPL-3.0-or-later`, `CC-BY-4.0`) stay PROPOSED; never add
   source headers without approval.
4. Third-party code keeps its own terms; relicensing third-party work is forbidden.
5. Range pins must be frozen before every release SBOM cut.

## 6. Appendix B — dependency compliance policy (draft)

1. Backend: collect `METADATA`/`License-Expression` for all 114 freeze rows +
   21 direct pins; UNVERIFIED never ships as cleared.
2. Frontend: re-verify `package-lock.json` licence fields on every lock update.
3. New dependency classes needing pre-approval: (a) any GPL/AGPL/LGPL/MPL,
   (b) any commercial/proprietary/UPL, (c) any dual-licensed package, (d) any
   package without machine-readable licence metadata.
4. Vendoring/forking a third-party package requires counsel sign-off + notice update.
5. Test-only copyleft must stay out of production bundles (build config evidence).

## 7. Appendix C — CONTRIBUTING draft (inside this doc only)

Contributions require Developer Certificate of Origin sign-off (`Signed-off-by`)
per `docs/legal/contributor-dco-guidance.md`; no copyright assignment is
requested. Do not paste third-party code without naming its licence. CI
`check_licences.py` is report-only until enforcement is human-approved.

## 8. Appendix D — CODE_OF_CONDUCT draft (inside this doc only)

Be respectful and inclusive; no harassment or discrimination. Maintainers
(TBD OWNER) may moderate. Reports to a contact address to be published by the
owner. This draft takes effect only when adopted by the owner.

## 9. Appendix E — SECURITY.md draft (inside this doc only)

Report vulnerabilities privately to a security contact (TBD OWNER to publish);
do not open public issues for exploits. Maintainers acknowledge within 5
business days. Supported versions table to be filled at first release.

## 10. SBOM automation proposal (describe, don't implement)

Extend `ci/check_licences.py` (currently report-only, `--strict` reserved for
future human-approved enforcement): (a) ingest `.venv` METADATA licence
expressions for the backend 114 + populate `docs/licensing/sbom/` JSON with a
per-row `evidence` field; (b) cross-check `package-lock.json` licence deltas on
each PR; (c) fail `--strict` only on Blocked/Unknown after counsel defines the
lists; (d) emit manifest with HEAD SHA + `generated_utc` (honouring
`SOURCE_DATE_EPOCH`). No code changed in this slice.

## 11. Commercial licensing policy note

No commercial licences are held or proposed here. If counsel finds Oracle UPL
terms (or any UNVERIFIED backend dep) incompatible with §1, the owner must
choose: replace the component, negotiate a commercial grant, or change the
application licence recommendation. **Requires counsel.**

## 12. BLOCKED on counsel / owner (approver names TBD)

B1. Karmathy→LibrePeople transfer instrument + who may sign (U1). B2. Grant
   election for oracledb dual licence + oci UPL compatibility with AGPL (F3).
   B3. fpdf2 LGPL boundary for lazy-import PDF path (F2). B4. Backend
   114-row licence metadata collection (F8/F9). B5. Copyright holder identity
   (TBD OWNER) + whether `© 2026 Karmathy` footer/brand transfers. B6. NOTICE
   sufficiency + CC-BY-4.0 data notice wording (F5/F9). B7. Approval to fetch
   official AGPL/CC-BY texts and publish LICENSE/COPYING/NOTICE. B8. Approval
   to enable `check_licences.py --strict` in CI.
