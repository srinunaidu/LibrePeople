# Import templates — the CSV contract

**Owner:** Data & Import · **Applies to:** every CSV the importer accepts.

This document is the operator-facing half of the import contract. The
machine-readable half is `backend/app/imports/spec.py`, and the two are
checked against each other by `backend/import_test_suite.py`: a column that
appears in one and not the other fails the suite.

---

## How an import works

An import is two steps, and the second cannot happen without the first.

1. **Dry run.** `POST /api/v1/import-export/import/{entity}?dry_run=true`
   validates the whole file and writes nothing to the entity's table. The
   response carries the counts, the row-level results, and a
   **confirmation token**.
2. **Commit.** `POST /api/v1/import-export/import/{entity}/commit` with that
   token applies the file.

The token is not a promise the client makes. It is bound to a hash of the
dry-run *outcome*, and the commit re-reads the uploaded file and re-validates
it. If the outcome has changed — because the database changed underneath the
operator, or because the file was altered in storage — the commit is refused
with `409 import_result_changed` and the operator is told to run the dry run
again.

A token is good for **15 minutes** and may be used **once**. The uploaded
file is deleted when the import is committed, or after **7 days** if it is
never committed.

There is also a one-shot form, `POST /api/v1/import-export/import/{entity}`
without `dry_run`. It runs the dry run and the commit back to back. It is not
a shortcut around validation: the validation still runs, and only the rows
that passed are applied.

---

## The rules every file follows

| Rule | What it means |
|---|---|
| **Encoding** | UTF-8. A byte-order mark is accepted and ignored. A file that is not valid UTF-8 is refused. |
| **Format** | RFC 4180: comma-separated, `CRLF` or `LF` line endings, double-quoted fields, doubled quotes inside a quoted field, newlines allowed inside a quoted field. |
| **Header** | The first record is the header. Every header must match a column of the entity, exactly or through a documented alias. An unknown header is refused with `422` and the refusal names it and lists every accepted header. There is no fuzzy matching. |
| **Size** | 5 MB maximum. |
| **Rows** | 10,000 data rows maximum. The header is not a row. |
| **Dates** | ISO 8601 only: `YYYY-MM-DD` for a date, `YYYY-MM-DDTHH:MM:SS` for a date-time, `HH:MM` for a time. `31/12/2026` is refused — it means different things on different sides of the Atlantic. |
| **Numbers** | A plain decimal. A thousands separator is refused. |
| **Booleans** | `true`, `false`, `yes`, `no`, `1`, `0`, `y`, `n`, `t`, `f`, `on`, `off`. The comparison ignores case. |
| **Enums** | Only the values listed for the column. The comparison ignores case and the value is stored in the canonical spelling. |
| **References** | A reference is named by the key a human recognises (`job_code`), not by a database id. The importer resolves it and refuses the row with `reference_not_found` if it cannot. |
| **Required columns** | A required column, or one of its alternatives, must be present and non-blank. A row that is missing one is refused with `missing_required`. |
| **Formula injection** | A value whose first character is `=`, `+`, `-`, `@`, tab or carriage return is prefixed with a single quote so a spreadsheet treats it as text. The one exception: a value that is a number (`-1000`) is a number, not a formula, and is left alone. |
| **Upsert** | The import matches on the entity's **natural key**. A key that is not there is created, a key that is there with the same values is left alone, and a key that is there with different values is updated. **A second import of the same file creates nothing and reports every row as `unchanged`.** |
| **Absent columns** | A column that is absent from the file, or present but blank, is left as it is. An import never clears a value it was not given. |
| **Personal data** | A personal value is never echoed back. An error names the row and the column and the rule that was broken, and never quotes the data. |

---

## The counts

| Count | Meaning |
|---|---|
| `create` | The row would be created. |
| `update` | The row's natural key exists and the values differ. |
| `unchanged` | The row's natural key exists and the values are the same. |
| `reject` | The row is refused. Every rejected row carries its reasons. |
| `total_rows` | The data rows in the file, rejected ones included. |

A rejected row is never written. The commit writes exactly the rows the
preview showed.

---

## The entities

The six entities below are the ones the golden files cover. The others —
`cost_centers`, `candidates`, `leave_types`, `benefit_plans`, `courses`,
`compliance_rules`, `pay_components` — work the same way; their columns are
in `GET /api/v1/import-export/columns/{entity}`.

### `departments`

