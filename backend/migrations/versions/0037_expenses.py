"""expense categories, claims and receipts (LP-EXP-001+002)

Revision ID: 0037_expenses
Revises: 0036_legal_entities
Create Date: 2026-11-22

What this adds
--------------
* ``expense_categories`` — the reimbursable category master: unique natural
  key ``code``, name, description, ``is_active`` and the shared ``tenant_id``
  discriminator, plus the composite ``ix_expense_categories_tenant_id_id``
  index the other masters carry.
* ``expense_claims`` — one reimbursable expense: employee, category,
  expense date, ``amount`` as ``Numeric(12, 2)``, currency, claim ``status``
  (``DRAFT``/``SUBMITTED``/``L1_APPROVED``/``APPROVED``/``REJECTED``) and
  ``payment_status`` (``UNPAID``/``PAID``), with the actor/at columns each
  state move records.
* ``expense_receipts`` — receipt files attached to a claim: the claim, the
  opaque storage key (unique), file name, content type and size. The bytes
  live in object storage; the download route authenticates.

Expand-only
-----------
Pure expansion. It creates three tables and their indexes and changes no
column of an existing table, so it applies cleanly on a database that
already holds data. The downgrade removes exactly what the upgrade
created: each table only when present, each index only when there.

Idempotency
-----------
Both directions ask the catalog first (the 0036 pattern): a database the
current models already built via ``create_all()`` carries the tables, so
the upgrade skips them there. Re-running is a no-op.

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

revision = "0037_expenses"
down_revision = "0036_legal_entities"
branch_labels = None
depends_on = None

CATEGORIES = "expense_categories"
CLAIMS = "expense_claims"
RECEIPTS = "expense_receipts"

CATEGORY_INDEXES = (
    ("ix_expense_categories_tenant_id_id", (CATEGORIES, ("tenant_id", "id"))),
)

CLAIM_INDEXES = (
    ("ix_expense_claims_tenant_id", (CLAIMS, ("tenant_id",))),
    ("ix_expense_claims_employee_id", (CLAIMS, ("employee_id",))),
    ("ix_expense_claims_category_id", (CLAIMS, ("category_id",))),
    ("ix_expense_claims_tenant_id_id", (CLAIMS, ("tenant_id", "id"))),
)

RECEIPT_INDEXES = (
    ("ix_expense_receipts_tenant_id", (RECEIPTS, ("tenant_id",))),
    ("ix_expense_receipts_claim_id", (RECEIPTS, ("claim_id",))),
    ("ix_expense_receipts_tenant_id_id", (RECEIPTS, ("tenant_id", "id"))),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    catalog = catalog_names(op.get_bind(), tables=[CATEGORIES, CLAIMS, RECEIPTS])

    if catalog.table(CATEGORIES) is None:
        op.create_table(
            CATEGORIES,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", name="uq_expense_categories_code"),
        )
        print(f"[0037_expenses] created {CATEGORIES}")
    else:
        print(f"[0037_expenses] {CATEGORIES} already present; skipping")

    if catalog.table(CLAIMS) is None:
        op.create_table(
            CLAIMS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("expense_categories.id"), nullable=False),
            sa.Column("expense_date", sa.Date(), nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
            sa.Column("payment_status", sa.String(10), nullable=False, server_default="UNPAID"),
            sa.Column("submitted_by", sa.Integer(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("l1_approved_by", sa.Integer(), nullable=True),
            sa.Column("l1_approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_by", sa.Integer(), nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("paid_by", sa.Integer(), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        print(f"[0037_expenses] created {CLAIMS}")
    else:
        print(f"[0037_expenses] {CLAIMS} already present; skipping")

    if catalog.table(RECEIPTS) is None:
        op.create_table(
            RECEIPTS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("claim_id", sa.Integer(), sa.ForeignKey("expense_claims.id"), nullable=False),
            sa.Column("storage_key", sa.String(500), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("content_type", sa.String(120), nullable=False, server_default="application/octet-stream"),
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("uploaded_by", sa.Integer(), nullable=True),
            sa.Column(
                "uploaded_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("storage_key", name="uq_expense_receipts_storage_key"),
        )
        print(f"[0037_expenses] created {RECEIPTS}")
    else:
        print(f"[0037_expenses] {RECEIPTS} already present; skipping")

    for name, (table, columns) in CATEGORY_INDEXES + CLAIM_INDEXES + RECEIPT_INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0037_expenses] created index {name}")
        else:
            print(f"[0037_expenses] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in reversed(RECEIPT_INDEXES + CLAIM_INDEXES + CATEGORY_INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0037_expenses] dropped index {name}")

    existing = _tables()
    for table in (RECEIPTS, CLAIMS, CATEGORIES):
        if table in existing:
            op.drop_table(table)
            print(f"[0037_expenses] dropped {table}")
        else:
            print(f"[0037_expenses] {table} already absent; skipping")
