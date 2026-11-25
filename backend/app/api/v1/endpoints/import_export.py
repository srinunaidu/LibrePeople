"""CSV import and export.

The shape of an import
----------------------
An import is two steps, and the second one cannot happen without the first:

1. **Dry run.** The file is validated in full and nothing is written to the
   entity's table. The operator gets the counts — create, update, unchanged,
   reject — the row-level results, and a *confirmation token*.
2. **Commit.** The token is presented. The server re-reads the uploaded
   file, re-validates it, checks that the outcome is the one the operator
   was shown, and applies every row in **one transaction**.

The token is not a promise the client makes. It is bound to the hash of the
dry-run outcome, so a token cannot be reused for a different file or for a
file whose validation has since changed.

A one-shot import (``dry_run=false``) is available and does both steps
back to back. It is not a shortcut around validation: the validation still
runs, and only the rows that passed are applied.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.api.deps import get_current_admin_user, get_db
from app.core.errors import ApiError, ErrorCategory
from app.core.tenancy import tenant_column_criterion, tenant_id_for
from app.imports import progress, runner
from app.imports.config import settings
from app.imports.errors import ImportFileError
from app.imports.parser import read_all_limited
from app.imports.spec import ENTITIES, get_spec
from app.imports.templates import build_template
from app.models.user import User

router = APIRouter()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _entity_or_404(entity: str) -> None:
    if entity not in ENTITIES:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")


def _read_upload(file: UploadFile) -> bytes:
    """Read the uploaded file, refusing it if it is too large."""
    try:
        return read_all_limited(file.file, settings.IMPORT_MAX_UPLOAD_BYTES)
    except ImportFileError as exc:
        status_code = (
            413 if exc.code == "file_too_large" else 422
        )
        raise ApiError(
            exc.code,
            exc.message,
            ErrorCategory.VALIDATION,
            status_code=status_code,
            details=exc.details or None,
        ) from None


def _export_columns(entity: str, db=None) -> list[str]:
    """The model attributes the export writes, in order.

    For employees, the tenant's active custom definitions are appended as
    ``custom.<key>`` columns (LP-CORE-005), so an export carries the same
    vocabulary the importer accepts and round-trips without editing.
    """
    spec = get_spec(entity)
    columns = ["id"]
    for column in spec.columns:
        if column.name == "id":
            continue
        target = column.writes_to
        if target not in columns:
            columns.append(target)
    if entity == "employees" and db is not None:
        from app.services import custom_fields as custom_field_service

        for key in sorted(custom_field_service.def_map(db)):
            columns.append(f"custom.{key}")
    return columns


def _summary(result, **extra: Any) -> dict[str, Any]:
    payload = result.summary()
    payload.update(extra)
    return payload


def _counts(record) -> dict[str, Any]:
    """The counts of a dry run, as the dry run reported them."""
    create = record.create_count or 0
    update = record.update_count or 0
    unchanged = record.unchanged_count or 0
    reject = record.reject_count or 0
    return {
        "entity": record.entity,
        "total_rows": record.total_rows or 0,
        "create": create,
        "update": update,
        "unchanged": unchanged,
        "reject": reject,
        "accepted": create + update + unchanged,
        "created": create,
        "updated": update,
        "rejected": reject,
        "skipped": 0,
    }


def _queued(record, job) -> JSONResponse:
    """The response for an import that will be applied in the background.

    A large file is applied by a job rather than inside the request, so
    the request is not held open for the length of the import. The job's
    status is the import's status, and the counts are the ones the
    operator was shown.
    """
    return JSONResponse(
        status_code=202,
        content={
            **_counts(record),
            "committed": False,
            "state": "queued",
            "job": {
                "id": job.id,
                "type": job.job_type,
                "state": job.state,
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
            },
            "note": (
                "The file is large, so the import is running as a "
                "background job. The job's status is the import's status."
            ),
        },
    )


def _reject_structurally_broken(result) -> None:
    """Refuse a file whose header row cannot be understood.

    A file with an unknown header, or one that is missing a required
    column, is not a file with some bad rows in it — it is the wrong file.
    It is refused with 422, and the error carries the full list of headers
    the entity accepts so the operator can fix it without guessing.
    """
    if not result.file_errors:
        return
    error = result.file_errors[0]
    details: dict[str, Any] = {
        "unknown_headers": result.headers.unknown,
        "accepted_headers": result.headers.accepted,
        "missing_columns": result.missing_columns,
    }
    raise ApiError(
        error.code,
        error.message,
        ErrorCategory.VALIDATION,
        status_code=422,
        details=details,
    )


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------


@router.get("/export/{entity}", operation_id="importsExportEntity")
def export_csv(
    entity: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Export an entity as CSV.

    The columns are the ones the import accepts, so an export can be
    edited and imported back without changing a single header.
    """
    _entity_or_404(entity)
    spec = get_spec(entity)
    columns = _export_columns(entity, db)
    query = db.query(spec.model)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and hasattr(spec.model, "tenant_id"):
        query = query.filter(tenant_column_criterion(spec.model.tenant_id, tenant_id))
    rows = query.all()

    # Configurable attributes (LP-CORE-005): the export runs as HR or
    # SuperAdmin, the roles that see every value, so no masking applies.
    custom_values: dict[int, dict[str, str]] = {}
    if entity == "employees":
        from app.services import custom_fields as custom_field_service

        custom_values = custom_field_service.read_values(
            db, [row.id for row in rows]
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        record = []
        for column in columns:
            if column.startswith("custom."):
                record.append(
                    custom_values.get(getattr(row, "id", None), {}).get(
                        column[len("custom."):])
                )
            else:
                record.append(getattr(row, column, None))
        writer.writerow(record)

    from app.core.audit import record_audit

    record_audit(db, current_user, "export", entity, None, details=f"{len(rows)} rows")
    db.commit()

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{entity}.csv"'},
    )