| Column | Type | Required | Notes |
|---|---|---|---|
| `name` | text | yes | Display name. |
| `code` | code | yes | Unique. **The natural key.** |
| `description` | text | no | |
| `is_active` | boolean | no | Defaults to true. |

```csv
name,code,description,is_active
Alpha,ALPHA,First department,true
```

### `locations`

| Column | Type | Required | Notes |
|---|---|---|---|
| `name` | text | yes | Display name. |
| `code` | code | yes | Unique. **The natural key.** |
| `address` | text | no | |
| `city` | text | no | |
| `country` | text | no | |
| `timezone` | text | no | IANA name, e.g. `Europe/London`. |
| `is_active` | boolean | no | Defaults to true. |

```csv
name,code,city,country,timezone,is_active
Head Office,HQ-LON,London,GB,Europe/London,true
```

### `jobs`

| Column | Type | Required | Notes |
|---|---|---|---|
| `title` | text | yes | |
| `code` | code | yes | Unique. **The natural key.** |
| `department_id` | integer | yes* | The department's id. |
| `department_code` | code | yes* | The department's code. Resolved to the id. |
| `min_salary` | decimal | no | Per pay period. |
| `max_salary` | decimal | no | Per pay period. Must not be below `min_salary`. |
| `is_active` | boolean | no | Defaults to true. |

\* One of `department_id` and `department_code` must be present.

> **The salary unit is per pay period.** `base_salary` is the amount paid
> for one pay period, not an annual figure. This is the owner-confirmed
> decision recorded in `agents/DECISIONS.md` and the audit finding A2-16.
> A file that states an annual figure in a per-period column is a mistake
> the importer cannot detect; it is also a mistake that costs real money.

### `employees`

| Column | Type | Required | Notes |
|---|---|---|---|
| `employee_id` | code | yes | The employee number, e.g. `EMP-0001`. Unique. **The natural key.** |
| `first_name` | text | yes | |
| `last_name` | text | yes | |
| `email` | email | yes | Unique. |
| `phone` | text | no | |
| `hire_date` | date | yes | ISO 8601. |
| `job_id` | integer | yes* | The job's id. |
| `job_code` | code | yes* | The job's code. Resolved to the id. |
| `department_id` | integer | yes* | The department's id. |
| `department_code` | code | yes* | The department's code. Resolved to the id. |
| `manager_id` | integer | no* | The manager's id. |
| `manager_employee_id` | code | no* | The manager's employee number. Resolved to the id. |
| `status` | text | no | `Active`, `On Leave`, `Terminated`, `Rehired`. |
| `salary` | decimal | no | Per pay period. See the note on `jobs`. |

\* One of each pair must be present, except for the manager, where neither
is required.

```csv
employee_id,first_name,last_name,email,hire_date,job_code,department_code,status,salary
EMP-0001,Ada,Lovelace,ada@example.com,2026-01-15,J-ENG,ALPHA,Active,7500
```

### `leave_balances`

| Column | Type | Required | Notes |
|---|---|---|---|
| `employee_number` | code | yes* | The employee's number. Resolved to the id. |
| `employee_id` | integer | yes* | The employee's id. |
| `leave_type_code` | code | yes* | The leave type's code, e.g. `ANN`. Resolved to the id. |
| `leave_type_id` | integer | yes* | The leave type's id. |
| `entitlement_year` | integer | yes | The calendar year. |
| `entitled_days` | decimal | no | |
| `carried_over_days` | decimal | no | |
| `used_days` | decimal | no | |

\* One of `employee_number` and `employee_id`, and one of `leave_type_code`
and `leave_type_id`, must be present.

The natural key is the triple *(employee, leave type, year)*.

#### Leave balances are written through the leave ledger

A leave balance is not three numbers on a row: it is the sum of a signed
**leave ledger**, and the three columns above are a cache of that sum. An
imported leave balance is therefore written as ledger rows — an
`entitlement` row for the days entitled, a `carry_over` row for the days
brought forward and a `usage` row for the days taken — and the cache is
refreshed from them by the ledger itself. The import never writes the three
columns directly.

Two things follow, and the importer refuses both of them:

* **A balance of zero days is refused** with `ledger_no_movement`. A balance
  with no ledger row behind it is a balance the reconciliation cannot see,
  so it is not imported.
* **A file that lowers a balance is refused** with
  `ledger_reduction_refused`, and the error names the column it refused.
  The ledger records days coming to a balance; it does not take them off.
  A correction that lowers an entitlement, a carry-over or the usage is
  made through the leave ledger, not through an import.

