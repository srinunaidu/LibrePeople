# LibrePeople
**People. Time. Pay. Connected.**
*Open by design. Simple to adopt. Reliable to operate.*
India-first, customer-controlled HCM for organisations of 10–500 people. Each customer installs and operates its own instance; no vendor-hosted control plane; the product must never require a central LibrePeople service.
> Status: extraction in progress — NOT production-ready. Payroll/statutory sign-off outstanding. PostgreSQL/Oracle live proof absent. Performance unmeasured. Licensing and ownership NOT cleared.
## Source provenance
Extracted from Karmathy, branch feature/librepeople-production at commit 5a6461ea0709911693cae7a4b7ff897bca8c2c13, via git archive HEAD (tracked files only — no history mirror, no caches, no secrets, no local databases).
## Layout
- backend/ — FastAPI API, SQLAlchemy models, Alembic migrations (0001→0047), rule packs, worker, diagnostics.
- frontend/ — React + TypeScript + Vite application and design system.
- seed/, docs/, ci/, docker-compose.yml, Dockerfiles — operations and evidence.
## Start
- Install: docs/validation/clean-install.md; Scenarios: docs/validation/e2e-scenarios.md; Limits: docs/release/release-notes-and-known-limitations.md; Gaps: docs/programme/phase2-domain-gap-register.md.
## Gates (honest)
- FY2025–26 frozen; FY2026–27 pending verification; gratuity OFF. Register: 2 VERIFIED / 105 IMPLEMENTED / 18 BLOCKED / 8 DEFERRED / 3 IN PROGRESS (136).
## License
No LICENSE published: ownership and dependency clearance pending. Do not distribute releases until cleared.
