# India Standard FY 2026-27 — Skeleton Sign-off Scaffold (NOT a verification)

**Pack:** `in-standard` v0.1.0-fy2627-skeleton — `backend/rule_packs/in-standard-fy2627-skeleton.json`
**Status:** `pending_verification` — structure only. The engine gate refuses to
calculate India payroll on or after 2026-04-01 until a named human transcribes
the FY26-27 instruments and verifies the pack.

This file is a scaffold, not a sign-off. Nothing here verifies anything.

## What this skeleton is

- Same `pack_id` (`in-standard`), same table names, same band bounds and codes
  as FY25-26 — the shape a verifier will fill in.
- Every numeric `rate` / `value` is `0`; thresholds and overtime numerics are
  `null`; leave entitlements are `0`; `golden_cases` is empty.
- `effective_from` is `2026-04-01`, `effective_to` is open. FY25-26
  (`in-standard.json` v1.0.0, `2025-04-01`–`2026-03-31`, verified) is untouched.
- The resolver returns `pack=None` for `IN` on/after `2026-04-01`
  (`pending_verification`, no fallback to FY25-26). The pay-run path, the
  direct-write path and the payslip page all refuse with
  `rule_pack_not_verified`.

## What the verifier must do (all of it, before any calculation)

1. **Transcribe** the FY26-27 instruments (Finance Act 2026, EPF/ESI updates,
   state PT notifications) into the skeleton's tables. No `0` placeholder and
   no `null`-where-a-value-belongs may remain.
2. **Write golden cases** that the engine reproduces line for line
   (TDS bands, §87A, PF/ESI, PT per state, gratuity boundary if scoped).
3. **Declare scope explicitly**: a table the engine may emit from carries
   `"in_scope": true`. Gratuity stays out of scope unless the verifier both
   scopes it and verifies the pack.
4. **Fill the five verification fields** and flip `status` to `verified`:

```json
"status": "verified",
"verification": {
  "verified_by_name": "<Full legal name of the human verifier>",
  "verified_by_role": "<Role, e.g. Payroll Compliance Analyst / External Counsel>",
  "verified_on": "<YYYY-MM-DD, must be >= source.retrieved_on>",
  "source_document_reference": "<Exact citation the verifier checked>",
  "golden_case_set_id": "<the golden case set shipped in this pack>"
}
```

5. **Re-run** the gate suites below — all must be green after the flip.
6. **Commit** the verified pack with the verifier's name in the commit message.

## Gate suites (run before hand-off, and again after the flip)

```bash
bash ci/run_backend_tests.sh india
bash ci/run_backend_tests.sh payroll
bash ci/run_backend_tests.sh migration
bash ci/run_backend_tests.sh framework
cd backend && python3 -m pytest app/rules -q
```

## Guardrails the verifier must not move

- FY25-26 (`in-standard.json` v1.0.0) stays byte-identical and verified.
- No statutory value is invented here: this scaffold ships zeros and nulls only.
- The engine refuses non-verified packs by design; no test flips a file on
  disk, only status in memory. The sign-off is the human, not the signature.
