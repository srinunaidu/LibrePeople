# Karmathy contract tree

This directory holds the contracts of the Karmathy platform. A contract is
a written promise: it says what an endpoint does, what it needs and what
it refuses to do. The contracts here are the source of truth for the API
surface, and the code is checked against them.

```
contracts/
├── README.md               <- this file: the guide to the tree
├── errors.md               <- the one error envelope and the one code list
├── rules/                  <- the rule pack contract (another lane)
│   ├── rule-pack.schema.json   <- the JSON Schema of a rule pack
│   └── preset.schema.json      <- the JSON Schema of a rule pack preset
├── events/                 <- the event envelope contract (another lane)
│   ├── jobs.yaml              <- the background job events
│   ├── imports.yaml           <- the import events
│   ├── payroll_runs.yaml      <- the payroll run events
│   └── shifts.yaml            <- the scheduling events
└── openapi/                <- the OpenAPI contract
    ├── _components.yaml    <- shared components: security, errors, schemas
    ├── auth.yaml           <- one fragment per domain
    ├── employees.yaml
    ├── time.yaml
    ├── leave.yaml
    ├── scheduling.yaml
    ├── payroll.yaml
    ├── forecasting.yaml
    ├── imports.yaml
    ├── onboarding.yaml
    ├── admin.yaml
    ├── openapi.yaml        <- generated: the merged document, do not hand edit
    └── _undeclared.md      <- generated: the triage report of the drift check
```

`contracts/rules/` and `contracts/events/` belong to other lanes. This lane
does not create and does not edit them. The rule pack schema is the only
place in the product where statutory values may live, and the event
envelope is the only place where a customer identifier travels between
processes.

---

## 1. The model: fragments, merge, drift

The contract is written in **fragments**, one per domain, and merged into
one document. The merged document is what clients and generators read.

```
contracts/openapi/*.yaml   --merge-->   contracts/openapi/openapi.yaml
       (the source of truth)                    |
                                                |  compare
                                                v
                       the running application's own OpenAPI document
                       GET {app}/api/v1/openapi.json
```

Three rules hold the model together.

1. **The running application is the authority for what the code does
   today.** FastAPI generates its own document and serves it at
   `GET /api/v1/openapi.json`. When the code and this tree disagree about
   the behaviour that exists right now, the generated document wins. The
   code is the fact.
2. **The merged contract is the authority for what the code promises.**
   When they disagree about what a client may rely on, the contract wins.
   The contract is the promise, and a promise that the server does not
   keep is a defect.
3. **Drift in the first direction fails CI; drift in the second direction
   is triaged.** A promised endpoint the application does not serve is a
   hard failure. An endpoint the application serves and the contract does
   not declare is a warning and a work item for the coordinator, never an
   automatic edit of the contract.

### The tools

```bash
# merge the fragments into contracts/openapi/openapi.yaml
.venv/bin/python scripts/merge_openapi.py

# fail when the merged document is out of date (use this in CI)
.venv/bin/python scripts/merge_openapi.py --check

# compare the contract with the running application
.venv/bin/python scripts/check_openapi_drift.py --app https://karmathy-backend.onrender.com

# compare the contract with a specification file or another URL
.venv/bin/python scripts/check_openapi_drift.py --spec ./some-openapi.json
```

`merge_openapi.py` never touches the network and never edits a fragment.
It fails loudly, one line per problem, on a duplicate `operationId`, a
path or method declared twice, a path declared by two fragments, a `$ref`
that does not resolve, an operation without an `operationId`, a tag, a
summary, a description or a response, and an `x-lifecycle` marker that is
neither `released` nor `planned`.

`check_openapi_drift.py` compares the merged contract with the generated
document of the running application and prints:

| finding | meaning | exit |
|---|---|---|
| **HARD FAILURE** | the contract promises the endpoint and the application does not serve it | 1 |
| **CONTRACT AHEAD OF CODE** | the endpoint is declared as `x-lifecycle: planned`, so the promise has not been made yet | 0 |
| **WARNING** | the same route, a different `operationId` or a different spelling of a path parameter | 0 |
| **UNDECLARED ENDPOINTS** | the application serves it, the contract does not declare it | 0 |

The checker never edits the contract. The undeclared endpoints are written
to `contracts/openapi/_undeclared.md` for the coordinator to triage (use
`--no-report` to skip the file, `--report PATH` to write it elsewhere).

### `x-lifecycle`: the promise marker

Every operation in a fragment carries a lifecycle marker, on the operation
or on the path item:

```yaml
paths:
  /payroll/runs/{run_id}/finalise:
    post:
      operationId: payrollFinaliseRun
      x-lifecycle: planned        # declared, not shipped yet
```

| marker | meaning | the drift checker |
|---|---|---|
| `released` (the default) | the contract promises this endpoint to clients | fails when the application does not serve it |
| `planned` | the contract declares the endpoint, the promise has not been made yet | reports it as "contract ahead of code", does not fail |

Promoting an operation from `planned` to `released` is the act of making
the promise, and it is the moment the drift checker starts to hold the
code to it. A lane ships the endpoint first, then flips the marker, in the
same change request.

The comparison is made on the **route**: a path and a method. The name of
a path parameter is not part of the identity of a route
(`/time/timesheets/{sheet_id}` and `/time/timesheets/{timesheet_id}` are
the same route, and the difference is reported as a warning). The shape of
a body is not compared either: a lane that changes the shape of a
response keeps that work in its own backlog, the contract states the
target shape.

