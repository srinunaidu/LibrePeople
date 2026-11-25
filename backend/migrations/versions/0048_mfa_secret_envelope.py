"""mfa: widen users.mfa_secret_hash to Text (ENCv1 envelope exceeds VARCHAR(64))

Revision ID: 0048_mfa_secret_envelope
Revises: 0047_expense_category_tenant_code
Create Date: 2026-11-25

What this changes
-----------------
* ``users.mfa_secret_hash``: ``VARCHAR(64)`` -> ``TEXT``.

Why
---
The column was sized for a SHA-256 hex digest (64 chars), but the live
code path (``POST /auth/mfa/enroll`` in ``app/api/v1/endpoints/auth.py``)
stores ``encrypt_secret(package["secret"])`` — the versioned envelope
``ENCv1:<key_id>:<fernet token>``. A 32-char base32 TOTP secret encrypts
to a ~140-char Fernet token, so the stored value is ~150-160 chars
(158 chars with the test key id). On PostgreSQL the ``VARCHAR(64)``
limit is enforced and enrollment fails verbatim with::

    DataError (psycopg.errors.StringDataRightTruncation)
    value too long for type character varying(64)

SQLite does not enforce ``VARCHAR`` lengths, which is why the MFA suites
stayed green there while PG enrollment was broken. The perf-baseline
scratch database carried a manual ``ALTER`` workaround; this revision
makes the fix part of the schema.

Expand-only
-----------
Pure type widening: no row is added, removed, or backfilled; no value is
touched. Nullable-ness is unchanged. Downgrade restores ``VARCHAR(64)``
only when no stored value exceeds 64 chars; otherwise it refuses with a
message rather than truncating secrets.

Idempotency
-----------
The upgrade inspects the live column type first: anything that is not a
length-64 ``VARCHAR`` (fresh ``create_all()`` databases already emit
``TEXT`` from the fixed model, and re-runs see ``TEXT``) is skipped.
The migration imports no model.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0048_mfa_secret_envelope"
down_revision = "0047_expense_category_tenant_code"
branch_labels = None
depends_on = None

TABLE = "users"
COLUMN = "mfa_secret_hash"


def _column_type(bind) -> sa.types.TypeEngine | None:
    """The live type of users.mfa_secret_hash, or None when absent."""
    insp = sa.inspect(bind)
    if TABLE not in set(insp.get_table_names()):
        return None
    for col in insp.get_columns(TABLE):
        if col["name"] == COLUMN:
            return col["type"]
    return None


def upgrade() -> None:
    bind = op.get_bind()
    live = _column_type(bind)
    if live is None:
        print(f"[0048_mfa_secret_envelope] {TABLE}.{COLUMN} absent; skipping")
        return
    if not (isinstance(live, sa.String) and live.length == 64):
        print(
            f"[0048_mfa_secret_envelope] {TABLE}.{COLUMN} is already "
            f"{live!r}; skipping"
        )
        return
    with op.batch_alter_table(TABLE) as batch:
        batch.alter_column(
            COLUMN,
            existing_type=sa.String(64),
            type_=sa.Text(),
            existing_nullable=True,
        )
    print(f"[0048_mfa_secret_envelope] widened {TABLE}.{COLUMN} to TEXT")


def downgrade() -> None:
    bind = op.get_bind()
    live = _column_type(bind)
    if live is None:
        return
    if isinstance(live, sa.String) and live.length == 64:
        print(f"[0048_mfa_secret_envelope] {TABLE}.{COLUMN} already VARCHAR(64)")
        return
    longest = bind.execute(
        sa.text(f"SELECT max(length({COLUMN})) FROM {TABLE}")
    ).scalar()
    if longest and longest > 64:
        raise RuntimeError(
            f"[0048_mfa_secret_envelope] refusing downgrade: {TABLE}.{COLUMN} "
            f"holds a {longest}-char value that VARCHAR(64) would truncate"
        )
    with op.batch_alter_table(TABLE) as batch:
        batch.alter_column(
            COLUMN,
            existing_type=sa.Text(),
            type_=sa.String(64),
            existing_nullable=True,
        )
    print(f"[0048_mfa_secret_envelope] narrowed {TABLE}.{COLUMN} to VARCHAR(64)")
