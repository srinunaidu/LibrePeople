# Synthetic Accounts

Roles required for validation: SuperAdmin, HR, Manager, Associate, PayrollViewer (seed uses `PayrollViewer`, not `Payroll`).

Seeding:
- SuperAdmin: `cd backend && ADMIN_INITIAL_PASSWORD='...' python -m scripts.seed_admin`
- Synthetic demo data: from repo root `python -m seed.dev.seed_dev` (idempotent; writes credentials to `seed/dev/.credentials.out`, git-ignored; refuses non-local targets).

MFA: accounts may require MFA depending on configuration; seeded SuperAdmin has `must_change_password=True`. Flag: no dedicated seed script for HR/Manager/Associate/PayrollViewer individual accounts beyond seed_dev; manual creation via SuperAdmin UI/API is required if seed_dev is not used (gap).
