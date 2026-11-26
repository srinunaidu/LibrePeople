# Commercial Open-Source Strategy (Prepared-Only Draft)

> Status: **PREPARED-ONLY — no legal effect.** The licence direction
> described here (AGPL-3.0-or-later) is **PROPOSED/INTENDED only**; no
> licence has been granted, no root `LICENSE` is published, and no legal
> clearance is claimed. Ownership and dependency clearance are pending
> (see `docs/legal/legal-clearance-register.md` and
> `unresolved-blocker-register.md`). Do not distribute releases until
> cleared.

## Provenance

- Extracted from **Karmathy**, branch `feature/librepeople-production`
  at commit `5a6461ea0709911693cae7a4b7ff897bca8c2c13`, via `git archive`
  HEAD (tracked files only). Karmathy provenance notices must be
  preserved wherever they appear.

## Licence direction: pure AGPL, rights-reserved elsewhere

- **Intended licence: pure AGPL-3.0-or-later (PROPOSED).** Every customer
  installs and operates its own instance (self-host); network use of the
  software triggers the AGPL's remote-network-interaction obligations
  once the licence is actually granted.
- Until grant, **all rights are reserved** — nothing in this document
  conveys a licence.
- Dual-licensing option (reserved for future decision): the copyright
  holder(s), once ownership is settled, **may** offer a separate
  commercial licence alongside the AGPL for customers who cannot comply
  with copyleft terms. No dual-licence terms exist yet; the decision
  maker and approval date are **TBD**. Any dual-licence grant would be
  **rights-reserved** under its own commercial terms, not a waiver of
  the AGPL for the open edition.

## Commercial model: managed hosting, implementation, support, customisation

- **Managed hosting:** operate a customer-dedicated instance on their
  behalf; each deployment stays customer-controlled with no central
  vendor control plane.
- **Implementation:** guided install, data migration, payroll/statutory
  rule-pack verification (FY gates per `docs/validation/`).
- **Support:** versioned SLAs against supported releases (support window
  TBD — see `SECURITY.md`); best-effort only while pre-release.
- **Customisation / enterprise features:** customer-specific modules,
  connectors, and enterprise hardening delivered under commercial terms
  (rights-reserved), kept separable from the AGPL core so the open
  edition remains buildable without them.
- No enterprise/commercial offering exists yet; offering owner is **TBD**.

## Copyright vs licence vs patent vs trademark

These four are distinct — do not conflate them:

- **Copyright:** who owns the work and can therefore grant (or withhold)
  licences. Ownership here is **unsettled** (Karmathy extraction
  lineage; clearance pending). Only the settled copyright holder(s) can
  grant the AGPL or any commercial/dual licence.
- **Licence:** what others are permitted to do with the work. The
  proposed licence is AGPL-3.0-or-later (INTENDED); until published via
  a root `LICENSE` plus clearance, the default is all rights reserved.
- **Patent:** rights over inventions the software may implement. This
  draft makes no patent grant, no patent non-assert beyond what the
  AGPL text itself will convey once granted, and no claim that patent
  clearance has been performed (recorded as unresolved in the blocker
  register).
- **Trademark:** rights over names and brands (e.g. "LibrePeople",
  "Karmathy"). Nothing here grants trademark use; commercial, hosting,
  or fork naming needs a separate written trademark permission, which
  does not exist yet (owner TBD).

## Enterprise and dual-licensing notes

- Enterprise/custom modules stay **rights-reserved** under commercial
  terms; they are not contributed under the AGPL unless explicitly
  relicensed in writing by their copyright holder.
- If dual licensing is adopted, the AGPL edition and the commercial
  edition share the core but differ in licence obligations; customers
  choose one lane per deployment. The dual-licensing decision maker is
  **TBD** and no commitment date is claimed.

## What must happen before any of this takes effect

1. Settle copyright ownership (Karmathy lineage) and record it.
2. Clear dependency/licence blockers (inventory + SBOM + policy).
3. Designate licence approver, clearance authority/date, commercial
   owner, and security/conduct contacts (all currently TBD).
4. Publish the root `LICENSE` and notices in a dedicated slice — not
   this one.
