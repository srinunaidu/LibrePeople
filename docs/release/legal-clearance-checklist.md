# Legal Clearance Checklist (owner-facing — NO clearance claimed)

- Scope: licence readiness prep only. This document claims **no clearance, no approval, no ownership**. Only owner/counsel can clear.
- Inventory basis: `docs/licensing/sbom/` from transfer — `manifest.json` (head 969d403), `backend-transitive.json` (114 freeze rows from `.venv311 pip freeze` — **no backend lock file, freeze-confirmed not lock-confirmed**), `frontend-transitive.json` (537 lock entries, citable to `frontend/package-lock.json`). Licence rule: UNVERIFIED unless a short single-line METADATA licence / lock-entry licence field is present; never inferred. No LICENSE/NOTICE is published — do not publish one from these files.
- Manifest-vs-pin reconciliation: backend pins verified against `backend/requirements.txt` (19 pins); frontend entries verified against `frontend/package-lock.json`. Versions: fpdf2→2.9.0, oci→2.192.0, oracledb==26.0.1 (freeze-confirmed, matches pin).

## Items requiring owner/counsel decision

| # | Item | Version / pin | Licence status (from existing docs) | Notes | Owner action |
|---|---|---|---|---|---|
| 1 | `oracledb` | 26.0.1 (`oracledb==26.0.1`) | UNVERIFIED locally; upstream dual UPL-1.0 and/or Apache-2.0 (unconfirmed) — see `docs/licensing/copyleft-and-proprietary.md` | Lazy use (`oracle+oracledb://`); no client libs/wallets vendored | Confirm licence from package metadata; record acceptance |
| 2 | `oci` (Oracle Cloud SDK) | 2.192.0 (`oci>=2.120.0`) | UNVERIFIED locally; upstream UPL-1.0 (unconfirmed) — see copyleft doc | Lazy `import oci` in `backend/app/storage/backends.py`; not needed for local dev | Confirm licence; record acceptance |
| 3 | `fpdf2` | 2.9.0 (`fpdf2>=2.7.0,<3.0.0`) | UNVERIFIED locally; upstream LGPL-3.0-only (unconfirmed) — see copyleft doc | Lazy function-local import in `offer_letter.py`, Helvetica built-in only, no vendoring/modification | Counsel: confirm LGPL boundary (dynamic/lazy, unmodified) before release; redistribution must carry licence text |
| 4 | Backend UNVERIFIED transitive (excl. above) | fastapi 0.111.0, Jinja2 3.1.6, markdown-it-py 4.3.0, mdurl 0.1.2, pip_api 0.0.35, pip_audit 2.10.1, scipy 1.17.1, tomli_w 1.2.0 | UNVERIFIED (no single-line METADATA licence found) | Likely benign tooling/build deps but **not verified — do not assume** | Run full licence scan; record each |
| 5 | Backend direct set (19 pins) | per `docs/licensing/backend-direct.md` | All UNVERIFIED at inventory time | No GPL/AGPL identified in direct set; transitive unverified | Full scan still required |
| 6 | No vendoring found | — | — | No `vendor/`/`third_party/` dirs, no bundled `.ttf`, no modified copies of fpdf2/oracledb/oci | Re-confirm at release cut |

## Owner sign-off (all pending)

- [ ] Licence scan completed for all UNVERIFIED rows — owner/counsel initials + date: ______
- [ ] oracledb / oci / fpdf2 accepted for redistribution model — initials + date: ______
- [ ] LICENSE/NOTICE decision recorded (publish vs withhold + why) — initials + date: ______
- [ ] Range pins (fpdf2, oci, numpy, statsmodels, ortools) re-frozen at release cut — initials + date: ______

Prepared by Team F (prep only). Nothing here is legal advice and nothing here clears anything.
