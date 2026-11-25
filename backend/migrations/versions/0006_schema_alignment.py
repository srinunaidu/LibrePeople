"""schema_alignment: add the columns the models expect

Revision ID: 0006_schema_alignment
Revises: 0005_forecasting
Create Date: 2026-10-21

The platform was deployed before Alembic existed. Its schema was built by
``Base.metadata.create_all()`` from the models as they were at the time,
and the models have moved on since. The frozen baseline deliberately does
not evolve those tables, so the tables the deployment created are missing
the columns the code now reads. A query that touches one of them fails at
runtime rather than at migration time.

This revision adds the missing columns:

- ``case_comments.comment`` — the body of a comment on an HR case.
- ``compensation_bands.level`` — the band, e.g. Junior or Principal.
- ``pay_runs.processed_by`` / ``processed_at`` — who processed the run
  and when, for segregation of duties.
- ``pay_runs.finalized_by`` / ``finalized_at`` — who finalised the run
  and when.
- ``pay_runs.warning`` — the operator-facing note about the run.

The two columns that must not be null are added nullable, backfilled,
and then made not null: a table that already holds rows cannot take a
not-null column without a default.

Every step checks whether it is needed first, so the revision is safe to
run against a database that already has the columns.

Identifiers come from the catalog, not from the reflection
----------------------------------------------------------
SQLAlchemy's Oracle reflection **lower-cases every identifier** it
reports: ``get_table_names()`` answers ``case_comments`` while the
catalog holds ``CASE_COMMENTS``, and a column the catalog holds as
``comment`` — lower case, quoted, because ``COMMENT`` is a reserved word —
comes back as ``comment``.

The catalog is therefore *mixed*, and a statement built from a reflected
name names an object that does not exist. The first version of this
revision built its backfill out of the reflected name and the chain could
not be applied to a fresh Oracle database: it failed with ``ORA-00942``
("table or view does not exist") and then ``ORA-00904`` ("invalid
identifier").

Every statement here is built from the names the catalog holds, read
through :func:`app.core.migrations.catalog_names` — ``ALL_TABLES`` and
``ALL_TAB_COLUMNS``, which are the only places the real names are.

A column that is already not null is not constrained again
-----------------------------------------------------------
The first version of this revision constrained every column it found,
without asking whether the column was already ``NOT NULL``. A fresh
database is built by ``create_all()`` from the current models, and those
models declare both ``case_comments.comment`` and
``compensation_bands.level`` as not null — so the constraint was already
there and Oracle refused the second one with ``ORA-01442`` ("column to be
modified to NOT NULL is already NOT NULL").

The nullability is read from ``ALL_TAB_COLUMNS.NULLABLE`` and the step is
skipped when the column is already not null.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names

revision = "0006_schema_alignment"
down_revision = "0005_forecasting"
branch_labels = None
depends_on = None


#: Columns to add: table -> (column name, definition, backfill value).
#: The backfill is the value the column is given on the rows that already
#: exist; it is what makes the not-null constraint possible.
COLUMNS: dict[str, list[tuple[str, sa.Column, object | None]]] = {
    "case_comments": [
        ("comment", sa.Column("comment", sa.Text(), nullable=True), ""),
    ],
    "compensation_bands": [
        ("level", sa.Column("level", sa.String(40), nullable=True), "Unspecified"),
    ],
    "pay_runs": [
        (
            "processed_by",
            sa.Column("processed_by", sa.Integer(), nullable=True),
            None,
        ),
        (
            "processed_at",
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            None,
        ),
        (
            "finalized_by",
            sa.Column("finalized_by", sa.Integer(), nullable=True),
            None,
        ),
        (
            "finalized_at",
            sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
            None,
        ),
        ("warning", sa.Column("warning", sa.Text(), nullable=True), None),
    ],
}

#: The columns that end up not null.
NOT_NULL = {("case_comments", "comment"), ("compensation_bands", "level")}


def needs_not_null(catalog, table: str, column: str) -> bool:
    """Whether the column still has to be made not null.

    The answer comes from the catalog, not from the revision's own opinion.
    A column the catalog already reports as ``NOT NULL`` must not be
    constrained again: Oracle refuses the second constraint with
    ORA-01442 ("column to be modified to NOT NULL is already NOT NULL"),
    and a fresh database built by ``create_all()`` from the current models
    already has the constraint.
    """
    return not catalog.is_not_null(table, column)


def _supports_modify_not_null(bind) -> bool:
    """Whether the dialect can add a not-null constraint to a table.

    Oracle can, with ``ALTER TABLE ... MODIFY``. SQLite cannot add the
    constraint to a table that already holds rows, and there is no
    equivalent statement.
    """
    return bind.dialect.name not in {"sqlite"}


def backfill_statement(live_table: str, live_column: str) -> str:
    """The statement that fills a newly added column.

    The names are the ones the catalog uses, spelled exactly. Oracle folds
    unquoted identifiers to upper case, so a column the model calls
    ``comment`` is ``comment`` in lower case and quoted in the catalog when
    it was created as a reserved word — and a statement that quotes it as
    ``COMMENT`` does not find it.
    """
    return (
        f'UPDATE "{live_table}" SET "{live_column}" = :value '
        f'WHERE "{live_column}" IS NULL'
    )


def not_null_statement(live_table: str, live_column: str) -> str:
    """The statement that makes a column not null."""
    return f'ALTER TABLE "{live_table}" MODIFY "{live_column}" NOT NULL'


def _is_already_exists(exc: BaseException) -> bool:
    """Whether the error means the column is already there.

    Oracle raises ORA-01430 for a column that is already present. The
    database may hold the column under a name that differs from the
    model's only in case, and the identifier the model uses is folded by
    the database, so the two can be the same column. Treating the error
    as "it is there" is correct in that case and harmless in any other.
    """
    text = str(exc)
    return "ORA-01430" in text or "already exists" in text.lower()


def upgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=list(COLUMNS))

    for table, columns in COLUMNS.items():
        live_name = catalog.table(table)
        if live_name is None:
            # The table itself is missing; that is a different problem and
            # this revision does not invent tables.
            print(f"[0006_schema_alignment] table {table} is not present; skipping")
            continue

        # The catalog's names, not the reflection's. The reflection
        # lower-cases every identifier, and the catalog is mixed.
        present = catalog.columns.get(live_name.upper(), {})
        for name, definition, backfill in columns:
            if name.upper() in present:
                # The column is there under the name the catalog uses. The
                # statement uses that exact name, so it works whether the
                # database folds identifiers to upper case or not.
                live_column = present[name.upper()]
            else:
                live_column = name
                try:
                    op.add_column(live_name, definition)
                except Exception as exc:  # noqa: BLE001
                    if not _is_already_exists(exc):
                        raise
                    # The column is already there under the name the
                    # database uses. Adding it again is refused, and it does
                    # not need to be added.
                    print(
                        f"[0006_schema_alignment] {live_name}.{name} is already "
                        "present; skipping"
                    )
                    continue
                print(f"[0006_schema_alignment] added {live_name}.{name}")

            if backfill is None:
                continue
            # The column has to hold a value on the rows that already
            # exist before it can be made not null. The statement uses
            # the name the catalog has for the column, so it works on a
            # database that folds identifiers to upper case.
            op.execute(
                sa.text(backfill_statement(live_name, live_column)).bindparams(
                    value=backfill
                )
            )

    # Now the not-null constraints can be applied. The catalog is read
    # again because the columns above may have been added since the first
    # read.
    catalog = catalog_names(bind, tables=list(COLUMNS))
    for table, name in sorted(NOT_NULL):
        live_name = catalog.table(table)
        if live_name is None:
            continue
        live_column = catalog.column(live_name, name)
        if live_column is None:
            # The column is not there under any spelling, so there is
            # nothing to constrain.
            continue
        if not needs_not_null(catalog, live_name, live_column):
            # The column is already not null. Constraining it again is
            # refused by Oracle with ORA-01442, and it is not needed.
            print(
                f"[0006_schema_alignment] {live_name}.{live_column} is already "
                "not null; skipping"
            )
            continue
        if not _supports_modify_not_null(bind):
            # SQLite cannot add a not-null constraint to an existing table.
            # The column is still backfilled, so the values are there; only
            # the constraint is missing, and only on a dialect that cannot
            # express it.
            print(
                f"[0006_schema_alignment] {live_name}.{live_column} stays "
                "nullable: this dialect cannot add a not-null constraint"
            )
            continue
        op.execute(sa.text(not_null_statement(live_name, live_column)))
        print(f"[0006_schema_alignment] {live_name}.{live_column} is now not null")


def downgrade() -> None:
    """Remove the columns this revision added.

    The data in them is lost, which is the correct reverse of adding a
    column.

    The drop goes through Alembic's batch mode: SQLite refuses to drop a
    column that a foreign key refers to, and the batch mode rebuilds the
    table instead of altering it. On Oracle the batch mode issues the
    plain statement, because Oracle can drop the column directly.
    """
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=list(COLUMNS))

    for table, columns in COLUMNS.items():
        live_name = catalog.table(table)
        if live_name is None:
            continue
        to_drop = []
        for name, _definition, _backfill in columns:
            live_column = catalog.column(live_name, name)
            if live_column is not None:
                to_drop.append(live_column)
        if not to_drop:
            continue
        with op.batch_alter_table(live_name) as batch:
            for live_column in to_drop:
                batch.drop_column(live_column)
                print(f"[0006_schema_alignment] dropped {live_name}.{live_column}")