A file that states what the ledger already says writes nothing: the second
import of the same file is reported as `unchanged`, and the ledger does not
grow.

The numbers in the file are the **tenant's own policy**. The importer never
supplies an entitlement of its own, and none is written into a file, a
template or a test.

### `shift_templates`

| Column | Type | Required | Notes |
|---|---|---|---|
| `name` | text | yes | |
| `code` | code | yes | Unique. **The natural key.** |
| `start_time` | time | yes | 24-hour `HH:MM`. |
| `end_time` | time | yes | 24-hour `HH:MM`. |
| `break_minutes` | integer | no | |
| `is_night` | boolean | no | |
| `is_active` | boolean | no | Defaults to true. |

```csv
name,code,start_time,end_time,break_minutes,is_night,is_active
Day 09-17,SH-DAY,09:00,17:00,30,false,true
```

---

## The alias table

A header may be written in an alternative spelling. The alias is recorded in
the dry-run response under `aliases_used`, so the operator can see what the
file was understood to mean.

| Canonical | Also accepted |
|---|---|
| `id` | `identifier`, `uid` |
| `name` | `full_name`, `department_name`, `location_name` |
| `code` | `department_code`, `job_code`, `location_code`, `leave_type_code`, `benefit_plan_code`, `course_code`, `compliance_rule_code`, `shift_template_code`, `pay_component_code`, `cost_center_code` |
| `title` | `job_title`, `position_title`, `course_title` |
| `description` | `desc`, `details` |
| `is_active` | `active` |
| `employee_id` | `employee_code`, `emp_id`, `staff_id`, `personnel_number` |
| `employee_number` | `employee_no`, `employee_code`, `emp_id`, `staff_id`, `personnel_number` |
| `first_name` | `firstname`, `given_name` |
| `last_name` | `lastname`, `surname`, `family_name` |
| `email` | `email_address`, `work_email` |
| `phone` | `phone_number`, `telephone`, `mobile` |
| `hire_date` | `date_of_hire` |
| `job_id` | `job_code` |
| `job_code` | `job_code_id`, `position_code` |
| `department_id` | `department_code`, `dept_code` |
| `manager_id` | `manager_code`, `reports_to` |
| `manager_employee_id` | `manager_employee_number`, `manager_code` |
| `status` | `employment_status` |
| `salary` | `base_salary` |
| `min_salary` | `minimum_salary` |
| `max_salary` | `maximum_salary` |
| `leave_type_id` | `leave_type_code` |
| `leave_type_code` | `leave_type` |
| `max_days_per_year` | `annual_allowance`, `entitlement_days` |
| `is_paid` | `paid` |
| `plan_type` | `type` |
| `provider` | `insurer` |
| `employer_contribution` | `employer_contrib` |
| `employee_contribution` | `employee_contrib` |
| `course_id` | `course_code` |
| `plan_id` | `benefit_plan_code` |
| `rule_id` | `compliance_rule_code` |
| `position_id` | `position_code` |
| `category` | `cat` |
| `duration_hours` | `duration`, `hours` |
| `is_mandatory` | `mandatory` |
| `break_minutes` | `break_duration`, `break_length` |
| `fte` | `full_time_equivalent` |
| `start_time` | `shift_start` |
| `end_time` | `shift_end` |
| `is_night` | `night_shift` |
| `entitlement_year` | `year` |
| `entitled_days` | `entitlement`, `days_entitled` |
| `carried_over_days` | `carry_over_days`, `carried_over` |
| `used_days` | `days_used` |
| `address` | `street_address` |
| `city` | `town` |
| `country` | `country_code` |
| `timezone` | `time_zone`, `tz` |
| `source` | `recruitment_source` |
| `severity` | `risk_level` |
| `component_type` | `pay_component_type` |
| `is_taxable` | `taxable` |
| `is_pre_tax` | `pre_tax` |

---

## The error codes

Every refused row carries one or more of these. They are stable identifiers:
branch on them, do not parse the message.

