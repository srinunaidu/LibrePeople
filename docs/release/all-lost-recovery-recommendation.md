# All-Lost Recovery Recommendation — HEAD cf25fee (`feature/librepeople-production`)

> Status: RECOMMENDATIONS ONLY. No approval claimed. No implementation. Owner decision pending per `decision-register.md` (all-lost: OPEN).

## 1. Scenarios

1. Total credential loss (all admins locked out, MFA devices gone).
2. Platform loss (DB + secrets + backups online-copy destroyed).
3. Malicious lockout (rogue admin rotates credentials/secrets).

## 2. Recommended mechanism (offline, two-person, time-boxed)

- Sealed offline kit: paper/QR split of root-break-glass secret (2-of-2 halves, two custodians), stored in two locations; no digital copy.
- Recovery requires both custodians present, opens a 2-hour window only, single-use token, auto-expiry, max 1 active window.
- Re-seal mandatory after any use; rehearsal quarterly on staging, never production data.

## 3. Auth / verification

- Identity check: government ID + live owner confirmation call; deny on single-custodian request.
- Technical: split-secret reconstruct offline, hardware-key-bound new admin, old sessions/secrets revoked on success.

## 4. Audit evidence

- Tamper-evident log: who, when, window ID, reason ticket, success/failure; export to closure evidence index; failed attempts alert owner.

## 5. Abuse tests

1. One custodian alone requests access — must fail. 2. Expired window replay — must fail. 3. Reused token — must fail. 4. Post-recovery old-session reuse — must fail.

## 6. Owner questions

1. Accept 2-of-2 custodians + 2-hour window? 2. Who are custodians/locations? 3. Quarterly rehearsal cadence OK? 4. Accept production never used for rehearsal? 5. Approve mandatory re-seal + revocation rule?

## 7. Tier 1 irreversible note

Root-secret compromise or misuse is Tier 1 irreversible: leaked halves cannot be un-seen; rotation + re-seal + full audit required after any suspected exposure.