---

## 2. Ownership: a lane may not change another lane's contract

Every domain fragment belongs to one lane, and one lane only.

* **A lane may only change its own fragment.** The fragment of another
  lane is changed only with a **written change request to the coordinator
  and to the owning lane**. A pull request that edits another lane's
  fragment without that change request is not merged, no matter how small
  the edit is.
* **Shared components are coordinator territory.** `_components.yaml`
  holds the pieces more than one domain uses: the security scheme, the
  error responses, the pagination, the shared schemas. A lane that needs
  a new shared schema asks the coordinator; a lane that needs a private
  schema keeps it out of `_components.yaml` and declares it in its own
  fragment.
* **`contracts/errors.md` is coordinator territory.** No lane may add a
  code, change the meaning of a code or change the envelope on its own.
* **The generated files are not hand written.** `openapi.yaml` and
  `_undeclared.md` are outputs. A change to a fragment is a change to the
  merged document, never the other way round.

### Adding a new domain fragment

1. Create `contracts/openapi/<domain>.yaml`.
2. Start from the header of an existing fragment: the file is a mapping
   with `paths` and, optionally, `tags`. It is **not** a standalone
   OpenAPI document: no `openapi` key, no `info` key, no `servers` key.
   The merge script adds those.
3. Give every operation:
   * an `operationId` in camelCase, prefixed with the domain and unique
     across **all** fragments (`payrollListRuns`, not `list_runs`);
   * exactly one tag, the tag of the domain;
   * a `summary` and a `description` that say what the endpoint does, what
     it needs and what it refuses to do;
   * the `parameters` of the path and the query, with `required: true` on
     every path parameter;
   * a `requestBody` where a body is needed, with
     `content: application/json: schema: ...` and `required: true` when
     the body is mandatory;
   * the happy path and the error responses that can happen, referring to
     `#/components/responses/...`;
   * `security: [{bearerAuth: []}]`, or `security: []` for an operation
     that is deliberately public.
4. Put the schemas the fragment needs into `_components.yaml` and refer
   to them with `$ref: '#/components/schemas/<Name>'`.
5. Run the merge and the drift check:

```bash
.venv/bin/python scripts/merge_openapi.py
.venv/bin/python scripts/check_openapi_drift.py --app <the deployment>
```

### Adding a new error code

The order is not negotiable:

1. **Add the code to `contracts/errors.md` first.** It belongs in the
   table of its category, with the shape of its `details` and the
   condition that raises it. The file is owned by the coordinator, so the
   change goes through a change request.
2. Only then raise it in the code, from `app/core/errors.py`, using the
   helper of its category (`validation`, `not_found`, `forbidden`,
   `conflict`, `unavailable`, ...).
3. Only then describe it in the fragment of the domain, in the response
   that carries it.

No lane may invent a private error shape, return a bare `detail`, or
return a stack trace. The envelope is the same for every endpoint of the
platform:

```json
{"error": {"code": "...", "category": "...", "message": "...",
           "retryable": false, "details": {}, "request_id": "..."}}
```

---

## 3. The deployment model: one customer per deployment

Karmathy is deployed **once per customer**. One deployment holds exactly
one customer's data in exactly one Oracle schema. There is no shared
database, no shared schema and no cross tenant querying anywhere in the
product.

What that means for the contract:

* **No tenant parameter.** No endpoint in this contract takes a `tenantId`
  path parameter or a tenant filter. A caller of a deployment can only
  ever see the records of that deployment. If you find a tenant parameter
  in a fragment, it is a bug.
* **The schema is the boundary.** The Oracle schema of the deployment is
  what isolates one customer from another. Nothing in the API needs to
  carry a customer identifier, because the connection already points at
  the right schema.
* **Events carry the tenant in the envelope.** An event published by a
  deployment carries `tenant.schema` and `tenant.deployment` in its
  envelope, so a consumer can tell which customer schema and which
  deployment produced it. The envelope is defined in `contracts/events/`,
  which belongs to another lane.
* **The contract is per deployment, but it is written once.** The same
  contract tree describes every deployment. It never describes what one
  deployment can see and another cannot, because a deployment cannot see
  another deployment at all.

---

## 4. Writing rules for a fragment

* **Paths are relative to the API root `/api/v1`.** A fragment writes
  `/employees`, never `/api/v1/employees`.
* **The description is operational.** It says what the endpoint does, what
  it requires and what it refuses to do. For example: *"Refuses to
  calculate unless the jurisdiction has a `verified` rule pack."* A
  description that only repeats the summary is not good enough.
* **Never put real data in the contract.** No names, no addresses, no
  salary figures, no identifiers of real people, no credentials, no
  statutory values. The platform does not ship statutory values: they
  belong to the customer's rule packs.
* **Reference the shared schemas.** A request body uses
  `$ref: '#/components/schemas/<Name>'` whenever a shared schema exists.
  A schema is invented only when nothing fits.
* **Only the codes of `contracts/errors.md` may be named.** If an
  endpoint needs a code that is not in the list, the code is added there
  first.
* **The pagination is uniform.** A collection returns
  `{items: [...], meta: {page, page_size, total, total_pages}}` and takes
  `page` and `page_size` from `#/components/parameters/...`.
* **Mutations a client may retry take an `Idempotency-Key` header**, taken
  from `#/components/parameters/idempotencyKeyHeader`.