| Code | What it means |
|---|---|
| `missing_required` | A required column, or one of its alternatives, is absent or blank. |
| `invalid_integer` | The value is not a whole number. |
| `invalid_number` | The value is not a number. |
| `invalid_boolean` | The value is not a true/false value. |
| `invalid_date` | The value is not an ISO 8601 date. |
| `invalid_datetime` | The value is not an ISO 8601 date-time. |
| `invalid_time` | The value is not a 24-hour `HH:MM` time. |
| `invalid_email` | The value is not an email address. |
| `invalid_enum` | The value is not one of the column's allowed values. |
| `too_long` | The value is longer than the column allows. |
| `below_minimum` | The number is below the configured lower bound. |
| `above_maximum` | The number is above the configured upper bound. |
| `inconsistent_values` | Two columns of the row disagree. |
| `reference_not_found` | The row names a record that does not exist. |
| `duplicate_in_file` | An earlier row in the same file has the same natural key. |
| `duplicate_exists` | Another record already holds a value this column must be unique on. |
| `too_many_fields` | The row has more values than the header declares. |
| `too_few_fields` | The row has fewer values than the header declares. |
| `write_failed` | The row could not be written. The detail is in the server log. |
| `ledger_no_movement` | The row would leave a leave balance with no ledger row behind it. |
| `ledger_reduction_refused` | The row would lower a leave balance, and the leave ledger cannot record that. |

File-level codes, which refuse the whole file:

| Code | What it means |
|---|---|
| `unknown_headers` | The header row contains a header the entity does not accept. |
| `too_many_rows` | The file has more than the row limit. |
| `file_too_large` | The file is larger than the size limit. |
| `not_utf8` | The file is not valid UTF-8. |
| `malformed_csv` | The file is not valid RFC 4180 CSV. |
| `empty_file` | The file has no content. |
| `no_header` | The file has no header row. |

---

## The limits and where they are set

| Setting | Default | Meaning |
|---|---|---|
| `IMPORT_MAX_UPLOAD_BYTES` | 5 MB | The largest upload. |
| `IMPORT_MAX_ROWS` | 10,000 | The largest number of data rows. |
| `IMPORT_BATCH_SIZE` | 500 | The rows held in memory at once. |
| `IMPORT_TOKEN_TTL_MINUTES` | 15 | How long a confirmation token is usable. |
| `IMPORT_MAX_OUTSTANDING_TOKENS` | 100 | How many uncommitted dry runs may exist at once. |
| `UPLOAD_RETENTION_DAYS` | 7 | How long an uncommitted upload is kept. |
| `TENANT_ID` | `default` | Which customer this deployment serves. |
| `IMPORT_SALARY_MIN` | unset | The tenant's lower bound on an imported salary. |
| `IMPORT_SALARY_MAX` | unset | The tenant's upper bound on an imported salary. |
| `IMPORT_JOB_ROW_THRESHOLD` | 2,000 | How many rows a file may hold before its import runs as a background job. |
| `IMPORT_JOB_TTL_MINUTES` | 60 | How long the token of a queued import stays usable. |

They are environment variables. They are read from `app/imports/config.py`,
which is this lane's own configuration module.

---

## Large files run as a job

An import of more than `IMPORT_JOB_ROW_THRESHOLD` rows is not applied inside
the request. The commit returns **202** with the job instead of the counts:

```json
{
  "entity": "departments",
  "total_rows": 5400,
  "create": 5400,
  "update": 0,
  "unchanged": 0,
  "reject": 0,
  "committed": false,
  "state": "queued",
  "job": {"id": 17, "type": "csv_import", "state": "queued"}
}
```

The job applies **the import the operator previewed** — the same record, the
same token — so there is one import with one status, and the job's status is
the import's status. The job:

* applies the file in **one transaction**, so the file is applied entirely or
  not at all;
* reports its **progress** after every batch;
* **stops** when the import is cancelled or when the job loses its lease, and
  the transaction is rolled back with it, so a cancelled job leaves nothing
  behind;
* returns the **same report the dry run produced**, with the rows that could
  not be written named in it.

A token that has been queued stays usable for `IMPORT_JOB_TTL_MINUTES`,
because a job waits in a queue. It is still bound to the outcome it was
issued for, and it may still be used once.

---

## Getting the templates

```
GET /api/v1/import-export/template/{entity}
```

Returns the header row and one example row. The example row is generated
from the contract, so it always satisfies the contract's own rules.

```
GET /api/v1/import-export/columns/{entity}
```

Returns the contract itself as JSON: every column, its type, whether it is
required, its allowed values, what it points at, and whether it holds
personal data.

---

## The row-error CSV

```
GET /api/v1/import-export/import/{entity}/row-errors?confirmation_token=...
```

Returns a CSV with one row per error: the record number, the column, the
error code, and the reason. It contains no personal value, because the
validator never puts one in a message.

The record number is the number of the record in the file, with the header as
record 1, so the first data row is record 2. It matches the line number in a
spreadsheet unless the file contains a newline inside a quoted field, in
which case the physical lines shift and the record numbers do not.
