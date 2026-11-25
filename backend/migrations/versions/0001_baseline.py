"""baseline: adopt the schema that predates Alembic

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-19

Context
-------
This platform was deployed before Alembic existed. The schema was built by
``Base.metadata.create_all()`` at application start, which means a production
database already exists with no migration history.

Adopting Alembic has two halves:

* **A fresh database** runs this migration and gets the inherited schema
  created from the frozen table list in ``migrations/baseline_schema.py``.
  The DDL is generated for the live dialect (Oracle in production) and the
  tables are created in dependency order, which Oracle requires.
* **An existing production database** is *stamped* at this revision rather
  than replaying it — see ``scripts/migrate.py``, which detects the legacy
  schema and stamps instead of creating. The tables are already there, so
  creating them again would fail.

Downgrade drops the frozen tables. That is a destructive operation and is the
correct reverse of a baseline that creates the whole schema; it is never run
against a production database as part of normal operation.
"""
from __future__ import annotations

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from migrations.baseline_schema import create_frozen_schema

    create_frozen_schema(op.get_bind())


def downgrade() -> None:
    from migrations.baseline_schema import drop_frozen_schema

    drop_frozen_schema(op.get_bind())
