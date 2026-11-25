"""Schemas for the background-jobs monitor (PS-10).

Mirrors `contracts/openapi/admin.yaml` (paths `/admin/jobs*`) and the
shared `Job` / `PaginatedJobs` components in
`contracts/openapi/_components.yaml`.

Vocabulary note: the contract's `JobStatus` calls the queued state
`pending` (`pending | running | succeeded | failed | dead | cancelled |
discarded`); the `job_queue` table stores `queued`
(`models/job_queue.py`, migration `0004_job_queue`). The translation
happens in `app.services.job_admin`, never in the schema, so these
models carry the contract vocabulary as-is.

`payload` and `result` are declared optional in the contract. The queue
persists input/result *hashes*, not payloads, so both are `null` today;
`include_payload=true` includes the fields rather than leaving them out,
so a client that asks for them knows the answer is "not stored" rather
than "not sent".
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from app.schemas.pagination import PageMeta


class JobOut(BaseModel):
    """One background job, in the contract's `Job` shape."""

    id: str
    type: str
    state: str
    attempts: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    last_error_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    payload: dict | None = None
    result: dict | None = None


class PaginatedJobs(BaseModel):
    """A page of background jobs, newest first, in the contract's envelope.

    Dead rows are part of the page: a dead job is never silently
    discarded, so neither the default listing nor any state filter
    hides it. The counts live under `meta`, which is what
    `PaginatedJobs` in the contract declares; flat fields were a
    second, smaller contract drift (`D-044`).
    """

    items: list[JobOut]
    meta: PageMeta
