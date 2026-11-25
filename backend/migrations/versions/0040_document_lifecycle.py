"""versioned documents, acknowledgements and access logs (LP-DOC-002)

Revision ID: 0040_document_lifecycle
Revises: 0039_custom_fields
Create Date: 2026-11-22

What this adds
--------------
* ``document_versions`` — one immutable row per upload of an employee
  document: (document_id, version_no) is unique, so the rows behind a
  document are its ordered download history.
* ``document_acks`` — one acknowledgement per (document, account): the
  unique backstop ``uq_docack_doc_user`` keeps "I have read this" a
  single accountable event.
* ``document_access_logs`` — one row per authenticated download served
  by ``GET /api/v1/files/{path}`` for a key that belongs to a document.
* Three columns on ``employee_documents``: ``storage_key`` (the opaque
  key inside the storage backend the files route serves), ``current_version``
  (the newest version number, starting at 1) and ``retention_until``
  (the keep-until date once the document is Expired).

Expand-only
-----------
Pure expansion. It creates three tables and adds three columns, and it
changes no existing column of any existing table, so it applies cleanly
on a database that already holds documents. ``current_version`` is added
NOT NULL with a server default of 1, which backfills the rows written
before versions existed; ``storage_key`` and ``retention_until`` are
nullable, derived or set on first touch. The downgrade removes exactly
what the upgrade created.

Idempotency
-----------
Both directions ask the catalog first (the 0036/0037/0039 pattern): a
database the current models already built via ``create_all()`` carries
the tables and columns, so the upgrade skips them there. Re-running is
a no-op.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0040_document_lifecycle"
down_revision = "0039_custom_fields"
branch_labels = None
depends_on = None

VERSIONS = "document_versions"
ACKS = "document_acks"
ACCESS_LOGS = "document_access_logs"
DOCUMENTS = "employee_documents"

NEW_TABLES: tuple[str, ...] = (VERSIONS, ACKS, ACCESS_LOGS)

INDEXES: tuple[tuple[str, str, list[str]], ...] = (
    ("ix_docver_doc_id", VERSIONS, ["document_id"]),
    ("ix_docack_doc_id", ACKS, ["document_id"]),
    ("ix_doclog_doc_id", ACCESS_LOGS, ["document_id"]),
)

NEW_COLUMNS: tuple[tuple[str, sa.Column], ...] = (
    (DOCUMENTS, sa.Column("storage_key", sa.String(500), nullable=True)),
    (
        DOCUMENTS,
        sa.Column(
            "current_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    ),
    (DOCUMENTS, sa.Column("retention_until", sa.Date(), nullable=True)),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    catalog = catalog_names(op.get_bind(), tables=list(NEW_TABLES))

    if catalog.table(VERSIONS) is None:
        op.create_table(
            VERSIONS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column(
                "document_id",
                sa.Integer(),
                sa.ForeignKey("employee_documents.id"),
                nullable=False,
            ),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("storage_key", sa.String(500), nullable=True),
            sa.Column("storage_url", sa.String(500), nullable=False),
            sa.Column("uploaded_by", sa.String(100), nullable=True),
            sa.Column(
                "uploaded_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "document_id", "version_no", name="uq_docver_doc_ver"
            ),
        )
        print(f"[0040_document_lifecycle] created {VERSIONS}")
    else:
        print(f"[0040_document_lifecycle] {VERSIONS} already present; skipping")

    if catalog.table(ACKS) is None:
        op.create_table(
            ACKS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column(
                "document_id",
                sa.Integer(),
                sa.ForeignKey("employee_documents.id"),
                nullable=False,
            ),
            sa.Column("acknowledged_by", sa.String(100), nullable=False),
            sa.Column(
                "acknowledged_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "document_id", "acknowledged_by", name="uq_docack_doc_user"
            ),
        )
        print(f"[0040_document_lifecycle] created {ACKS}")
    else:
        print(f"[0040_document_lifecycle] {ACKS} already present; skipping")

    if catalog.table(ACCESS_LOGS) is None:
        op.create_table(
            ACCESS_LOGS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column(
                "document_id",
                sa.Integer(),
                sa.ForeignKey("employee_documents.id"),
                nullable=False,
            ),
            sa.Column("accessed_by", sa.String(100), nullable=False),
            sa.Column(
                "accessed_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        print(f"[0040_document_lifecycle] created {ACCESS_LOGS}")
    else:
        print(f"[0040_document_lifecycle] {ACCESS_LOGS} already present; skipping")

    for name, table, columns in INDEXES:
        if create_index_if_missing(name, table, columns):
            print(f"[0040_document_lifecycle] created index {name}")
        else:
            print(f"[0040_document_lifecycle] index {name} already present; skipping")

    existing_columns: dict[str, set[str]] = {}
    inspector = sa.inspect(op.get_bind())
    for table, _column in NEW_COLUMNS:
        if table not in existing_columns:
            try:
                existing_columns[table] = {
                    column["name"] for column in inspector.get_columns(table)
                }
            except sa.exc.NoSuchTableError:
                existing_columns[table] = set()
    for table, column in NEW_COLUMNS:
        if column.name in existing_columns.get(table, set()):
            print(
                f"[0040_document_lifecycle] {table}.{column.name} "
                "already present; skipping"
            )
            continue
        op.add_column(table, column)
        print(f"[0040_document_lifecycle] added {table}.{column.name}")


def downgrade() -> None:
    for name, table, _columns in reversed(INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0040_document_lifecycle] dropped index {name}")

    existing = _tables()
    for table in reversed(NEW_TABLES):
        if table in existing:
            op.drop_table(table)
            print(f"[0040_document_lifecycle] dropped {table}")
        else:
            print(f"[0040_document_lifecycle] {table} already absent; skipping")

    inspector = sa.inspect(op.get_bind())
    for table, column in reversed(NEW_COLUMNS):
        try:
            names = {c["name"] for c in inspector.get_columns(table)}
        except sa.exc.NoSuchTableError:
            names = set()
        if column.name in names:
            op.drop_column(table, column.name)
            print(f"[0040_document_lifecycle] dropped {table}.{column.name}")
        else:
            print(
                f"[0040_document_lifecycle] {table}.{column.name} "
                "already absent; skipping"
            )
