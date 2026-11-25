"""Applying an analysed file.

Bulk, not row-at-a-time
-----------------------
Oracle Autonomous Database raises ``ORA-12838`` when a statement modifies a
table that a parallel operation is reading, and the previous implementation
walked the rows one at a time. Every write here is therefore issued as a
single prepared statement per table per batch, executed with array binding.
One statement, many rows: the driver sends it once and the database does the
loop.

What a write means
------------------
The import is an **upsert** on the entity's natural key:

* the key is not there -> the row is **created**;
* the key is there and the values are the same -> the row is **unchanged**
  and nothing is written;
* the key is there and the values differ -> the row is **updated**, and only
  the columns the file actually supplied are written.

A column that is absent from the file, or present but blank, is left alone.
An import never clears a value it was not given. That is the difference
between an upsert and a replace, and it is what makes re-running the same
file a no-op rather than a way to lose data.

How a failed batch is undone
----------------------------
A batch that fails must leave nothing behind, and the rest of the file must
still be applied. The obvious implementation — a SAVEPOINT per batch — is
wrong on SQLite: releasing the outermost savepoint *commits* the
transaction, so the batch's rows survive the rollback that follows. That
behaviour is invisible on Oracle, where releasing a savepoint does not
commit, which is exactly the kind of difference a test on one database
misses.

So the undo is explicit. Before a batch is written, the values it is about
to change are read, and the statements that reverse it are prepared. If the
batch fails, those statements run inside the same transaction. The file
stays in one transaction throughout, which is what makes a storage failure
abort the whole import rather than half of it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, delete, insert, update
from sqlalchemy.orm import Session

from app.imports.analyse import Batch, key_part, natural_key_of
from app.imports.spec import EntitySpec


@dataclass
class Undo:
    """A statement that reverses one part of a batch."""

    kind: str  # "delete" | "restore" | "ledger"
    key: dict[str, Any] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)
    #: For ``"ledger"``: the objects the batch put into the session and
    #: that have to be taken back out of it when the batch fails.
    staged: list[Any] = field(default_factory=list)


@dataclass
class ApplyResult:
    """What an apply actually did."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: list = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "failed": len(self.errors),
        }


def _payload(
    spec: EntitySpec, values: dict[str, Any], resolved: dict[str, Any]
) -> dict[str, Any]:
    """The model attributes a row writes, from the file's values."""
    payload: dict[str, Any] = {}
    for column in spec.columns:
        if column.name == "id":
            continue
        if column.name in resolved:
            payload[column.writes_to] = resolved[column.name]
            continue
        if column.name in values:
            payload[column.writes_to] = values[column.name]
    return payload


def apply_batch(
    db: Session,
    spec: EntitySpec,
    batch: Batch,
    undo: list[Undo] | None = None,
    *,
    reference_id: int | None = None,
    created_by: int | None = None,
    errors: list | None = None,
) -> tuple[int, int, int]:
    """Apply one batch of rows. Does not commit.

    Returns ``(created, updated, unchanged)``. The statements that reverse
    the batch are appended to ``undo`` as the batch is prepared, before
    anything is written, so that the caller can reverse the batch even if
    the write itself fails part-way through.

    ``errors`` is the list a refusal is reported on. A ledger-backed row
    that the ledger refuses is reported there and skipped; the other rows
    of the batch are still applied.
    """
    if spec.writes_through_ledger:
        return _apply_ledger_batch(
            db,
            spec,
            batch,
            undo,
            reference_id=reference_id,
            created_by=created_by,
            errors=errors,
        )
    model = spec.model
    key_names = list(spec.natural_key_targets)
    if not key_names:
        return (0, 0, 0)
    if undo is None:
        undo = []

    keys: list[tuple] = []
    payloads: list[dict[str, Any]] = []
    for row_number, values in batch.rows:
        resolved = batch.resolved.get(row_number, {})
        keys.append(natural_key_of(spec, values, resolved))
        payloads.append(_payload(spec, values, resolved))

    existing = _existing_rows(db, spec, keys)

    creates: list[dict[str, Any]] = []
    updates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    unchanged = 0

    for key, payload in zip(keys, payloads):
        current = existing.get(key)
        if current is None:
            creates.append(payload)
            undo.append(
                Undo(kind="delete", key=dict(zip(key_names, key)))
            )
            continue
        changed = {
            attribute: value
            for attribute, value in payload.items()
            if attribute not in key_names
            and not _same(value, getattr(current, attribute, None))
        }
        if not changed:
            unchanged += 1
            continue
        params = {f"k_{name}": part for name, part in zip(key_names, key)}
        for attribute, value in changed.items():
            params[f"v_{attribute}"] = value
        updates.append((params, changed))
        undo.append(
            Undo(
                kind="restore",
                key=dict(zip(key_names, key)),
                values={
                    attribute: getattr(current, attribute, None)
                    for attribute in changed
                },
            )
        )

    if creates:
        db.execute(insert(model), creates)

    if updates:
        # One statement per distinct set of changed columns. In practice a
        # file supplies the same columns for every row, so this is one
        # statement; a file with blank cells produces a small number.
        groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for params, changed in updates:
            groups.setdefault(tuple(sorted(changed)), []).append(params)
        for columns, params_list in groups.items():
            statement = (
                update(model)
                .where(*_key_conditions(model, key_names))
                .values(
                    {
                        attribute: bindparam(f"v_{attribute}")
                        for attribute in columns
                    }
                )
            )
            db.execute(statement, params_list)

    if spec.name == "employees":
        _apply_custom_values(db, spec, batch, undo, errors=errors)

    return (len(creates), len(updates), unchanged)


