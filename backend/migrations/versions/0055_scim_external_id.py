"""users.external_id for SCIM provisioning (scim-provisioning slice).

Revision ID: 0055_scim_external_id
Revises: 0053_report_schedules
Create Date: 2026-11-26

What this changes
-----------------
* ``users.external_id``: new nullable ``VARCHAR(255)`` + index
  ``ix_users_external_id``. Only SCIM-provisioned rows carry a value;
  the SCIM router treats it as the idempotency key (``externalId``).

Expand-only
-----------
Pure expansion: one nullable column and its index, no existing column
changes, no backfill, no row is touched. The downgrade drops exactly
what the upgrade created.

Idempotency
-----------
Both directions ask the catalog first (the 0037/0047/0050-0053 pattern):
a database the current models already built via ``create_all()`` carries
the column and index, so the upgrade skips them there. Re-running is a
no-op. The migration imports no model.

Postgres cleanliness
--------------------
Plain ``String`` column, no database enum. Index created only when
missing. On SQLite the add/drop column goes through ``batch_alter_table``
(a table rebuild); on Postgres it is a plain ``ADD/DROP COLUMN``.
Downgrade refuses when live values exist rather than dropping data.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0055_scim_external_id"
down_revision = "0054_filing_records"
branch_labels = None
depends_on = None

TABLE = "users"
COLUMN = "external_id"
INDEX = "ix_users_external_id"


def _columns(bind) -> set[str]:
    insp = sa.inspect(bind)
    if TABLE not in set(insp.get_table_names()):
        return set()
    return {c["name"] for c in insp.get_columns(TABLE)}


def _indexes(bind) -> set[str]:
    insp = sa.inspect(bind)
    try:
        return {i.get("name") for i in insp.get_indexes(TABLE)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    if TABLE not in set(sa.inspect(bind).get_table_names()):
        print(f"[0055_scim_external_id] {TABLE} absent; skipping")
        return
    if COLUMN not in _columns(bind):
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table(TABLE) as batch:
                batch.add_column(sa.Column(COLUMN, sa.String(255), nullable=True))
        else:
            op.add_column(TABLE, sa.Column(COLUMN, sa.String(255), nullable=True))
        print(f"[0055_scim_external_id] added {TABLE}.{COLUMN}")
    else:
        print(f"[0055_scim_external_id] {TABLE}.{COLUMN} already present; skipping")
    if INDEX not in _indexes(bind):
        op.create_index(INDEX, TABLE, [COLUMN])
        print(f"[0055_scim_external_id] created index {INDEX}")
    else:
        print(f"[0055_scim_external_id] index {INDEX} already present; skipping")


def downgrade() -> None:
    bind = op.get_bind()
    if TABLE not in set(sa.inspect(bind).get_table_names()):
        print(f"[0055_scim_external_id] {TABLE} absent; skipping")
        return
    if COLUMN in _columns(bind):
        # Check before touching anything: refusing after the index is gone
        # would leave a half-downgraded schema.
        live = bind.execute(
            sa.text(f"SELECT count(*) FROM {TABLE} WHERE {COLUMN} IS NOT NULL")
        ).scalar()
        if live:
            raise RuntimeError(
                f"[0055_scim_external_id] refusing downgrade: {live} row(s) "
                f"carry {TABLE}.{COLUMN}; clear them first"
            )
    if INDEX in _indexes(bind):
        op.drop_index(INDEX, table_name=TABLE)
        print(f"[0055_scim_external_id] dropped index {INDEX}")
    else:
        print(f"[0055_scim_external_id] index {INDEX} already absent; skipping")
    if COLUMN in _columns(bind):
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table(TABLE) as batch:
                batch.drop_column(COLUMN)
        else:
            op.drop_column(TABLE, COLUMN)
        print(f"[0055_scim_external_id] dropped {TABLE}.{COLUMN}")
    else:
        print(f"[0055_scim_external_id] {TABLE}.{COLUMN} already absent; skipping")