@router.get("/template/{entity}", operation_id="importsTemplateEntity")
def import_template(
    entity: str,
    current_user: User = Depends(get_current_admin_user),
):
    """Download a CSV template with the correct headers and one example row."""
    _entity_or_404(entity)
    return StreamingResponse(
        iter([build_template(entity)]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{entity}-template.csv"'
        },
    )


@router.get("/columns/{entity}", operation_id="importsColumnsEntity")
def import_columns(
    entity: str,
    current_user: User = Depends(get_current_admin_user),
):
    """The contract for one entity: columns, types, and what is required."""
    _entity_or_404(entity)
    spec = get_spec(entity)
    return {
        "entity": entity,
        "label": spec.label,
        "natural_key": list(spec.natural_key),
        "columns": [
            {
                "name": column.name,
                "kind": column.kind,
                "required": column.required,
                "alternatives": list(column.alternatives),
                "enum": list(column.enum),
                "reference": column.reference,
                "reference_by": column.reference_by,
                "sensitive": column.sensitive,
                "description": column.description,
            }
            for column in spec.columns
        ],
    }


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------


@router.post("/import/{entity}", operation_id="importsImportEntity")
def import_csv(
    entity: str,
    file: UploadFile = File(...),
    dry_run: bool = Query(
        default=False,
        description="Validate only. Nothing is written to the database.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Import a CSV with validation, duplicate detection and row-level results.

    ``dry_run=true`` performs every check and writes nothing, so an
    operator can see exactly which rows would be created, updated, left
    alone or rejected — and why — before touching live data.
    """
    _entity_or_404(entity)
    data = _read_upload(file)
    if not data.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty")

    try:
        outcome = runner.dry_run(
            db,
            entity,
            data,
            file_name=file.filename,
            user_id=current_user.id,
            actor=current_user,
        )
    except ImportFileError as exc:
        raise ApiError(
            exc.code,
            exc.message,
            ErrorCategory.VALIDATION,
            details=exc.details or None,
        ) from None

    result = outcome.result
    _reject_structurally_broken(result)

    if dry_run:
        return {
            **_summary(
                result,
                confirmation_token=outcome.token,
                expires_at=outcome.expires_at.isoformat(),
            ),
            "rows": [row.as_dict() for row in result.outcomes[:200]],
            "note": "Dry run: nothing was written.",
        }

    # One-shot import: validate, then commit the result that was just
    # validated. The commit re-validates the same bytes, so the two agree.
    if runner.is_job_sized(result.total_rows):
        record = runner.pending_import(db, entity, outcome.token, current_user.id)
        job = runner.queue_job(db, entity, outcome.token, current_user.id)
        return _queued(record, job)

    try:
        committed = runner.commit(
            db,
            entity,
            outcome.token,
            user_id=current_user.id,
            actor=current_user,
        )
    except runner.ImportResultChanged as exc:
        raise ApiError(
            "import_result_changed",
            str(exc),
            ErrorCategory.CONFLICT,
        ) from None
    except runner.ImportNotFound as exc:
        raise ApiError(
            "invalid_confirmation_token", str(exc), ErrorCategory.CONFLICT
        ) from None

    return {
        **_summary(result),
        "created": committed.applied.created,
        "updated": committed.applied.updated,
        "unchanged": committed.applied.unchanged,
        "committed": True,
        "rows": [row.as_dict() for row in result.outcomes[:200]],
    }


@router.post("/import/{entity}/dry-run", operation_id="importsDryRunEntity")
def import_dry_run(
    entity: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Validate a CSV import without writing anything (dedicated endpoint).

    Returns the counts plus a ``confirmation_token`` that must be presented
    to the commit endpoint. The token is bound to the dry-run result hash,
    so it cannot be forged or reused for a different outcome.
    """
    _entity_or_404(entity)
    data = _read_upload(file)
    if not data.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty")

    try:
        outcome = runner.dry_run(
            db,
            entity,
            data,
            file_name=file.filename,
            user_id=current_user.id,
            actor=current_user,
        )
    except ImportFileError as exc:
        raise ApiError(
            exc.code,
            exc.message,
            ErrorCategory.VALIDATION,
            details=exc.details or None,
        ) from None

    result = outcome.result
    _reject_structurally_broken(result)
    return {
        **_summary(
            result,
            confirmation_token=outcome.token,
            expires_at=outcome.expires_at.isoformat(),
        ),
        "rows": [row.as_dict() for row in result.outcomes[:200]],
    }


@router.post("/import/{entity}/commit", operation_id="importsCommitEntity")
def import_commit(
    entity: str,
    confirmation_token: str = Query(..., description="Confirmation token from dry run"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Commit a previously validated dry-run import.

    Requires a ``confirmation_token`` obtained from the dry-run response.
    The token is bound to the dry-run result hash: the server re-validates
    the uploaded file and refuses the commit if the outcome has changed.
    """
    _entity_or_404(entity)
    try:
        record = runner.pending_import(
            db, entity, confirmation_token, current_user.id
        )
    except runner.ImportNotPermitted as exc:
        raise ApiError(
            "forbidden", str(exc), ErrorCategory.PERMISSION
        ) from None
    except runner.ImportCancelled as exc:
        raise ApiError(
            "import_cancelled", str(exc), ErrorCategory.CONFLICT
        ) from None
    except runner.ImportNotFound as exc:
        raise ApiError(
            "invalid_confirmation_token", str(exc), ErrorCategory.CONFLICT
        ) from None

    # A large file is applied by a job rather than inside the request.
    if runner.is_job_sized(record.total_rows):
        job = runner.queue_job(db, entity, confirmation_token, current_user.id)
        return _queued(record, job)

    try:
        committed = runner.commit(
            db,
            entity,
            confirmation_token,
            user_id=current_user.id,
            actor=current_user,
        )
    except runner.ImportNotPermitted as exc:
        raise ApiError(
            "forbidden", str(exc), ErrorCategory.PERMISSION
        ) from None
    except runner.ImportNotFound as exc:
        raise ApiError(
            "invalid_confirmation_token", str(exc), ErrorCategory.CONFLICT
        ) from None
    except runner.ImportResultChanged as exc:
        raise ApiError(
            "import_result_changed", str(exc), ErrorCategory.CONFLICT
        ) from None
    except ImportFileError as exc:
        raise ApiError(
            exc.code, exc.message, ErrorCategory.DEPENDENCY
        ) from None

    result = committed.result
    return {
        **_summary(result),
        "created": committed.applied.created,
        "updated": committed.applied.updated,
        "unchanged": committed.applied.unchanged,
        "committed": True,
        "warnings": committed.warnings,
    }


@router.post(
    "/import/{entity}/cancel",
    operation_id="importsCancelEntity",
)
def import_cancel(
    entity: str,
    confirmation_token: str = Query(..., description="Confirmation token from dry run"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Cancel an import that has not been committed.

    The import is one transaction, so cancellation is always safe: the rows
    it had written are taken back with it and nothing is left behind. A
    queued import is stopped by its job at the next batch boundary; a
    preview that was never committed simply stops being usable.

    A committed import cannot be cancelled — its rows are in the database —
    and the answer says so rather than reporting an unknown token. The
    cancellation is audited, in the same transaction as the status change.
    """
    _entity_or_404(entity)
    try:
        record = runner.cancel_import(
            db,
            entity,
            confirmation_token,
            current_user.id,
            actor=current_user,
        )
    except runner.ImportNotPermitted as exc:
        raise ApiError(
            "forbidden", str(exc), ErrorCategory.PERMISSION
        ) from None
    except runner.ImportNotCancellable as exc:
        raise ApiError(
            "import_not_cancellable", str(exc), ErrorCategory.CONFLICT
        ) from None
    except runner.ImportNotFound as exc:
        raise ApiError(
            "invalid_confirmation_token", str(exc), ErrorCategory.CONFLICT
        ) from None

    return {
        **_counts(record),
        "cancelled": True,
        "import_status": record.status,
        "committed": False,
        "note": (
            "The import is cancelled. The rows it had applied are taken back "
            "with its transaction, so nothing was written."
        ),
    }


@router.get(
    "/import/{entity}/progress/{job_id}",
    operation_id="importsProgressEntity",
)
def import_progress(
    entity: str,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """The progress of an import that is being applied by a background job.

    A file over the row threshold is answered ``202`` with the job's id.
    This operation answers what happened to it: the job's state, the rows the
    file holds, the rows applied and rejected, how many batches that is, and —
    when the job has finished — the same report the synchronous commit
    returns, including the rows that failed.

    The numbers come from three places that cannot disagree with the job:
    the job row is the state, the progress the handler records after every
    batch is the count, and the dry-run record is the size of the file and
    the rows it rejected. A failed job reports **zero** rows applied, because
    the import is one transaction and a failed one rolled back: the rows it
    had reached are not in the database, and reporting them would be a lie an
    operator would act on.

    Only the operator who queued the import is served. Another operator's job
    is answered ``404`` rather than ``403``, because a job id is a small
    integer and a ``403`` would confirm that the job exists.
    """
    _entity_or_404(entity)
    try:
        return progress.job_progress(db, entity, job_id, current_user.id)
    except progress.ImportProgressNotFound as exc:
        raise ApiError(
            "job_not_found", str(exc), ErrorCategory.NOT_FOUND
        ) from None


@router.get("/import/{entity}/row-errors", operation_id="importsRowErrorsEntity")
def import_row_errors(
    entity: str,
    confirmation_token: str = Query(..., description="Confirmation token from dry run"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Download a CSV of row-level errors from a dry run.

    The file is re-validated from the stored upload, so the errors are the
    errors of the exact bytes that were uploaded. Personal values are not
    in it: the validator never puts them in an error message.
    """
    _entity_or_404(entity)
    try:
        result = runner.row_errors(db, entity, confirmation_token, current_user.id)
    except runner.ImportNotPermitted as exc:
        raise ApiError(
            "forbidden", str(exc), ErrorCategory.PERMISSION
        ) from None
    except runner.ImportNotFound as exc:
        raise ApiError(
            "invalid_confirmation_token", str(exc), ErrorCategory.CONFLICT
        ) from None
    except ImportFileError as exc:
        raise ApiError(
            exc.code, exc.message, ErrorCategory.DEPENDENCY
        ) from None

    return StreamingResponse(
        iter([runner.row_error_csv(result)]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{entity}-row-errors.csv"'
        },
    )


@router.get("/entities", operation_id="importsListEntities")
def list_entities(u: User = Depends(get_current_admin_user)):
    return {"entities": list(ENTITIES.keys())}
