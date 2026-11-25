"""india aadhaar encryption + identity (india-payroll slice 6)

Revision ID: 0032_india_aadhaar_encryption
Revises: 0031_india_fnf_basic_da
Create Date: 2026-11-18

What this adds
--------------
* ``employees.aadhaar_encrypted`` Text nullable — AES-GCM (Fernet) encrypted
  at rest via app.core.security (PAYROLL §9.3). Raw Aadhaar never stored in
  clear. Nullable so non-Indian tenants and pre-migration rows stay readable.
* ``employees.aadhaar_last4`` String(4) nullable — last 4 digits for masked
  display (** **-****-1234). Stored separately so list/detail can render masked
  without decrypting.
* ``employees.pan_verified_status`` String(20) nullable — stub status for
  verify_pan (always pending_verification in v1).
* ``employees.aadhaar_masked`` String(14) nullable — alias/mirror of last4
  masked form for backwards compat where needed.

Idempotency / downgrade follow 0030/0031 pattern: inspect catalog first,
skip what already exists, drop what this revision added on downgrade.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names, drop_index_if_present

revision = "0032_india_aadhaar_encryption"
down_revision = "0031_india_fnf_basic_da"
branch_labels = None
depends_on = None

EMPLOYEES = "employees"

AADHAAR_LAST4_LEN = 4


def upgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[EMPLOYEES])
    live_table = catalog.table(EMPLOYEES)
    if live_table is None:
        print(f"[0032_india_aadhaar_encryption] {EMPLOYEES} is not present; skipping")
        return

    # aadhaar_encrypted Text nullable
    if catalog.column(live_table, "aadhaar_encrypted") is None:
        op.add_column(
            live_table,
            sa.Column("aadhaar_encrypted", sa.Text(), nullable=True),
        )
        print(f"[0032_india_aadhaar_encryption] added {live_table}.aadhaar_encrypted")
    else:
        print(f"[0032_india_aadhaar_encryption] {live_table}.aadhaar_encrypted already present; skipping")

    # aadhaar_last4 String(4) nullable
    if catalog.column(live_table, "aadhaar_last4") is None:
        op.add_column(
            live_table,
            sa.Column("aadhaar_last4", sa.String(4), nullable=True),
        )
        print(f"[0032_india_aadhaar_encryption] added {live_table}.aadhaar_last4")
    else:
        print(f"[0032_india_aadhaar_encryption] {live_table}.aadhaar_last4 already present; skipping")

    # aadhaar_masked String(14) nullable (display form ****-****-1234 or ** **-****-1234)
    if catalog.column(live_table, "aadhaar_masked") is None:
        op.add_column(
            live_table,
            sa.Column("aadhaar_masked", sa.String(14), nullable=True),
        )
        print(f"[0032_india_aadhaar_encryption] added {live_table}.aadhaar_masked")
    else:
        print(f"[0032_india_aadhaar_encryption] {live_table}.aadhaar_masked already present; skipping")

    # pan_verified_status
    if catalog.column(live_table, "pan_verified_status") is None:
        op.add_column(
            live_table,
            sa.Column("pan_verified_status", sa.String(20), nullable=True),
        )
        print(f"[0032_india_aadhaar_encryption] added {live_table}.pan_verified_status")
    else:
        print(f"[0032_india_aadhaar_encryption] {live_table}.pan_verified_status already present; skipping")

    # uan_verified_status / esi_verified_status / form11_json / nominee_json as generic identity stubs
    if catalog.column(live_table, "uan_verified_status") is None:
        op.add_column(live_table, sa.Column("uan_verified_status", sa.String(20), nullable=True))
        print(f"[0032_india_aadhaar_encryption] added {live_table}.uan_verified_status")
    if catalog.column(live_table, "esi_verified_status") is None:
        op.add_column(live_table, sa.Column("esi_verified_status", sa.String(20), nullable=True))
        print(f"[0032_india_aadhaar_encryption] added {live_table}.esi_verified_status")
    if catalog.column(live_table, "form11_json") is None:
        op.add_column(live_table, sa.Column("form11_json", sa.Text(), nullable=True))
        print(f"[0032_india_aadhaar_encryption] added {live_table}.form11_json")
    if catalog.column(live_table, "nominee_json") is None:
        op.add_column(live_table, sa.Column("nominee_json", sa.Text(), nullable=True))
        print(f"[0032_india_aadhaar_encryption] added {live_table}.nominee_json")


def downgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[EMPLOYEES])
    live_table = catalog.table(EMPLOYEES)
    if live_table is None:
        print(f"[0032_india_aadhaar_encryption] {EMPLOYEES} is not present; skipping")
        return
    for col in ("aadhaar_encrypted", "aadhaar_last4", "aadhaar_masked", "pan_verified_status", "uan_verified_status", "esi_verified_status", "form11_json", "nominee_json"):
        live_column = catalog.column(live_table, col)
        if live_column is None:
            print(f"[0032_india_aadhaar_encryption] {live_table}.{col} already absent; skipping")
            continue
        inspector = sa.inspect(bind)
        for index in inspector.get_indexes(live_table):
            column_names = [str(c).casefold() for c in index.get("column_names") or []]
            if live_column.casefold() in column_names:
                drop_index_if_present(index["name"], live_table)
        op.drop_column(live_table, live_column)
        print(f"[0032_india_aadhaar_encryption] dropped {live_table}.{col}")
