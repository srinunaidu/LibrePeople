"""The rules every master-data reference entity shares.

Four entities — departments, jobs, locations and positions — are the spine the
rest of the product hangs off: employees, positions, requisitions, forecasts
and cost centres all point at them. They were created and never edited, never
archived and never deleted, so an operator who misspelled a code had no way to
correct it, and nothing stopped two records from carrying the same natural key.

This module holds the three guards they all need, in one place, so that the
rules are stated once:

* **A natural key is unique across the entity** — not only because a unique
  index says so, which SQLite only enforces when ``PRAGMA foreign_keys`` is on
  and Oracle only reports as ``ORA-00001``, but as ``409 duplicate_natural_key``
  naming the key, which is what a form can render.
* **A reference must exist and be active.** A foreign key that does not resolve
  is refused as ``422 reference_not_found`` with the entity it should have
  pointed at, rather than as a database error.
* **A record still pointed at is archived, not deleted.** Deletion is refused
  as ``409 reference_in_use``, and the refusal lists what points at it and how
  many rows, so the operator can move them or archive instead.

Nothing here writes: the caller decides the transaction and the audit row.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

from sqlalchemy import Column, func
from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found, validation


def load_or_404(db: Session, model: type, object_id: int, label: str) -> Any:
    """Load one row by primary key, or raise 404 naming the entity."""
    row = db.get(model, object_id)
    if row is None:
        raise not_found(label)
    return row


def ensure_unique_natural_key(
    db: Session,
    model: type,
    column: Any,
    value: str,
    exclude_id: int | None = None,
    label: str = "record",
) -> None:
    """Refuse a second row that carries the same natural key.

    ``exclude_id`` is the row being edited: it is allowed to keep the key it
    already owns. The comparison is case-insensitive on the code, because two
    codes that differ only in case read as the same code to a person and are
    matched loosely by the importer.
    """
    if value is None:
        return
    query = db.query(func.count()).select_from(model).filter(
        func.lower(column) == func.lower(str(value).strip())
    )
    if exclude_id is not None:
        query = query.filter(model.id != exclude_id)
    if query.scalar():
        raise conflict(
            "duplicate_natural_key",
            f"{label} already uses the code {value!r}. Codes are unique.",
            entity=model.__name__.lower(),
            value=value,
        )


def ensure_reference(
    db: Session,
    model: type,
    object_id: int | None,
    label: str,
    required: bool = True,
) -> Any:
    """Load a referenced entity, refusing an id that does not resolve.

    Called because a missing reference is a *validation* failure of the payload,
    not a missing resource of its own: the operator named an id that does not
    exist, and the message has to say which field.
    """
    if object_id is None:
        if required:
            raise validation(
                "reference_not_found",
                f"{label} is required.",
                entity=label,
            )
        return None
    row = db.get(model, object_id)
    if row is None:
        raise validation(
            "reference_not_found",
            f"{label} {object_id} does not exist.",
            entity=label,
            id=object_id,
        )
    return row


def refuse_null_updates(
    changes: dict[str, Any],
    required: Sequence[str],
    label: str,
) -> None:
    """Refuse an explicit ``null`` for a column that cannot hold one.

    A partial edit says "change only what I sent", and a client that sends
    ``"name": null`` has asked to clear a column the schema requires. Left
    alone that reaches the database as a constraint error; it is a payload
    error and is refused before anything is written.
    """
    nulls = sorted(field for field in required if field in changes and changes[field] is None)
    if nulls:
        raise validation(
            "validation_error",
            f"{label} cannot clear {', '.join(nulls)}; the field is required.",
            entity=label,
            fields=nulls,
        )


def count_dependents(
    db: Session,
    checks: Sequence[tuple[str, type, Any]],
    object_id: int,
) -> list[dict[str, Any]]:
    """Count the rows that point at ``object_id``, per dependent entity."""
    found: list[dict[str, Any]] = []
    for label, model, column in checks:
        n = (
            db.query(func.count())
            .select_from(model)
            .filter(column == object_id)
            .scalar()
        )
        if n:
            found.append({"entity": label, "count": int(n)})
    return found


def refuse_if_in_use(
    dependents: Iterable[dict[str, Any]],
    label: str,
    object_id: int,
) -> None:
    """Refuse deletion of a record that other rows still point at.

    The details carry the dependents and the action that is allowed instead, so
    the client can say "move the 12 employees first, or archive" rather than
    "delete failed".
    """
    found = list(dependents)
    if found:
        raise conflict(
            "reference_in_use",
            f"{label} {object_id} is still referenced and cannot be deleted. "
            "Archive it, or move the referencing rows first.",
            entity=label,
            id=object_id,
            dependents=found,
            alternative="archive",
        )