def _apply_custom_values(
    db: Session,
    spec: EntitySpec,
    batch: Batch,
    undo: list[Undo],
    *,
    errors: list | None = None,
) -> None:
    """Write the ``custom.<key>`` columns of one batch (LP-CORE-005).

    Runs after the standard upsert, so every row's employee already exists
    and is found by its natural key. Values were coerced at analysis time;
    they are validated once more against the live definitions because a
    definition may have changed between the dry run and the commit. A row
    the live definitions reject is reported and skipped; the rest of the
    batch is still applied.
    """
    from app.imports.errors import ErrorCode, RowError
    from app.models.custom_field import CustomFieldValue
    from app.services import custom_fields as custom_field_service

    wanted: list[tuple[int, tuple, dict[str, str]]] = []
    for row_number, values in batch.rows:
        custom = {
            name[len("custom."):]: value
            for name, value in values.items()
            if isinstance(name, str)
            and name.startswith("custom.")
            and value is not None
        }
        if not custom:
            continue
        resolved = batch.resolved.get(row_number, {})
        wanted.append((row_number, natural_key_of(spec, values, resolved), custom))
    if not wanted:
        return

    defs = custom_field_service.def_map(db)
    key_names = list(spec.natural_key_targets)
    columns = [getattr(spec.model, name) for name in key_names]
    filters = []
    for column, parts in zip(columns, zip(*[key for _, key, _ in wanted])):
        filters.append(column.in_(list({part for part in parts})))
    found: dict[tuple, Any] = {}
    for row in db.query(*columns, spec.model).filter(*filters).all():
        found[
            tuple(
                key_part(spec, name, row[index])
                for index, name in enumerate(key_names)
            )
        ] = row[-1]

    existing_values: dict[tuple[int, int], CustomFieldValue] = {}
    employee_ids = list(
        {
            getattr(found.get(key), "id", None)
            for _, key, _ in wanted
        }
        - {None}
    )
    if employee_ids:
        for value_row in (
            db.query(CustomFieldValue)
            .filter(CustomFieldValue.employee_id.in_(employee_ids))
            .all()
        ):
            existing_values[(value_row.employee_id, value_row.def_id)] = value_row

    for row_number, key, custom in wanted:
        employee = found.get(key)
        if employee is None:
            continue  # the standard upsert reports a missing row, not this
        for custom_key, raw in custom.items():
            defn = defs.get(custom_key.lower())
            if defn is None:
                if errors is not None:
                    errors.append(
                        RowError(
                            row_number,
                            f"custom.{custom_key}",
                            ErrorCode.UNKNOWN_HEADERS,
                            f"Unknown custom field 'custom.{custom_key}'.",
                        )
                    )
                continue
            try:
                coerced = custom_field_service.validate_value(defn, raw)
            except custom_field_service.CustomFieldError as exc:
                if errors is not None:
                    errors.append(
                        RowError(row_number, f"custom.{custom_key}", exc.code, str(exc.message))
                    )
                continue
            current = existing_values.get((employee.id, defn.id))
            previous = current.value_text if current is not None else None
            prior_tenant = (
                current.tenant_id
                if current is not None and current.tenant_id is not None
                else getattr(employee, "tenant_id", None)
            )
            key_tenant = (
                current.tenant_id
                if current is not None and current.tenant_id is not None
                else getattr(employee, "tenant_id", None)
            )
            if coerced is None:
                if current is not None:
                    undo.append(
                        Undo(
                            kind="custom",
                            key={
                                "employee_id": employee.id,
                                "def_id": defn.id,
                                "tenant_id": key_tenant,
                            },
                            values={
                                "value_text": previous,
                                "tenant_id": prior_tenant,
                            },
                        )
                    )
                    db.delete(current)
                    del existing_values[(employee.id, defn.id)]
                continue
            if previous == coerced:
                continue
            undo.append(
                Undo(
                    kind="custom",
                    key={
                        "employee_id": employee.id,
                        "def_id": defn.id,
                        "tenant_id": key_tenant,
                    },
                    values={"value_text": previous, "tenant_id": prior_tenant},
                )
            )
            if current is None:
                current = CustomFieldValue(
                    tenant_id=getattr(employee, "tenant_id", None),
                    employee_id=employee.id,
                    def_id=defn.id,
                    value_text=coerced,
                )
                db.add(current)
                existing_values[(employee.id, defn.id)] = current
            else:
                current.value_text = coerced
    db.flush()


