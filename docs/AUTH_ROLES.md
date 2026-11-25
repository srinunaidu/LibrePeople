# Karmathy — Auth & Roles (RBAC)

JWT bearer auth. Token payload: `{ "sub": <username>, "exp": <utc> }`.
Signed with `HS256` using `SECRET_KEY`. Lifetime: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30).

## Roles

| Role | Purpose |
|------|---------|
| `SuperAdmin` | Full access, user management, config |
| `HR` | Hiring, onboarding, employee records |
| `Manager` | Team views, approvals (future modules) |
| `Associate` | Self-service only (future modules) |
| `PayrollViewer` | Read-only payroll/compensation views |

## Enforcement (current)

- `get_current_user` — validates JWT, loads `User` (403 on invalid).
- `get_current_active_user` — additionally requires `is_active` (400 if disabled).
- `get_current_admin_user` — requires role in `{SuperAdmin, HR}` (403 otherwise).

## Endpoint classes

- **Public**: `/health`, `/api/v1/auth/login`, `/api/v1/auth/register`
- **Authenticated (any role)**: all `GET` list/detail endpoints, onboarding summary/tasks/documents reads
- **Admin (SuperAdmin or HR)**: all writes — create/update employees, departments, jobs,
  requisitions, candidates, applications, offers, offer letter generation, hiring, onboarding writes

## Extending

Module-specific guards (e.g. Manager approvals, PayrollViewer for payroll) are added as
new dependency functions in `app/api/deps.py` following the same pattern:

```python
def get_current_payroll_viewer(user = Depends(get_current_active_user)):
    if user.role not in ("SuperAdmin", "PayrollViewer"):
        raise HTTPException(403, "Not enough permissions")
    return user
```
