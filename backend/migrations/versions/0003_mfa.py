"""mfa: add multi-factor authentication fields to users

Revision ID: 0003_mfa
Revises: 0002_credential_lifecycle
Create Date: 2026-10-20

What this adds
--------------
* ``users.mfa_enabled`` — whether MFA is active for the account.
* ``users.mfa_secret_hash`` — SHA-256 hash of the TOTP secret (never the
  plaintext secret).
* ``users.mfa_enrolled_at`` — when MFA was enrolled.
* ``users.recovery_codes_hash`` — bcrypt hashes of single-use recovery codes,
  as a JSON array.

Guarded like the previous credential migration: each column is added only
when it does not already exist, so the migration is safe against both fresh
databases and legacy databases stamped at an earlier revision.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_mfa"
down_revision = "0002_credential_lifecycle"
branch_labels = None
depends_on = None


def _column_names(inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_names(inspector, "users"):
        return

    existing = _column_names(inspector, "users")

    if "mfa_enabled" not in existing:
        op.add_column(
            "users",
            sa.Column(
                "mfa_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "mfa_secret_hash" not in existing:
        op.add_column(
            "users",
            sa.Column("mfa_secret_hash", sa.String(length=64), nullable=True),
        )
    if "mfa_enrolled_at" not in existing:
        op.add_column(
            "users",
            sa.Column("mfa_enrolled_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "recovery_codes_hash" not in existing:
        op.add_column(
            "users",
            sa.Column("recovery_codes_hash", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_names(inspector, "users"):
        return

    existing = _column_names(inspector, "users")
    for column in (
        "recovery_codes_hash",
        "mfa_enrolled_at",
        "mfa_secret_hash",
        "mfa_enabled",
    ):
        if column in existing:
            op.drop_column("users", column)