def undo_batch(db: Session, spec: EntitySpec, undo: list[Undo]) -> None:
    """Reverse a batch that failed."""
    model = spec.model
    key_names = list(spec.natural_key_targets)
    for step in reversed(undo):
        conditions = [
            getattr(model, name) == value
            for name, value in step.key.items()
        ]
        if step.kind == "delete":
            db.execute(delete(model).where(*conditions))
        elif step.kind == "restore" and step.values:
            db.execute(
                update(model).where(*conditions).values(**step.values)
            )
        elif step.kind == "ledger":
            _undo_ledger_batch(db, step)
        elif step.kind == "custom":
            _undo_custom_value(db, step)


def _undo_custom_value(db: Session, step: Undo) -> None:
    """Reverse one custom-field write.

    ``values["value_text"]`` is what the row held before the batch: null
    means the batch created the row, so the undo deletes it; otherwise the
    previous text is restored. ``tenant_id`` travels in both the key (to
    scope the lookup) and the values (to restore the row); a restored row
    for a tenant-owned employee is never left with a NULL tenant.
    """
    from app.models.custom_field import CustomFieldValue

    expected_tenant = step.key.get("tenant_id")
    if expected_tenant is None:
        expected_tenant = step.values.get("tenant_id")

    query = db.query(CustomFieldValue).filter(
        CustomFieldValue.employee_id == step.key.get("employee_id"),
        CustomFieldValue.def_id == step.key.get("def_id"),
    )
    if expected_tenant is not None:
        query = query.filter(CustomFieldValue.tenant_id == expected_tenant)
    row = query.first()
    previous = step.values.get("value_text")
    if previous is None:
        if row is not None:
            if (
                expected_tenant is not None
                and row.tenant_id is not None
                and row.tenant_id != expected_tenant
            ):
                return
            db.delete(row)
    elif row is None:
        restore_tenant = step.values.get("tenant_id")
        if restore_tenant is None:
            restore_tenant = step.key.get("tenant_id")
        if restore_tenant is None:
            # Never leave a tenant-owned row with a NULL tenant: fall
            # back to the employee's own tenant before re-creating.
            from app.models.employee import Employee

            owner = (
                db.query(Employee)
                .filter(Employee.id == step.key.get("employee_id"))
                .first()
            )
            if owner is not None:
                restore_tenant = getattr(owner, "tenant_id", None)
        db.add(
            CustomFieldValue(
                tenant_id=restore_tenant,
                employee_id=step.key.get("employee_id"),
                def_id=step.key.get("def_id"),
                value_text=previous,
            )
        )
    else:
        if (
            expected_tenant is not None
            and row.tenant_id is not None
            and row.tenant_id != expected_tenant
        ):
            return
        row.value_text = previous
        if row.tenant_id is None and expected_tenant is not None:
            row.tenant_id = expected_tenant


