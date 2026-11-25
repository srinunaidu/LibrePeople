# Field encryption key rotation (LibrePeople)

Field encryption is mandatory for the India payroll fields (Aadhaar, IFSC,
bank account, PAN verification state, beneficiary name) and for TOTP secrets
and recovery codes. New writes are always encrypted with the key named by
`FIELD_ENCRYPTION_ACTIVE_KEY_ID`; every key in `FIELD_ENCRYPTION_KEYS` can
decrypt, which is what makes rotation possible **without a data migration**:
no stored value has to be rewritten when a key is added or removed.

There is **no fallback to `SECRET_KEY` in any environment** — production
refuses to start without `FIELD_ENCRYPTION_KEYS` and
`FIELD_ENCRYPTION_ACTIVE_KEY_ID`, and encryption without a registered key
raises instead of writing a secret in the clear.

## Prerequisites

- `FIELD_ENCRYPTION_KEYS` contains the old key **and** the new key while the
  rotation is in progress: `key_id_old:<secret_old>,key_id_new:<secret_new>`.
- A backup of the database exists, and a re-encryption plan exists if any
  rows were encrypted under keys that will be retired. Values encrypted
  under a key removed from the registry can no longer be decrypted, so
  retirement is the destructive step.

## Steps

1. **Add the new key to the registry and make it active.** Set
   `FIELD_ENCRYPTION_KEYS` to include both keys and set
   `FIELD_ENCRYPTION_ACTIVE_KEY_ID` to the new key. Deploy.
   - New values are written under the new key id (`ENCv1:<new_id>:<token>`).
   - Existing values remain readable: decryption accepts every registered
     key, so values still under the old key id decrypt with the old key.
2. **Verify.** Check that writes carry the new key id — read a freshly
   encrypted value through the API or via `app.core.security.encrypt_secret`
   and confirm the envelope names `FIELD_ENCRYPTION_ACTIVE_KEY_ID`.
3. **Wait.** Keep the old key registered until values encrypted under it
   are either re-encrypted under the new key or no longer needed (see
   "Re-encryption" below).
4. **Retire the old key.** Remove `key_id_old` from `FIELD_ENCRYPTION_KEYS`
   (leaving `FIELD_ENCRYPTION_ACTIVE_KEY_ID` as-is) and deploy.
   - Values encrypted under `key_id_old` are now unreadable; that is the
     intended semantics of retiring a key. If they are still needed,
     re-encrypt them before this step.
5. **Confirm.** `app.core.security.field_encryption_status()` reports the
   configured, rotatable state; it returns `configured: true` only when the
   active key id is in the registry.

## Re-encryption (optional)

Re-encryption moves existing values from an old key id to the active one.
It is a deliberate, operator-driven step:

```python
from app.core.security import decrypt_secret, encrypt_secret
new = encrypt_secret(decrypt_secret(old_value))
```

Apply it row by row against the models that carry encrypted fields (the
Employee payroll/India fields, TOTP secrets, recovery codes). Do not run any
bulk re-encryption as part of the rotation itself — step 1 already switches
the write path.

## Operational notes

- A deployment without `FIELD_ENCRYPTION_KEYS` in **production** will not
  start (`app.core.config.Settings.validate` raises `RuntimeError`).
- `DOCUMENT_URL`-style stored values are unrelated to this key registry.
- The verification script
  `backend/scripts/verify_files_urls.py` (item 9) reports nothing about
  encryption; encryption status is visible through `/health/wallet` plus
  `field_encryption_status()`.
