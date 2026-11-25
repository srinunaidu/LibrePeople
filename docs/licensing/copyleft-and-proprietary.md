# Copyleft and proprietary components

## fpdf2 2.9.0 — LGPL-3.0-only

- Declared pin: `fpdf2>=2.7.0,<3.0.0` in `backend/requirements.txt`;
  freeze-resolved to **2.9.0**. Licence field **UNVERIFIED** in local metadata
  (upstream declares LGPL-3.0-only; not independently verified here).
- Usage: `backend/app/services/offer_letter.py` — `from fpdf import FPDF`
  is a **lazy (function-local) import**, so the application runs without fpdf2
  installed. Only the offer-letter PDF path exercises the library.
- Fonts: built-in **Helvetica** only (`pdf.set_font("Helvetica", …)`); no
  `.ttf` vendored, no font embedding. No fpdf2 source is vendored or modified
  in this repo.
- Obligation note (informational, not legal advice): dynamic/lazy use with no
  modification or vendoring keeps the LGPL boundary at the library; redistribution
  of fpdf2 itself must still carry its licence text. Confirm with counsel before
  release.

## oracledb 26.0.1 + oci 2.192.0 — Oracle (UPL / Apache-2.0 mix)

- `oracledb==26.0.1` (freeze-confirmed). Upstream licence: **UPL-1.0 and/or
  Apache-2.0** (dual) — **UNVERIFIED** locally, confirm from package metadata.
- `oci>=2.120.0` freeze-resolved to **2.192.0**. Upstream licence: **UPL-1.0** —
  **UNVERIFIED** locally.
- Usage: `backend/app/core/database.py` (`oracle+oracledb://`), Alembic
  `env.py`, and `backend/app/storage/backends.py` `OCIObjectStorage`, where
  `import oci` is a **lazy import** (SDK not needed for local development).
- No Oracle client libraries, wallets, or SDK code are vendored
  (`backend/wallet/*` is git-ignored except `README.md`).

## No vendoring / no modification

- Repo search found no `vendor/`, `third_party/`, or `thirdparty/` directories
  (excluding `node_modules`), no bundled `.ttf` fonts, and no modified copies
  of fpdf2, oracledb, or oci sources.
- No GPL/AGPL-licensed runtime dependency was identified in the direct set;
  transitive sets remain UNVERIFIED — full licence scan still required.

No LICENSE/NOTICE file is published by this document.
