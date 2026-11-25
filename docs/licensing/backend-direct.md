# Backend direct dependencies — licensing SBOM

Source: `backend/requirements.txt` (19 pins). Resolved versions confirmed from
`.venv311` `pip freeze` (114 rows, see `backend-transitive.md`).
There is **no backend lock file** (`backend/*.lock` absent), so versions below
are freeze-confirmed, not lock-confirmed.

Licence status: **UNVERIFIED** for every row — no licence metadata was
collected from package metadata or PyPI at inventory time. Do not cite these
rows as licence evidence.

| # | Requirement pin | Resolved | Licence |
|---|---|---|---|
| 1 | fastapi==0.111.0 | 0.111.0 (freeze-confirmed) | UNVERIFIED |
| 2 | uvicorn[standard]==0.29.0 | 0.29.0 (freeze-confirmed) | UNVERIFIED |
| 3 | sqlalchemy==2.0.29 | 2.0.29 (freeze-confirmed) | UNVERIFIED |
| 4 | oracledb==26.0.1 | 26.0.1 (freeze-confirmed) | UNVERIFIED — see copyleft-and-proprietary.md (UPL/Apache-2.0) |
| 5 | pydantic-settings==2.3.0 | 2.3.0 (freeze-confirmed) | UNVERIFIED |
| 6 | pydantic==2.7.4 | 2.7.4 (freeze-confirmed) | UNVERIFIED |
| 7 | python-jose[cryptography]==3.3.0 | 3.3.0 (freeze-confirmed) | UNVERIFIED |
| 8 | bcrypt==4.2.0 | 4.2.0 (freeze-confirmed) | UNVERIFIED |
| 9 | python-multipart==0.0.9 | 0.0.9 (freeze-confirmed) | UNVERIFIED |
| 10 | fpdf2>=2.7.0,<3.0.0 | 2.9.0 (freeze-confirmed) | UNVERIFIED — see copyleft-and-proprietary.md (LGPL-3.0-only) |
| 11 | oci>=2.120.0 | 2.192.0 (freeze-confirmed) | UNVERIFIED — see copyleft-and-proprietary.md (UPL-1.0) |
| 12 | alembic==1.13.1 | 1.13.1 (freeze-confirmed) | UNVERIFIED |
| 13 | jsonschema==4.26.0 | 4.26.0 (freeze-confirmed) | UNVERIFIED |
| 14 | python-dotenv==1.0.1 | 1.0.1 (freeze-confirmed) | UNVERIFIED |
| 15 | pyotp==2.9.0 | 2.9.0 (freeze-confirmed) | UNVERIFIED |
| 16 | qrcode[pil]==7.4.2 | 7.4.2 (freeze-confirmed) | UNVERIFIED |
| 17 | numpy>=1.26.0 | 2.4.6 (freeze-confirmed) | UNVERIFIED |
| 18 | statsmodels>=0.14.0 | 0.15.0 (freeze-confirmed) | UNVERIFIED |
| 19 | ortools==9.15.* | 9.15.6755 (freeze-confirmed) | UNVERIFIED |

Notes:
- Extras (`uvicorn[standard]`, `python-jose[cryptography]`, `qrcode[pil]`)
  pull additional transitive packages; see `backend-transitive.md`.
- Range pins (fpdf2, oci, numpy, statsmodels, ortools) float; re-freeze on
  every release cut.
- No LICENSE/NOTICE file is published by this document.
