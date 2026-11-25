"""import_dry_runs: the table that holds a validated import waiting to be committed

Revision ID: 0007_import_dry_runs
Revises: 0006_schema_alignment
Create Date: 2026-10-21

Why this table exists
---------------------
The confirmation token used to live in a module-level dictionary in the
endpoint process. That store was unbounded, it did not survive a restart,
and it was not scoped to the user who asked for the dry run — one operator
could commit another operator's import.

A row in this table fixes all three:

* the token is unique, so a token cannot be used twice;
* the row records the user who asked for the dry run, so only that user can
  commit it;
* the row records the hash of the dry-run *outcome*, so the commit can
  check that the outcome the operator was shown is still the outcome.

The uploaded file itself is kept in object storage, and the row records
where. The file is deleted when the import is committed, or when its
retention period expires.

Expand-then-contract
---------------------
This revision is pure expansion: it adds a table and its indexes, and it
changes nothing that exists. Nothing reads the table until the code that
does is deployed, so this can be applied before the release that uses it.
The downgrade drops the table, which loses the pending dry runs — the
correct reverse of adding one, and never run against a production database
as part of normal operation.

Oracle
------
The primary key uses ``Identity()`` rather than ``autoincrement``: on
Oracle a plain autoincrement integer primary key raises ORA-01408 ("column
may not be implicitly specified") and the table is silently never created.

The revision is re-runnable
---------------------------
The first version of this revision created the table with the ``token``
column already unique, and then created a *second* unique index over the
same column list. Oracle refuses that with ORA-01408 ("such column list
already indexed"), whatever the two indexes are called, and the deployment
of ``main`` failed with exactly that error.

Oracle commits DDL implicitly, so the ``CREATE TABLE`` of the failed run
succeeded and only the index was refused. The revision was therefore never
stamped, and the next run of it began with a table that was already there.

This revision is written for that situation:

* a table that is already there is **adopted**, not recreated, and the
  columns that are missing from it are added;
* an index is created only when its **column list** is not already indexed
  — by an index, by a unique constraint, or by the primary key — because
  Oracle refuses a second index over a column list that is already taken;
* the ``token`` column carries no unique constraint of its own, so the
  uniqueness of the token is the unique index this revision creates and
  the two can never occupy the same column list. A table that already has
  the uniqueness — from a unique constraint, or from an index — is left
  alone, and the token stays unique either way.

The downgrade
-------------
The downgrade removes exactly what the upgrade created:

* the indexes this revision created, and only those — their names are the
  revision's own, so an index that belongs to the models is never touched;
* the table, but only if this revision created it. The marker is the
  primary key constraint: this revision names it, and the models do not
  name theirs, so a table that carries the name is one this revision
  built. A table that was adopted is left exactly as it was found.

A table left behind by the *failed* run of the earlier version of this
revision carries no marker either — it was created with an unnamed primary
key — so it is left in place rather than dropped on the assumption that it
is empty. It holds no rows: the feature has never been used in production.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_import_dry_runs"
down_revision = "0006_schema_alignment"
branch_labels = None
depends_on = None


TABLE = "import_dry_runs"

#: The name of the primary key constraint this revision creates.
#:
#: It is the marker that says "this revision created this table". The
#: models do not name their primary key, so a table that carries this name
#: is one this revision built, and only such a table is dropped by the
#: downgrade. The revision number is part of the name so that no naming
#: convention applied to the models can produce it by accident.
PRIMARY_KEY_NAME = "pk_0007_import_dry_runs"

COLUMNS = [
    sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
    # The token is unique, and the uniqueness is the unique index below
    # rather than a constraint on the column. A constraint and an index
    # over the same column list are what Oracle refuses with ORA-01408, so
    # the column carries one of them and not both.
    sa.Column("token", sa.String(64), nullable=False),
    sa.Column("entity", sa.String(40), nullable=False),
    sa.Column("file_hash", sa.String(64), nullable=False),
    sa.Column("result_hash", sa.String(64), nullable=False),
    sa.Column("storage_key", sa.String(500), nullable=False),
    sa.Column("file_name", sa.String(255), nullable=True),
    sa.Column("user_id", sa.Integer(), nullable=True),
    sa.Column("tenant_id", sa.String(60), nullable=False),
    sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
    sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("create_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("update_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("reject_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("upload_expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("failure_reason", sa.Text(), nullable=True),
]

#: The indexes the queries this table serves need.
#:
#: ``token`` is unique — it is the lookup key for a commit — and every
#: other index is on a column that is filtered or sorted: the entity, the
#: two hashes, the owner, the tenant, the status and the two expiries.
#:
#: The names are the revision's own (``ix_dryrun_``), not the names the
#: models would generate (``ix_import_dry_runs_``). A name that no
#: model-generated index can have is what lets the downgrade drop exactly
#: the indexes this revision created and never one that belongs to the
#: model. The same reasoning is used by ``0008_fk_indexes``, which names
#: its indexes ``ix_fk_*``.
INDEXES = [
    ("ix_dryrun_token", ["token"], True),
    ("ix_dryrun_entity", ["entity"], False),
    ("ix_dryrun_file_hash", ["file_hash"], False),
    ("ix_dryrun_result_hash", ["result_hash"], False),
    ("ix_dryrun_user_id", ["user_id"], False),
    ("ix_dryrun_tenant_id", ["tenant_id"], False),
    ("ix_dryrun_status", ["status"], False),
    ("ix_dryrun_expires_at", ["expires_at"], False),
    ("ix_dryrun_upload_expires_at", ["upload_expires_at"], False),
]


def _live_table(inspector) -> str | None:
    """The name the catalog uses for the table, or None if it is absent."""
    for name in inspector.get_table_names():
        if name.upper() == TABLE.upper():
            return name
    return None


def _index_names(inspector, table: str) -> set[str]:
    return {
        str(index["name"]).casefold()
        for index in inspector.get_indexes(table)
        if index.get("name")
    }


def _indexed_column_lists(inspector, table: str) -> set[tuple[str, ...]]:
    """Every column list the database already indexes.

    An index, a unique constraint and the primary key all occupy a column
    list in the database. Oracle refuses a second index over a column list
    that is already indexed (ORA-01408), whatever the two indexes are
    called, so the revision has to know about all three of them before it
    creates one.
    """
    lists: set[tuple[str, ...]] = set()

    def remember(columns) -> None:
        key = tuple(str(name).casefold() for name in columns or [])
        if key:
            lists.add(key)

    for index in inspector.get_indexes(table):
        remember(index.get("column_names"))
    for constraint in inspector.get_unique_constraints(table):
        remember(constraint.get("column_names"))
    primary_key = inspector.get_pk_constraint(table) or {}
    remember(primary_key.get("constrained_columns"))
    return lists


def _uniquely_indexed_column_lists(inspector, table: str) -> set[tuple[str, ...]]:
    """The column lists a unique structure already indexes.

    A unique constraint and a unique index both refuse a duplicate value,
    so a column list in here is already unique and needs no unique index.
    """
    lists: set[tuple[str, ...]] = set()

    def remember(columns) -> None:
        key = tuple(str(name).casefold() for name in columns or [])
        if key:
            lists.add(key)

    for index in inspector.get_indexes(table):
        if index.get("unique"):
            remember(index.get("column_names"))
    for constraint in inspector.get_unique_constraints(table):
        remember(constraint.get("column_names"))
    return lists


def _plain_column(column: sa.Column) -> sa.Column:
    """A copy of the column that carries no constraint of its own.

    The column is added to a table that already exists. The uniqueness of
    the token is not part of the column — it is the unique index the
    revision creates — and a unique constraint cannot be added to an
    existing table on every dialect, so the column is added plain.
    """
    identity = None
    if column.identity is not None:
        identity = sa.Identity(always=column.identity.always)
    return sa.Column(
        column.name,
        column.type,
        nullable=column.nullable,
        server_default=column.server_default,
        identity=identity,
    )


def _created_by_this_revision(inspector, table: str) -> bool:
    """Whether this revision created the table.

    The primary key constraint is the marker: this revision names it, and
    the models do not name theirs. A table that carries the name is one
    this revision built, and only such a table is dropped by the downgrade.
    """
    primary_key = inspector.get_pk_constraint(table) or {}
    name = str(primary_key.get("name") or "").casefold()
    return name == PRIMARY_KEY_NAME.casefold()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    live = _live_table(inspector)

    if live is None:
        op.create_table(
            TABLE,
            *COLUMNS,
            sa.PrimaryKeyConstraint("id", name=PRIMARY_KEY_NAME),
        )
        live = TABLE
        print(f"[0007_import_dry_runs] created {TABLE}")
    else:
        # The table is already there — a database created by
        # ``create_all()`` against the new model, or an earlier run of
        # this revision that failed after the table was created. Bring it
        # up to the shape the model expects, and never fail on what is
        # already there.
        present = {
            str(column["name"]).casefold()
            for column in inspector.get_columns(live)
        }
        for column in COLUMNS:
            if column.name.casefold() in present:
                continue
            op.add_column(live, _plain_column(column))
            print(f"[0007_import_dry_runs] added missing column {live}.{column.name}")

    inspector = sa.inspect(bind)
    live = _live_table(inspector) or TABLE
    indexed = _indexed_column_lists(inspector, live)
    unique_lists = _uniquely_indexed_column_lists(inspector, live)

    for name, columns, unique in INDEXES:
        key = tuple(column.casefold() for column in columns)
        if key in indexed:
            # The column list is already indexed — by a unique constraint,
            # by another index, or by the primary key. Oracle refuses a
            # second index over the same column list (ORA-01408), so this
            # index is not created. The uniqueness it would have given is
            # already there when a unique constraint covers the list.
            if unique and key not in unique_lists:
                print(
                    f"[0007_import_dry_runs] {live}({', '.join(columns)}) is "
                    f"indexed but not uniquely; {name} was not created"
                )
            else:
                print(
                    f"[0007_import_dry_runs] {live}({', '.join(columns)}) is "
                    f"already indexed; {name} was not created"
                )
            continue
        op.create_index(name, live, columns, unique=unique)
        indexed.add(key)
        if unique:
            unique_lists.add(key)
        print(f"[0007_import_dry_runs] created index {name}")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    live = _live_table(inspector)
    if live is None:
        print("[0007_import_dry_runs] nothing to drop")
        return

    # Only the indexes this revision created are dropped. Their names are
    # the revision's own, so an index that belongs to the model — or to
    # anybody else — is never touched.
    present_indexes = _index_names(inspector, live)
    for name, _columns, _unique in reversed(INDEXES):
        if name.casefold() in present_indexes:
            op.drop_index(name, table_name=live)
            print(f"[0007_import_dry_runs] dropped index {name}")

    # The table is dropped only when this revision created it. A table
    # that was adopted is left exactly as it was found.
    if _created_by_this_revision(inspector, live):
        # SQLite refuses to drop a table that a foreign key refers to, and
        # the batch mode rebuilds the table instead of altering it. There
        # is no foreign key here, so the plain statement is correct on
        # both.
        op.drop_table(live)
        print(f"[0007_import_dry_runs] dropped {live}")
    else:
        print(
            f"[0007_import_dry_runs] {live} was not created by this "
            "revision; leaving it in place"
        )
