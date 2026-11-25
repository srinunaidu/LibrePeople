# India Extraction Gates — feature/librepeople-production @ 85fa22e

Read-only gate record for the India-extract decision. PASS = evidence on file; OPEN = sign-off or target work outstanding. No approvals claimed.

| ID | Gate | Gate command | Evidence path | Status |
|----|------|--------------|---------------|--------|
| G-01 | v1 scope: INCLUDE 4, DEFERRED 8 | `python3 ci/check_requirements.py` + CSV DictReader count | `docs/product/requirements-traceability.csv` | PASS |
| G-02 | Capability: backend/rules suites present | `ls backend/*_test_suite.py rule_packs/` | `rule_packs/in-standard.json` | PASS |
| G-03 | E2E: india_final + frontend verify | `pytest backend/india_payroll_final_test_suite.py` | `backend/india_payroll_final_test_suite.py` | PASS |
| G-04 | Payroll sign-off (§29 verifier) | verifier sign-off record | `docs/release/blocker-register.md` | OPEN |
| G-05 | Migration: SQLite PASS, Oracle OPEN | `bash ci/oracle_migration_roundtrip.sh` | `ci/oracle_migration_roundtrip.py` | OPEN |
| G-06 | Security: secret_scan + suites | `python3 ci/secret_scan.py` | `backend/container_ci_security_test_suite.py` | OPEN |
| G-07 | Perf: PROPOSED targets only | `cat docs/performance/synthetic-10emp.md` | `docs/performance/synthetic-10emp.md` | OPEN |
| G-08 | Backup/restore runbook | `cat docs/runbooks/db-backup-restore.md` | `docs/runbooks/db-backup-restore.md` | OPEN |
| G-09 | Licensing: SBOM + clearance | `ls docs/licensing/sbom/` | `docs/licensing/sbom/` | OPEN |
| G-10 | Docs: readiness + closure index | `cat docs/release/production-readiness-tracker.md` | `docs/release/closure-evidence-index.json` | PASS |
| G-11 | CI/CD: workflows green | `cat .github/workflows/ci.yml` | `.github/workflows/ci.yml` | PASS |
| G-12 | Deployment: NFR-012/013 blockers | `cat docs/release/blocker-register.md` | `docs/release/decision-papers-doc-nfr.md` | OPEN |
| G-13 | Versioning + history/provenance | `git log --oneline -3` | `docs/licensing/provenance-and-exclusions.md` | PASS |
| G-14 | Tier2/3 exclusion log | `grep -i exclusion docs/licensing/provenance-and-exclusions.md` | `docs/licensing/provenance-and-exclusions.md` | PASS |

Notes: G-01 tracker reads 122 VERIFIED / 3 BLOCKED / 8 DEFERRED at HEAD ab9b392; G-06 secret_scan reports 8 test-credential findings; G-05 SQLite path passes, Oracle roundtrip unexecuted; G-04/G-12 keep status NOT READY.
