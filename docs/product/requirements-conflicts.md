# Requirements conflict register

Purpose: register legacy decisions in `/Users/srinivas/LLM/Workforce/Requirement India.txt` that are not aligned with the approved LibrePeople PRD (`/Users/srinivas/LLM/Workforce/librepeople-prod/docs/product/PRD.md`) or the decision register (`/Users/srinivas/LLM/Workforce/librepeople-sec/LibrePeople_PRD_Traceability_Register.csv`). The approved LibrePeople PRD and product-owner decisions override this legacy document; the legacy document is preserved unmodified.

CSV implementation states: no DONE/PARTIAL rows; all 136 requirements are NOT STARTED.

| Decision # | Legacy decision text | Status | Winner source | Rationale | Impact |
|---|---|---|---|---|---|
| 1 | Legacy line 4 (D1 / "managed" positioning): "Business model: Open-source software + paid managed cloud hosting + implementation + support + consulting." | LOST | PRD §1, PRD §20 | Product is customer-controlled; no vendor-hosted SaaS control plane. | Vendor-hosted SaaS control plane removed from the managed model; India remains the primary market scope (PRD §4). |
| 2 | Legacy line 47 (A3): "Architect for at least 1,000 employees per tenant to avoid premature architectural limitations." | LOST | PRD §4, PRD §25.1 | Independent per-customer installations; no shared multi-tenant architecture; target 10–500 with measured performance. | No shared multi-tenant architecture introduced. |
| 3 | Legacy line 34 (B3): "Decision: Retain Karmathy for now. Use Karmathy India as the working product identity." | TAKEN-PARTLY | PRD §27, PRD §29 | Product name is LibrePeople; Karmathy retained as the existing codebase. | Product name LibrePeople; Karmathy remains the existing codebase name. |
| 4 | Legacy line 40 (B11): "Decision: Indian SMB and mid-market businesses." | WON | PRD §4 | Legacy SMB (10–200) and mid-market (201–500) within the approved target market. | Legacy scope retained; product targets approximately 10–500 employees (PRD §4). |
| 5 | Legacy line 76 (B13): "Decision: Support all major employment categories. Permanent, Probation, Contract, Fixed-term, Trainee, Intern, Consultant." | TAKEN-PARTLY | LP-CORE-002, LP-CORE-005 | PRD supports employment status/probation (LP-CORE-002) and configurable employee fields (LP-CORE-005); the legacy 7-category list is not mandated. | Hiring categories configurable via employee status/fields; verify legacy list against LP-CORE-002/005. |
| 6 | Legacy lines 189/195 (C16): "GPS-based attendance as an optional feature. Location tracking must be proportionate and transparent." | WON | LP-TIME-008 | LibrePeople keeps geolocation optional and transparent. | Geolocation/GPS attendance optional, transparent and policy-controlled (LP-TIME-008). |
