# Karmathy HCM — Iteration 2 Plan

**Branch:** `iter/2-mfa`
**Parent:** main (`c3680dc`)
**Focus:** MFA for SuperAdmin and HR roles (P-05) + migration

## Gaps to close (from FEATURE_MATRIX.md)

| ID | Feature | Status | Plan |
|---|---|---|---|
| P-05 | MFA for SuperAdmin and HR roles (TOTP) | MISSING | Add pyotp, MFA core module, User MFA fields, migration, enroll/confirm/disable/recovery-codes endpoints, MFA gate in deps.py for privileged roles |
| P-10 | Sensitive field masking with reveal logging | MISSING | Defer to iteration 3 (depends on field encryption wiring) |

## Files expected to change

- `backend/requirements.txt` — add pyotp, qrcode[pil]
- `backend/app/core/mfa.py` — new: TOTP generation/verification, recovery code hashing
- `backend/app/models/user.py` — add mfa_enabled, mfa_secret_hash, recovery_codes_hash, mfa_enrolled_at
- `backend/migrations/versions/0003_mfa.py` — new migration for MFA columns
- `backend/app/api/v1/endpoints/auth.py` — add MFA endpoints
- `backend/app/api/deps.py` — add MFA requirement check for SuperAdmin/HR
- `backend/mfa_test_suite.py` — new test suite
- `ci/run_backend_tests.sh` — add mfa_test_suite
- `docs/validation/FEATURE_MATRIX.md` — mark P-05 VERIFIED

## Tests to add

- TOTP secret generation and verification
- Recovery code generation, hashing, one-time use
- MFA enroll → confirm flow
- MFA gate blocks privileged endpoints until MFA confirmed
- Wrong TOTP code rejected
- Already-enrolled user cannot re-enroll without disabling first

## Decision questions (section 5)

None — all Gate 0A decisions are recorded. MFA method (TOTP) is specified in the brief.
