# Bootstrap rotation remediation

## Scope

Git history contains old retail bootstrap passwords (seeded demo/retail accounts). Production databases seeded before rotation may still hold those accounts with known passwords. Treat all prior bootstrap values as compromised.

## Steps

1. **Rotate `ADMIN_INITIAL_PASSWORD` on Render.** Dashboard → Service → Environment: set value via Generate random value (do not paste a memorable password). Redeploy.
2. **Force rotation at first login.** Confirm bootstrap-created admin has `must_change_password=true`; do not clear it manually — login flow must force a change.
3. **Revoke sessions.** Log out all sessions / invalidate tokens issued before rotation (restart service if no session table exists).
4. **Disable/delete retail seeded accounts.** In prod DB, disable or delete any accounts created by retail seed scripts; keep only the real admin(s). Confirm no enabled account uses a historical bootstrap password.
5. **Clear `__pycache__`.** Delete stale bytecode on deploy hosts (`find . -name __pycache__ -type d -prune -exec rm -rf {} +`) so no cached bootstrap logic survives.
6. **Verify fail-closed startup.** Restart service with `ADMIN_INITIAL_PASSWORD` unset — startup must refuse to create a bootstrap admin (fail closed, no default password).

## Verification

```bash
git log -p --all -S 'ADMIN_INITIAL_PASSWORD' -- . | grep -E '^\+.*(password|secret)' || true
grep -rn --exclude-dir=.git --exclude-dir=.venv311 -iE 'retail.*password|ADMIN_INITIAL_PASSWORD\s*=' . | grep -v docs/runbooks/bootstrap-rotation-remediation.md
# DB: list enabled users; expect only real admins, all with must_change_password resolved post-login
```

No secret values are recorded in this runbook by design.
