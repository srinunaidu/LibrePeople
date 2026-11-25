"""Analysing a CSV without writing anything.

The analysis is the single source of truth for what an import will do. The
dry run runs it; the commit runs it again against the same bytes and refuses
to proceed if the result has changed. That is what makes the confirmation
token meaningful: it is not a promise made by the client, it is a hash of
the outcome the server computed.

Two phases, because the row limit is ten thousand
-------------------------------------------------
*Phase one* streams the file, validates every cell, and writes the rows that
survived to a temporary spill file. Nothing is accumulated on the heap except
the counters and the errors.

*Phase two* reads the spill file back in batches and asks the database the
questions that need it: does this natural key already exist, does this
reference resolve, does this row differ from the one that is there. Batches
are bounded, so the memory the analysis uses does not grow with the file.

The spill file is temporary and is removed when the analysis finishes.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.imports import ledger
from app.imports.errors import ErrorCode, RowError, RowOutcome
from app.imports.headers import resolve_headers
from app.imports.parser import iter_records
from app.imports.spec import ENTITIES, EntitySpec
from app.imports.validation import (
    ImportBounds,
    canonical_enum_value,
    check_enum,
    coerce_value,
)

#: How many rows are held in memory at once during phase two.
BATCH_SIZE = 500


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


@dataclass
class HeaderResolution:
    """What the header row was understood to mean."""

    raw_headers: list[str] = field(default_factory=list)
    accepted: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    #: raw header -> canonical name, for every header that resolved.
    mapping: dict[str, str] = field(default_factory=dict)
    #: raw header -> canonical name, for headers resolved through an alias.
    aliases_used: dict[str, str] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """The outcome of analysing one file."""

    entity: str
    total_rows: int = 0
    create: int = 0
    update: int = 0
    unchanged: int = 0
    reject: int = 0
    errors: list[RowError] = field(default_factory=list)
    outcomes: list[RowOutcome] = field(default_factory=list)
    headers: HeaderResolution = field(default_factory=HeaderResolution)
    missing_columns: list[str] = field(default_factory=list)
    file_hash: str = ""
    result_hash: str = ""
    spill_path: str | None = None
    file_errors: list[RowError] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "total_rows": self.total_rows,
            "create": self.create,
            "update": self.update,
            "unchanged": self.unchanged,
            "reject": self.reject,
            "accepted": self.create + self.update + self.unchanged,
            # The older names, kept so that a client written against the
            # previous contract keeps working. An import no longer skips
            # rows: a row whose key already exists is updated or left
            # alone, never silently dropped.
            "created": self.create,
            "updated": self.update,
            "rejected": self.reject,
            "skipped": 0,
            "missing_columns": self.missing_columns,
            "unknown_headers": self.headers.unknown,
            "accepted_headers": self.headers.accepted,
            "aliases_used": self.headers.aliases_used,
            "file_hash": self.file_hash,
            "result_hash": self.result_hash,
        }


@dataclass
class Batch:
    """A bounded group of rows, with their resolved references."""

    rows: list[tuple[int, dict[str, Any]]] = field(default_factory=list)
    resolved: dict[int, dict[str, Any]] = field(default_factory=dict)
    unresolved: dict[int, list[tuple[str, Any]]] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Value encoding for the spill file
# --------------------------------------------------------------------------


def _encode(value: Any) -> Any:
    if isinstance(value, Decimal):
        return {"__t__": "dec", "v": str(value)}
    if isinstance(value, datetime):
        return {"__t__": "dt", "v": value.isoformat()}
    if isinstance(value, date):
        return {"__t__": "d", "v": value.isoformat()}
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, dict) and "__t__" in value:
        kind = value["__t__"]
        if kind == "dec":
            return Decimal(value["v"])
        if kind == "dt":
            return datetime.fromisoformat(value["v"])
        if kind == "d":
            return date.fromisoformat(value["v"])
    return value


# --------------------------------------------------------------------------
# The analysis
# --------------------------------------------------------------------------


class Analyzer:
    """Analyses one file against one entity."""

    def __init__(
        self,
        db: Session,
        entity: str,
        spec: EntitySpec,
        bounds: ImportBounds | None = None,
        batch_size: int = BATCH_SIZE,
    ) -> None:
        self.db = db
        self.spec = spec
        self.entity = entity
        self.bounds = bounds or ImportBounds()
        self.batch_size = batch_size
        self.result = AnalysisResult(entity=entity)
        self._seen_keys: set[tuple] = set()
        #: The rows the analysis rejected. They stay in the spill file so
        #: that the dry run can report them, but the commit must not
        #: write them.
        self._rejected_rows: set[int] = set()
        #: Active custom-field definitions for this tenant (LP-CORE-005),
        #: keyed by lowercased key. Only the employees entity accepts
        #: ``custom.<key>`` headers.
        self._custom_defs: dict = {}
        #: Raw header -> canonical ``custom.<key>`` column, in file order.
        self._custom_headers: dict[str, str] = {}
        #: The file's full header row, in order (standard + custom).
        self._header_order: list[str] | None = None

    # -- public ---------------------------------------------------------- #

    def run(self, stream, max_bytes: int, max_rows: int) -> AnalysisResult:
        """Analyse the file.

        The temporary spill file is kept when the analysis succeeds, because
        the commit needs the rows again. The caller is responsible for
        calling :meth:`discard`.

        Raises :class:`app.imports.errors.ImportFileError` when the file
        breaks a hard limit or its header cannot be understood.
        """
        spill = tempfile.NamedTemporaryFile(
            prefix="karmathy-import-", suffix=".jsonl", delete=False
        )
        self.result.spill_path = spill.name
        try:
            with spill:
                self._phase_one(stream, max_bytes, max_rows, spill)
            self._phase_two()
        except Exception:
            self.discard()
            raise
        self.result.result_hash = compute_result_hash(self.result)
        return self.result

    def discard(self) -> None:
        """Remove the temporary spill file."""
        path = self.result.spill_path
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:  # pragma: no cover - best effort
                pass
        self.result.spill_path = None

    # -- phase one ------------------------------------------------------- #

    def _phase_one(self, stream, max_bytes: int, max_rows: int, spill) -> None:
        columns = self.spec.column_names
        resolution = HeaderResolution(accepted=list(columns))

        header_seen = False
        pending: list[tuple[int, dict[str, Any]]] = []

        for row_number, record in iter_records(stream, max_bytes, max_rows):
            if not header_seen:
                header_seen = True
                raw_headers = [h for h in record]
                resolution.raw_headers = raw_headers
                standard_headers, custom_headers = self._split_custom_headers(
                    raw_headers
                )
                self._custom_headers = custom_headers
                self._header_order = raw_headers
                mapping, unknown = resolve_headers(standard_headers, columns)
                resolution.mapping = mapping
                # A custom key no definition declares is an unknown header:
                # accepting it would silently drop the column.
                for raw in raw_headers:
                    if raw in custom_headers:
                        continue
                    if (
                        raw not in mapping
                        and self._custom_key_of(raw) is not None
                    ):
                        unknown.append(raw)
                resolution.unknown = unknown
                self.result.headers = resolution
                for raw, canonical in mapping.items():
                    if raw != canonical:
                        resolution.aliases_used[raw] = canonical
                for raw, canonical in custom_headers.items():
                    resolution.accepted.append(canonical)
                if unknown:
                    self._reject_file(
                        ErrorCode.UNKNOWN_HEADERS,
                        "Unknown headers in the CSV: " + ", ".join(unknown),
                    )
                    return
                missing = self._missing_columns(mapping)
                if missing:
                    self.result.missing_columns = missing
                    self._reject_file(
                        ErrorCode.MISSING_REQUIRED,
                        "Required columns are absent: " + ", ".join(missing),
                    )
                    return
                continue

            self.result.total_rows += 1
            values, errors = self._validate_row(row_number, record, mapping)
            if errors:
                self.result.reject += 1
                self.result.errors.extend(errors)
                self.result.outcomes.append(
                    RowOutcome(row=row_number, status="reject", errors=errors)
                )
                continue
            pending.append((row_number, values))
            if len(pending) >= self.batch_size:
                self._write_batch(spill, pending)
                pending = []
        if pending:
            self._write_batch(spill, pending)

    def _custom_key_of(self, raw_header: str | None) -> str | None:
        """The custom-field key a header claims, or ``None``.

        Only the employees entity accepts ``custom.<key>`` headers; every
        other entity treats them as ordinary (unknown) headers.
        """
        if self.entity != "employees":
            return None
        from app.services import custom_fields as custom_field_service

        return custom_field_service.normalize_key(raw_header)

    def _split_custom_headers(
        self, raw_headers: list[str]
    ) -> tuple[list[str], dict[str, str]]:
        """Separate ``custom.<key>`` headers from standard ones (LP-CORE-005).

        A custom header resolves against this tenant's active definitions.
        A duplicate custom key is dropped from the custom mapping so the
        header falls through to the unknown-header rejection rather than
        silently winning over its twin.
        """
        if self.entity != "employees":
            return raw_headers, {}
        from app.services import custom_fields as custom_field_service

        self._custom_defs = custom_field_service.def_map(self.db)
        standard: list[str] = []
        custom: dict[str, str] = {}
        seen_keys: set[str] = set()
        for raw in raw_headers:
            key = custom_field_service.normalize_key(raw)
            if key is None:
                standard.append(raw)
                continue
            canonical = f"custom.{key}"
            if key not in self._custom_defs or canonical in seen_keys:
                # Unknown key, or the same key twice: leave it out of both
                # lists so the caller reports it as an unknown header.
                continue
            seen_keys.add(canonical)
            custom[raw] = canonical
        return standard, custom

    def _missing_columns(self, mapping: dict[str, str]) -> list[str]:
        """The requirement groups that no header satisfies."""
        present = set(mapping.values())
        present.update(self._custom_headers.values())
        missing: list[str] = []
        for group in self.spec.required_groups:
            if not any(name in present for name in group):
                missing.append(group[0])
        # A required custom definition whose header is absent fails every
        # row the same way a required contract column does.
        for key, defn in self._custom_defs.items():
            if defn.required and f"custom.{key}" not in present:
                missing.append(f"custom.{key}")
        return missing

    def _validate_row(
        self, row_number: int, record: list[str], mapping: dict[str, str]
    ) -> tuple[dict[str, Any], list[RowError]]:
        errors: list[RowError] = []
        # The header count is the full row: standard columns plus any
        # ``custom.<key>`` columns. The mapping alone omits the custom
        # half, so a row that lines up with the file would read as short.
        order = self._header_order or list(mapping)
        expected = len(order)
        if len(record) > expected:
            errors.append(
                RowError(
                    row_number,
                    None,
                    ErrorCode.TOO_MANY_FIELDS,
                    f"The row has {len(record)} values but the header declares "
                    f"{expected}.",
                )
            )
        elif len(record) < expected:
            errors.append(
                RowError(
                    row_number,
                    None,
                    ErrorCode.TOO_FEW_FIELDS,
                    f"The row has {len(record)} values but the header declares "
                    f"{expected}.",
                )
            )

        raw_by_canonical: dict[str, str] = {}
        raw_headers = order
        for index, raw_header in enumerate(raw_headers):
            if index >= len(record):
                break
            cell = record[index]
            if cell is None:
                continue
            # The cell is not stripped here. A leading tab or carriage
            # return is one of the characters that makes a spreadsheet
            # treat a cell as a formula, and stripping it here would hide
            # the trigger from the neutraliser. The coercion decides what
            # to keep.
            text = str(cell)
            if text.strip(" ") == "":
                continue
            canonical = mapping.get(raw_header, self._custom_headers.get(raw_header))
            if canonical is None:
                continue
            raw_by_canonical[canonical] = text

        values: dict[str, Any] = {}
        for column in self.spec.columns:
            if column.name == "id":
                continue
            raw = raw_by_canonical.get(column.name)
            if raw is None:
                continue
            value, error = coerce_value(column, raw, self.bounds)
            if error:
                error.row = row_number
                errors.append(error)
                continue
            if value is None:
                continue
            enum_error = check_enum(column, value)
            if enum_error:
                enum_error.row = row_number
                errors.append(enum_error)
                continue
            values[column.name] = canonical_enum_value(column, value)

        # A requirement is satisfied by any one of its alternatives.
        for group in self.spec.required_groups:
            if any(values.get(name) is not None for name in group):
                continue
            errors.append(
                RowError(
                    row_number,
                    group[0],
                    ErrorCode.MISSING_REQUIRED,
                    f"'{group[0]}' is required"
                    + (f" (or {', '.join(group[1:])})" if len(group) > 1 else ""),
                )
            )

        # Configurable attributes (LP-CORE-005): coerced by the definition's
        # type. A blank cell for a required definition is a missing value,
        # not a cleared one — an import never clears what it was not given.
        if self._custom_headers:
            from app.services import custom_fields as custom_field_service

            for canonical in sorted(set(self._custom_headers.values())):
                defn = self._custom_defs.get(canonical[len("custom."):])
                if defn is None:
                    continue
                raw = raw_by_canonical.get(canonical)
                if raw is None:
                    if defn.required:
                        errors.append(
                            RowError(
                                row_number,
                                canonical,
                                ErrorCode.MISSING_REQUIRED,
                                f"'{canonical}' is required.",
                            )
                        )
                    continue
                try:
                    coerced = custom_field_service.validate_value(defn, raw)
                except custom_field_service.CustomFieldError as exc:
                    errors.append(
                        RowError(row_number, canonical, exc.code, str(exc.message))
                    )
                    continue
                if coerced is None:
                    if defn.required:
                        errors.append(
                            RowError(
                                row_number,
                                canonical,
                                ErrorCode.MISSING_REQUIRED,
                                f"'{canonical}' is required.",
                            )
                        )
                    continue
                values[canonical] = coerced

        # The tenant's salary bounds apply on top of the column's own bounds.
        for column in self.spec.columns:
            if column.name not in values or column.kind != "decimal":
                continue
            low, high = self.bounds.salary_bounds()
            value = values[column.name]
            if low is not None and value < Decimal(str(low)):
                errors.append(
                    RowError(
                        row_number,
                        column.name,
                        ErrorCode.BELOW_MINIMUM,
                        f"'{column.name}' must be at least {low}",
                    )
                )
            elif high is not None and value > Decimal(str(high)):
                errors.append(
                    RowError(
                        row_number,
                        column.name,
                        ErrorCode.ABOVE_MAXIMUM,
                        f"'{column.name}' must be at most {high}",
                    )
                )

        # Rules that span two columns of the same row.
        for rule in self.spec.consistency:
            lower = values.get(rule.lower)
            higher = values.get(rule.higher)
            if lower is None or higher is None:
                continue
            try:
                if Decimal(str(lower)) > Decimal(str(higher)):
                    errors.append(
                        RowError(
                            row_number,
                            rule.lower,
                            ErrorCode.INCONSISTENT_VALUES,
                            rule.message,
                        )
                    )
            except Exception:  # noqa: BLE001
                continue

        return values, errors

    def _write_batch(self, spill, pending) -> None:
        for row_number, values in pending:
            spill.write(
                json.dumps(
                    {
                        "row": row_number,
                        "values": {
                            name: _encode(value)
                            for name, value in values.items()
                        },
                    }
                ).encode("utf-8")
            )
            spill.write(b"\n")

    def _reject_file(self, code: str, message: str) -> None:
        error = RowError(0, None, code, message)
        self.result.file_errors.append(error)
        self.result.errors.append(error)
        self.result.reject = self.result.total_rows

    # -- phase two ------------------------------------------------------- #

    def _phase_two(self) -> None:
        """Resolve references, detect duplicates, and classify each row."""
        if self.result.file_errors:
            return
        for batch in self._raw_batches():
            self._classify_batch(batch)

    def iter_batches(self) -> Iterator[Batch]:
        """Read the spill file back in bounded batches.

        Rows that the analysis rejected are **not** returned. The spill
        file holds every row that survived the cell-level checks, which
        includes rows that were later rejected for a reference that does
        not resolve or for a duplicate. Those rows must not be written,
        and the commit must write exactly what the preview showed.
        """
        for batch in self._raw_batches():
            kept = [
                (row_number, values)
                for row_number, values in batch.rows
                if row_number not in self._rejected_rows
            ]
            if not kept:
                continue
            filtered = Batch(rows=kept)
            filtered.resolved = batch.resolved
            filtered.unresolved = batch.unresolved
            yield filtered

    def _raw_batches(self) -> Iterator[Batch]:
        """Every row in the spill file, including the ones later rejected."""
        path = self.result.spill_path
        if not path or not os.path.exists(path):
            return
        rows: list[tuple[int, dict[str, Any]]] = []
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                values = {
                    name: _decode(value)
                    for name, value in payload["values"].items()
                }
                rows.append((payload["row"], values))
                if len(rows) >= self.batch_size:
                    yield self._prepare(rows)
                    rows = []
        if rows:
            yield self._prepare(rows)

    def _prepare(self, rows) -> Batch:
        """Resolve the references of one batch."""
        batch = Batch(rows=rows)
        for column in self.spec.reference_columns():
            target_spec = ENTITIES.get(column.reference or "")
            if target_spec is None:
                continue
            wanted: list[Any] = []
            for _row_number, values in rows:
                value = values.get(column.name)
                if value is not None and value not in wanted:
                    wanted.append(value)
            if not wanted:
                continue
            found = self._lookup_reference(target_spec, wanted, column.reference_by)
            for row_number, values in rows:
                value = values.get(column.name)
                if value is None:
                    continue
                identifier = found.get(value)
                if identifier is None:
                    batch.unresolved.setdefault(row_number, []).append(
                        (column.name, value)
                    )
                    continue
                batch.resolved.setdefault(row_number, {})[column.name] = identifier
        return batch

    def _lookup_reference(
        self, target_spec: EntitySpec, values: list[Any], by_id: bool
    ) -> dict[Any, int]:
        """Map a reference value to the id of the record it names."""
        model = target_spec.model
        if by_id == "id":
            rows = self.db.query(model.id).filter(model.id.in_(values)).all()
            return {row[0]: row[0] for row in rows}
        key_names = list(target_spec.natural_key_targets)
        if not key_names:
            return {}
        key_columns = [getattr(model, name) for name in key_names]
        if len(key_columns) == 1:
            rows = (
                self.db.query(key_columns[0], model.id)
                .filter(key_columns[0].in_(values))
                .all()
            )
            return {row[0]: row[1] for row in rows}
        # A composite key. Oracle does not accept a row-value IN list on
        # every version, so each column is filtered separately and the exact
        # tuple is matched in Python.
        filters = []
        for index, column in enumerate(key_columns):
            filters.append(column.in_([value[index] for value in values]))
        rows = self.db.query(*key_columns, model.id).filter(*filters).all()
        result: dict[Any, int] = {}
        for row in rows:
            result[tuple(row[:-1])] = row[-1]
        return result

    def _classify_batch(self, batch: Batch) -> None:
        keyed: list[tuple[int, dict[str, Any], tuple]] = []
        for row_number, values in batch.rows:
            key = natural_key_of(self.spec, values, batch.resolved.get(row_number, {}))
            keyed.append((row_number, values, key))

        existing = self._existing_rows([key for _, _, key in keyed])
        collisions = self._unique_collisions(keyed, existing)

        for row_number, values, key in keyed:
            outcome = RowOutcome(row=row_number, status="reject", natural_key=key)

            if key in self._seen_keys:
                outcome.errors.append(
                    RowError(
                        row_number,
                        self.spec.natural_key[0],
                        ErrorCode.DUPLICATE_IN_FILE,
                        "An earlier row in this file has the same "
                        + " and ".join(self.spec.natural_key),
                    )
                )
                self._reject(outcome)
                continue
            self._seen_keys.add(key)

            collision = collisions.get(row_number)
            if collision is not None:
                outcome.errors.append(collision)
                self._reject(outcome)
                continue

            unresolved = batch.unresolved.get(row_number)
            if unresolved:
                for column_name, _raw in unresolved:
                    column = self.spec.column(column_name)
                    target = (column.reference if column else "") or "record"
                    outcome.errors.append(
                        RowError(
                            row_number,
                            column_name,
                            ErrorCode.REFERENCE_NOT_FOUND,
                            f"No {target} matches the value given for "
                            f"'{column_name}'",
                        )
                    )
                self._reject(outcome)
                continue

            current = existing.get(key)
            if self.spec.writes_through_ledger:
                # A ledger-backed entity is not compared with the row that
                # is in the table: it is compared with the history that
                # explains the row, because the row is only a cache of
                # that history. The same plan decides what the commit
                # will write, so the preview and the commit agree.
                plan = ledger.plan_row(self.db, current, values, row_number)
                if plan.error is not None:
                    outcome.errors.append(plan.error)
                    self._reject(outcome)
                    continue
                outcome.status = plan.status
                if plan.status == "create":
                    self.result.create += 1
                elif plan.status == "update":
                    self.result.update += 1
                else:
                    self.result.unchanged += 1
                self.result.outcomes.append(outcome)
                continue
            if current is None:
                outcome.status = "create"
                self.result.create += 1
            elif self._differs(current, values, batch.resolved.get(row_number, {})):
                outcome.status = "update"
                self.result.update += 1
            else:
                outcome.status = "unchanged"
                self.result.unchanged += 1
            self.result.outcomes.append(outcome)

    def _reject(self, outcome: RowOutcome) -> None:
        self._rejected_rows.add(outcome.row)
        self.result.reject += 1
        self.result.errors.extend(outcome.errors)
        self.result.outcomes.append(outcome)

    def _existing_rows(self, keys: list[tuple]) -> dict[tuple, Any]:
        """The rows that already exist for the given natural keys."""
        model = self.spec.model
        target_names = list(self.spec.natural_key_targets)
        if not target_names or not keys:
            return {}
        columns = [getattr(model, name) for name in target_names]
        filters = []
        for column, values in zip(columns, zip(*keys)):
            distinct = list({value for value in values})
            filters.append(column.in_(distinct))
        rows = self.db.query(*columns, model).filter(*filters).all()
        found: dict[tuple, Any] = {}
        for row in rows:
            key = tuple(
                key_part(self.spec, name, row[index])
                for index, name in enumerate(target_names)
            )
            found[key] = row[-1]
        return found

    def _unique_collisions(self, keyed, existing) -> dict[int, RowError]:
        """Rows whose value collides with an existing row's unique column.

        A row whose own natural key is already in the database does not
        collide with itself: re-importing the same file must leave the
        row unchanged, not reject it because it already holds its own
        email address.
        """
        model = self.spec.model
        collisions: dict[int, RowError] = {}
        natural_targets = set(self.spec.natural_key_targets)
        unique_columns = [
            column
            for column in model.__table__.columns
            if column.unique
            and column.name not in natural_targets
            and column.name != "id"
        ]
        for column in unique_columns:
            values_by_row: dict[Any, list[int]] = {}
            for row_number, values, _key in keyed:
                value = values.get(column.name)
                if value is None:
                    continue
                values_by_row.setdefault(value, []).append(row_number)
            if not values_by_row:
                continue
            rows = (
                self.db.query(getattr(model, column.name), model.id)
                .filter(getattr(model, column.name).in_(list(values_by_row)))
                .all()
            )
            holders = {row[0]: row[1] for row in rows}
            for value, row_numbers in values_by_row.items():
                holder = holders.get(value)
                if holder is None:
                    continue
                for row_number in row_numbers:
                    key = next(
                        (k for r, _v, k in keyed if r == row_number), None
                    )
                    own = existing.get(key) if key is not None else None
                    if own is not None and getattr(own, "id", None) == holder:
                        # The row already holds this value. It is the
                        # same record, not a collision with another one.
                        continue
                    collisions[row_number] = RowError(
                        row_number,
                        column.name,
                        ErrorCode.DUPLICATE_EXISTS,
                        f"A record with this {column.name} already exists",
                    )
        return collisions

    def _differs(self, current, values: dict[str, Any], resolved: dict[str, Any]) -> bool:
        """Whether the incoming values differ from the stored row."""
        for column in self.spec.columns:
            if column.name == "id":
                continue
            if column.name in resolved:
                incoming = resolved[column.name]
            elif column.name in values:
                incoming = values[column.name]
            else:
                continue
            stored = getattr(current, column.writes_to, None)
            if not _equal(incoming, stored):
                return True
        return False


def natural_key_of(
    spec: EntitySpec, values: dict[str, Any], resolved: dict[str, Any]
) -> tuple:
    """The natural key of a row, after its references are resolved.

    The parts come back in the order of ``spec.natural_key`` and are
    normalised against the *model* attribute each one is stored in, so the
    key a row computes matches the key the database returns.
    """
    parts: list[Any] = []
    for name in spec.natural_key:
        column = spec.column(name)
        target = column.writes_to if column else name
        if name in resolved:
            parts.append(resolved[name])
        elif target in resolved:
            parts.append(resolved[target])
        else:
            parts.append(values.get(name, values.get(target)))
    targets = spec.natural_key_targets
    return tuple(
        key_part(spec, target, part)
        for target, part in zip(targets, parts)
    )


def key_part(spec: EntitySpec, column_name: str, value: Any) -> Any:
    """Normalise one part of a natural key so it compares reliably.

    ``column_name`` is the model attribute the part is stored in, so the
    same normalisation is applied to a value computed from the file and to
    a value read back from the database.
    """
    if value is None:
        return None
    column = spec.column(column_name)
    if column is None:
        return value
    if column.kind == "integer" or column.reference_by == "id":
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if column.kind == "decimal":
        try:
            return Decimal(str(value))
        except Exception:  # noqa: BLE001
            return value
    return str(value)


def _equal(incoming: Any, stored: Any) -> bool:
    """Compare an incoming value with a stored one."""
    if incoming is None and stored is None:
        return True
    if incoming is None or stored is None:
        return False
    if isinstance(incoming, bool) or isinstance(stored, bool):
        return bool(incoming) == bool(stored)
    if isinstance(incoming, Decimal) or isinstance(stored, Decimal):
        try:
            return Decimal(str(incoming)) == Decimal(str(stored))
        except Exception:  # noqa: BLE001
            return str(incoming) == str(stored)
    if isinstance(incoming, (date, datetime)):
        return incoming == stored
    return str(incoming) == str(stored)


def compute_result_hash(result: AnalysisResult) -> str:
    """A stable hash of the analysis outcome.

    The hash covers the entity, the file's own hash, the counters, and every
    row's status and error codes. Any change to the outcome changes the
    hash, so a confirmation token issued for one outcome cannot be used for
    another.
    """
    digest = hashlib.sha256()
    digest.update(result.entity.encode("utf-8"))
    digest.update(result.file_hash.encode("utf-8"))
    digest.update(
        f"{result.total_rows}:{result.create}:{result.update}:"
        f"{result.unchanged}:{result.reject}".encode("utf-8")
    )
    for outcome in result.outcomes:
        digest.update(str(outcome.row).encode("utf-8"))
        digest.update(outcome.status.encode("utf-8"))
        for error in outcome.errors:
            digest.update(error.code.encode("utf-8"))
            digest.update((error.column or "").encode("utf-8"))
    return digest.hexdigest()