def _undo_ledger_batch(db: Session, step: Undo) -> None:
    """Take a failed ledger batch back out of the session.

    The rows a ledger batch writes are staged, not flushed, so reversing
    the batch means taking the staged objects back out of the session and
    putting the balance's cached columns back. Nothing was committed, so
    no history is rewritten: the rows never existed.
    """
    for obj in step.staged:
        if obj in db.new:
            db.expunge(obj)
    balance = step.key.get("balance")
    if balance is not None:
        for attribute, value in step.values.items():
            setattr(balance, attribute, value)


def _apply_ledger_batch(
    db: Session,
    spec: EntitySpec,
    batch: Batch,
    undo: list[Undo] | None = None,
    *,
    reference_id: int | None = None,
    created_by: int | None = None,
    errors: list | None = None,
) -> tuple[int, int, int]:
    """Apply one batch of rows that are written through a ledger.

    The rows of a ledger-backed entity are not written into their table.
    The history is written, through the ledger's own writer, and the
    ledger refreshes the cached columns from it. That is what keeps the
    derived balance and the cached columns in agreement, and it is what
    the guard that refuses a balance that moves without a row is there to
    protect.
    """
    from app.imports import ledger

    if undo is None:
        undo = []

    keys: list[tuple] = []
    rows: list[tuple[int, dict[str, Any]]] = []
    for row_number, values in batch.rows:
        resolved = batch.resolved.get(row_number, {})
        keys.append(natural_key_of(spec, values, resolved))
        rows.append((row_number, values))

    existing = _existing_rows(db, spec, keys)

    created = updated = unchanged = 0
    for key, (row_number, values) in zip(keys, rows):
        balance = existing.get(key)
        plan = ledger.plan_row(db, balance, values, row_number)
        if plan.refused:
            # The analysis refused this row before the commit, so the
            # file that is being applied is not the file that was
            # previewed. The row is reported and skipped rather than
            # written: a balance the ledger cannot explain is not a
            # balance the importer is allowed to write.
            if errors is not None:
                errors.append(plan.error)
            continue
        if plan.status == "unchanged":
            unchanged += 1
            continue

        staged: list[Any] = []
        cached: dict[str, Any] = {}
        if balance is None:
            balance = ledger.new_balance(spec, key)
            db.add(balance)
            staged.append(balance)
            created += 1
        else:
            for column in ledger.DAY_COLUMNS:
                cached[column] = getattr(balance, column, None)
            updated += 1

        # The undo is recorded before the rows are written, and it holds
        # the very list the rows are added to, so a write that fails
        # half way is still reversed.
        undo.append(
            Undo(kind="ledger", key={"balance": balance}, values=cached, staged=staged)
        )
        staged.extend(
            ledger.write_entries(
                db,
                balance,
                plan.entries,
                reference_id=reference_id,
                created_by=created_by,
            )
        )

    return (created, updated, unchanged)


def _key_conditions(model, key_names: list[str]):
    """The WHERE clause that identifies a row by its natural key."""
    return [
        getattr(model, name) == bindparam(f"k_{name}") for name in key_names
    ]


def _existing_rows(db: Session, spec: EntitySpec, keys: list[tuple]) -> dict[tuple, Any]:
    """The rows that already exist for the given natural keys.

    One query for the whole batch, not one per row. Oracle does not accept
    a row-value ``IN`` list on every version, so each key column is
    filtered separately and the exact tuple is matched in Python.
    """
    model = spec.model
    key_names = list(spec.natural_key_targets)
    if not key_names or not keys:
        return {}
    columns = [getattr(model, name) for name in key_names]
    filters = []
    for column, values in zip(columns, zip(*keys)):
        distinct = list({value for value in values})
        filters.append(column.in_(distinct))
    rows = db.query(*columns, model).filter(*filters).all()
    found: dict[tuple, Any] = {}
    for row in rows:
        key = tuple(
            key_part(spec, name, row[index])
            for index, name in enumerate(key_names)
        )
        found[key] = row[-1]
    return found


def _same(incoming: Any, stored: Any) -> bool:
    """Whether an incoming value equals the stored one."""
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
    return str(incoming) == str(stored)
