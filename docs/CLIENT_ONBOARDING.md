# Karmathy — Client Onboarding Portal

This guide is for **new customers** setting up a Karmathy tenant, and for
**administrators** configuring integrations and migrating data in.

## 1. Access

- Portal UI: `/onboarding-portal` (admin only)
- API base: `/api/v1/onboarding-portal`

## 2. Onboarding flow (6 steps)

1. **Company profile** — name, slug, industry, country, timezone, locale, branding (primary/secondary color, logo).
2. **Feature flags** — enable only the modules you need (Recruiting, Time & Attendance, Scheduling, Leave, Offboarding, Reports, and sub-features).
3. **Integrations** — connect source systems (Oracle ADB, REST, SFTP, CSV, webhook).
4. **Import data** — migrate employees, departments, jobs, candidates, leave balances.
5. **Users & roles** — create HR, managers and associates.
6. **Review & go live** — activate the tenant.

Each step can be completed in any order; progress is tracked per client.

## 3. Migration API connection

### 3.1 Authentication

All endpoints require a JWT:

```
POST /api/v1/auth/login
{ "username": "<admin>", "password": "<password>" }
-> { "access_token": "<jwt>", "token_type": "bearer", "role": "SuperAdmin" }
```

Use `Authorization: Bearer <jwt>` on every subsequent request.

### 3.2 Creating a client (tenant)

```
POST /api/v1/onboarding-portal/clients
{
  "name": "Acme Corp",
  "slug": "acme",
  "industry": "Manufacturing",
  "country": "India",
  "timezone": "Asia/Kolkata",
  "locale": "en",
  "primary_color": "#1E40AF",
  "contact_name": "Jane Doe",
  "contact_email": "jane@acme.com"
}
```

The response includes a default set of feature flags and onboarding steps.

### 3.3 Creating an integration

```
POST /api/v1/onboarding-portal/clients/{client_id}/integrations
{
  "name": "HR Source DB",
  "kind": "oracle_adb",          // oracle_adb | rest | sftp | csv | webhook
  "endpoint": "adb.ap-hyderabad-1.oraclecloud.com:1522/gb..._high.adb.oraclecloud.com",
  "username": "admin",
  "secret": "<password>",        // stored encrypted at rest
  "notes": "Production HR database"
}
```

Supported kinds:

| kind | Required fields | Notes |
|------|-----------------|-------|
| `oracle_adb` | endpoint, username, secret | TNS alias or EZConnect string; secret is the DB password |
| `rest` | endpoint, username, secret | REST endpoint + bearer/basic credentials |
| `sftp` | endpoint, username, secret | Host:port + credentials |
| `csv` | (none) | Upload CSV via the migration runner |
| `webhook` | endpoint | Outbound webhook for events |

Test the connection:

```
POST /api/v1/onboarding-portal/clients/{client_id}/integrations/{id}/test
```

### 3.4 Running a migration

```
POST /api/v1/onboarding-portal/clients/{client_id}/migrations
{ "integration_id": 1, "entity": "employees", "total": 500 }

POST /api/v1/onboarding-portal/clients/{client_id}/migrations/{job_id}/run
```

Entities: `employees`, `departments`, `jobs`, `candidates`, `leave_balances`.

Poll status:

```
GET /api/v1/onboarding-portal/clients/{client_id}/migrations
```

Each job reports `total`, `processed`, `succeeded`, `failed`, `error_log`, `status`.

### 3.5 Customization (maximum flexibility)

Arbitrary key/value settings per client:

```
PUT /api/v1/onboarding-portal/clients/{client_id}/settings/{key}
{ "key": "payroll.cycle_day", "value": "15" }
```

Common keys: `payroll.cycle_day`, `leave.year_start_month`, `attendance.overtime_threshold`,
`notifications.email_from`, `branding.favicon_url`, `modules.default_landing_page`.

### 3.6 Feature flags

```
GET  /api/v1/onboarding-portal/clients/{client_id}/feature-flags
PUT  /api/v1/onboarding-portal/clients/{client_id}/feature-flags/{key}
     { "enabled": true, "config": "{\"max_upload_mb\": 10}" }
```

## 4. Admin portal capabilities

- Create / update / delete clients (tenants)
- Toggle feature flags per client
- Manage integrations (create, test, delete)
- Run and monitor migration jobs
- Assign onboarding steps and track completion
- Configure arbitrary settings (key/value)
- Branding: primary/secondary color, logo URL, timezone, locale

## 5. Security notes

- Integration secrets are encrypted at rest with a key derived from `SECRET_KEY`.
- Never commit `~/.render/api_key`, `~/.karmathy/adb_password` or wallet files.
- Use least-privilege DB users for migration sources.
- Rotate integration secrets periodically via the update endpoint.

## 6. Oracle Autonomous Database migration source

When migrating from an Oracle ADB source:

1. Create an integration with `kind: oracle_adb`.
2. Set `endpoint` to the TNS alias host (e.g. `adb.ap-hyderabad-1.oraclecloud.com:1522/<service>`).
3. Set `username` / `secret` (DB user + password).
4. Ensure the source DB allows connections from the Karmathy backend (mTLS or IP allow-list).
5. Run a migration job per entity.

For bulk file-based migration, use `kind: csv` and upload CSVs through the migration runner.
