"""scenario_versions: versioning columns for forecast scenarios (AN-05)

Revision ID: 0018_scenario_versions
Revises: 0017_forecast_costs
Create Date: 2026-10-24

Adds four columns to forecast_scenarios so a scenario can be EDITED
under version control and FORKED into an independent lineage:

- version_no: 1, 2, 3... ascending inside one lineage (root_id)
- root_id: self-referential foreign key to forecast_scenarios.id; the
  lineage root is the first version, which points at itself
- source: created | edited | forked - how this version came into being
- forked_from_scenario_id: for forks only, the exact version copied from

Each column is added only when missing (a database built by
``create_all()``, or one that already had a hand-run of this revision,
is adopted without complaint), and legacy rows are backfilled:
version_no = 1 and root_id = id, so every pre-existing scenario becomes
the root of its own one-version lineage.

A unique index over (root_id, version_no) keeps one lineage from
holding two rows with the same version number.

If a later branch (for example AN-06) also ships a revision numbered
0018, the coordinator renumbers at merge time: change DOWN_REVISION
below and nothing else.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_scenario_versions"
DOWN_REVISION = "0017_forecast_costs"
down_revision = DOWN_REVISION
branch_labels = None
depends_on = None

TABLE = "forecast_scenarios"

NEW_COLUMNS = (
    ("version_no", sa.Column("version_no", sa.Integer(), nullable=False, server_default="1")),
    ("source", sa.Column("source", sa.String(20), nullable=False, server_default="created")),
    (
        "forked_from_scenario_id",
        sa.Column(
            "forked_from_scenario_id",
            sa.Integer(),
            sa.ForeignKey(f"{TABLE}.id", ondelete="SET NULL"),
            nullable=True,
        ),
    ),
    # root_id goes last so the other lineage columns exist first; it is
    # backfilled to the row's own id right after.
    (
        "root_id",
        sa.Column(
            "root_id",
            sa.Integer(),
            sa.ForeignKey(f"{TABLE}.id", ondelete="CASCADE"),
            nullable=True,
        ),
    ),
)

UNIQUE_INDEX = "uq_forecast_scenario_root_version"


def _columns(inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def _indexes(inspector, table: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if TABLE not in existing:
        # The scenarios table is created by revision 0015; if even that did
        # not run there is nothing to version yet.
        print(f"[{revision}] {TABLE} missing; nothing to do")
        return

    present = _columns(inspector, TABLE)
    dialect = bind.dialect.name

    for name, column in NEW_COLUMNS:
        if name in present:
            continue
        if dialect == "sqlite":
            # SQLite: add the plain column so ALTER TABLE stays simple;
            # NOT NULL columns carry their server_default, which ALTER
            # TABLE ADD COLUMN accepts, and any constraint is taken in
            # batch mode below, as 0016 does.
            op.add_column(
                TABLE,
                sa.Column(
                    name,
                    column.type,
                    nullable=column.nullable,
                    server_default=column.server_default,
                ),
            )
        else:
            # Oracle and others: the column carries its own inline FK.
            op.add_column(TABLE, column)
        present.add(name)
        print(f"[{revision}] added column {TABLE}.{name}")

    # On SQLite the two self-referential foreign keys were not created by
    # the plain adds above; take them in batch mode, if the dialect
    # reports the table without them.
    if dialect == "sqlite":
        # Reflected unnamed constraints carry no name, so the presence
        # check is on the constrained COLUMNS, not on names.
        fk_cols = {
            tuple(fk.get("constrained_columns") or [])
            for fk in inspector.get_foreign_keys(TABLE)
        }
        with op.batch_alter_table(TABLE) as batch:
            if ("forked_from_scenario_id",) not in fk_cols:
                batch.create_foreign_key(
                    "fk_forecast_scenarios_forked_from",
                    TABLE,
                    ["forked_from_scenario_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if ("root_id",) not in fk_cols:
                batch.create_foreign_key(
                    "fk_forecast_scenarios_root",
                    TABLE,
                    ["root_id"],
                    ["id"],
                    ondelete="CASCADE",
                )

    # Backfill: every scenario that predates versioning is the root (v1)
    # of its own lineage.
    op.execute(sa.text(f"UPDATE {TABLE} SET root_id = id WHERE root_id IS NULL"))
    op.execute(sa.text(f"UPDATE {TABLE} SET version_no = 1 WHERE version_no IS NULL"))
    op.execute(
        sa.text(
            f"UPDATE {TABLE} SET source = 'created' "
            "WHERE source IS NULL OR source = ''"
        )
    )

    if UNIQUE_INDEX not in _indexes(inspector, TABLE):
        op.create_index(UNIQUE_INDEX, TABLE, ["root_id", "version_no"], unique=True)
        print(f"[{revision}] created unique index {UNIQUE_INDEX}")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    if TABLE not in existing:
        print(f"[{revision}] {TABLE} missing; nothing to do")
        return

    if UNIQUE_INDEX in _indexes(inspector, TABLE):
        op.drop_index(UNIQUE_INDEX, table_name=TABLE)
        print(f"[{revision}] dropped index {UNIQUE_INDEX}")

    present = _columns(inspector, TABLE)
    with op.batch_alter_table(TABLE) as batch:
        for name, _column in reversed(NEW_COLUMNS):
            if name in present:
                batch.drop_column(name)
                present.discard(name)
                print(f"[{revision}] dropped column {TABLE}.{name}")
