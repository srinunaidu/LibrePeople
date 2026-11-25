# India Standard FY 2025-26 — Verification Hand-off (in-standard)

**Pack:** `in-standard` v1.0.0 — `backend/rule_packs/in-standard.json`  
**Status:** `pending_verification` — the engine gate refuses to calculate India payroll until a named human verifies and flips `status` to `verified`.

## What the verifier must do

1. **Read the source documents** cited in the pack's `source` block against the pack's rate tables, thresholds and golden cases.
2. **Fill the five verification fields** in `in-standard.json` and flip the status:

```json
"status": "verified",
"verification": {
  "verified_by_name": "<Full legal name of the human verifier>",
  "verified_by_role": "<Role, e.g. Payroll Compliance Analyst / External Counsel>",
  "verified_on": "<YYYY-MM-DD, must be >= source.retrieved_on>",
  "source_document_reference": "<Exact citation the verifier checked, e.g. Finance Act 2025 §... EPF Scheme para 26A dated ...>",
  "golden_case_set_id": "gc-in-standard-001"
}
```

3. **Re-run** `bash ci/run_backend_tests.sh india && bash ci/run_backend_tests.sh payroll && cd backend && .venv/bin/python -m pytest app/rules -q` — all must remain green after the flip (golden cases are replayed in-memory as `pending→verified` in the suite; after the real flip they must still pass on disk).

4. **Commit** the verified pack with the verifier's name in the commit message; the signature in `signing` is not cryptographically verified by the loader (same as `us-standard-verified.json`) — verification is the human sign-off, not the signature.

## Fields the human must fill

| Field | Description |
|-------|-------------|
| `verified_by_name` | Full name of the person who checked the rules against the cited source and the golden cases |
| `verified_by_role` | Role (e.g. `payroll compliance analyst`) |
| `verified_on` | Date of verification `YYYY-MM-DD` |
| `source_document_reference` | Precise document reference the reviewer actually checked (may be more specific than `source.document_reference`) |
| `golden_case_set_id` | Must be `gc-in-standard-001` — the 11 cases shipped in `golden_cases` |

## Status flip

`pending_verification → verified` only. Do not use `draft` or `superseded`. Once verified, the pack is the only one that may drive a production payroll calculation for `IN` in `2025-04-01` to `2026-03-31`. The loader (`load_rule_pack_for_date`) and the engine (`calculate_payslip_from_pack`) both refuse a non-verified pack; the suite proves the refusal.

## Checklist — items marked “checklist” in the pack and the code

These were left as single-value v1 simplifications and must be confirmed or ticketed before or at verification:

- [ ] **MH Feb ₹300 / annual cap ₹2,500** — Maharashtra PT monthly table is flat ₹200; February is ₹300 and the annual cap is ₹2,500. v1 monthly table encodes ₹200 every month. Decide whether v1.1 must encode the February exception and the cap.
- [ ] **TN half-yearly slabs** — Tamil Nadu PT statute is half-yearly (₹0–21,000→₹0; 21,001–30,000→₹0? actual slabs vary by notification). v1 collapses to ₹0 below ₹25,000 / ₹208.50 above. Confirm the correct monthly equivalent or restore half-yearly.
- [ ] **WB 10 rows** — West Bengal PT table has 10 rows from 0–5,000→0 up to 40,000+→200. Re-derive each bound and amount from the WB Act notification and confirm.
- [ ] **Employer PF split** — EPF employer 12% is legally 8.33% EPS (capped at ₹15,000 → ₹1,250) + remainder EPF. v1 records employer PF as 12% flat. Decide whether the payslip must split `PF_ER` into `EPS_ER`/`EPF_ER` and whether the EPS wage ceiling is the same.
- [ ] **Marginal relief above ₹12L** — §87A rebate is ₹60,000 up to ₹12L taxable, but Finance Act 2025 provides marginal relief just above ₹12L (so net tax does not jump). v1 rebate is `min(band_tax, 5000)` when `taxable ≤ 100000`; above the limit there is no rebate and no relief. Decide whether v1.1 must encode marginal relief.
- [ ] **Single salary field = PF/ESI base is full gross** — EPF “wages” is Basic+DA, not gross. v1 uses `base_salary` (the only salary field) as PF/ESI base and caps it at ₹15,000. Record as v1 simplification; decide whether a `basic_da` split is needed.
- [ ] **Band bounds rounding** — Monthly bounds 33333.33 / 66666.67 are annual/12 rounded to 2dp; annual slabs are the statute. Re-derive monthly bounds (33333.33 = 400000/12 → 33333.333…, etc.) and confirm the 2dp rounding the engine pins (golden cases state the arithmetic per band).
- [ ] **ESI 21000.01 edge** — ESI is skipped when `base > 21000`; at `21000` exactly it applies (`0.75%`/`3.25%`). The engine uses `Decimal` comparison, never float. Confirm.
- [ ] **Gratuity** — Payment of Gratuity Act 1972 is explicitly excluded from v1 (no accrual). Confirm deferral to a later slice.

## Loader notes

- The loader does **not** cryptographically verify `signing.signature`; same as the US pack today. `key_id: in-standard-key`, `signed_at` at content freeze (2026-03-31T00:00:00Z). Verification is the human record above.

## Golden cases

11 cases in `gc-in-standard-001-*` (see pack). Each states arithmetic in `notes`/`description`; the verifier must re-derive them from the cited Acts. Running twice is deterministic (the suite proves).

## After verification

- `ci/run_backend_tests.sh` full run must be all-pass.
- Do not touch routers, `payroll_engine` service, `rules/loader`, schema, `us-standard-verified.json`, migrations ≤0030, frontend, `docs/DB_SCHEMA.sql`.

