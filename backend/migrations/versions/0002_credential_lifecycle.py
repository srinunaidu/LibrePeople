"""credential lifecycle: refresh token table and user credential columns

Revision ID: 0002_credential_lifecycle
Revises: 0001_baseline
Create Date: 2026-10-19

What this adds
--------------
* ``refresh_tokens`` — storage for rotating, revocable sessions.
* ``users.must_change_password`` — forces an account to replace an
  administrator-set or bootstrapped password before it can use the API.
* ``users.password_changed_at`` — when the password last changed.
* ``users.failed_login_count`` and ``users.locked_until`` — per-account
  lockout, complementing the per-IP rate limit.
* ``users.password_history`` — the last N password hashes, so reuse can be
  refused.

Why every step is guarded
--------------------------
This migration runs against two different starting points:

* a **fresh** database, where the baseline created the tables from the
  *current* model metadata, so the ``users`` columns already exist; and
* the **existing production** database, which was stamped at the baseline
  because its schema predates Alembic, so the ``users`` columns do not
  exist.

A plain ``add_column`` would fail on the first and do nothing on the second.
Each step therefore checks the live schema first and acts only when the change
is actually needed. The check is cheap (a single catalogue query) and the
migration is safe to run against either starting point, and to re-run.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import create_index_if_missing, drop_index_if_present

revision = "0002_credential_lifecycle"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def _table_exists(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _column_names(inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # --- refresh_tokens ---------------------------------------------------
    if not _table_exists(inspector, "refresh_tokens"):
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("family_id", sa.String(length=64), nullable=False),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_reason", sa.String(length=60), nullable=True),
            sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
            sa.Column("ip_hash", sa.String(length=64), nullable=True),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], name="fk_refresh_tokens_user_id"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash", name="uq_refresh_token_hash"),
        )
        # The index is created only when its column list is free. An
        # index, a unique constraint and the primary key each occupy a
        # column list, and Oracle refuses a second index over a column
        # list that is taken (ORA-01408).
        for name, columns in (
            ("ix_refresh_tokens_user_id", ("user_id",)),
            ("ix_refresh_tokens_family_id", ("family_id",)),
        ):
            if create_index_if_missing(name, "refresh_tokens", list(columns)):
                print(f"[0002_credential_lifecycle] created index {name}")

    # --- users credential columns ----------------------------------------
    if not _table_exists(inspector, "users"):
        return

    existing = _column_names(inspector, "users")

    if "must_change_password" not in existing:
        op.add_column(
            "users",
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "password_changed_at" not in existing:
        op.add_column(
            "users",
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "failed_login_count" not in existing:
        op.add_column(
            "users",
            sa.Column(
                "failed_login_count",
                sa.Integer(),
                nullable=False,
                # sa.text() so it renders as a numeric literal. A bare string
                # would render as a quoted '0', which Oracle would have to
                # convert implicitly.
                server_default=sa.text("0"),
            ),
        )
    if "locked_until" not in existing:
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )
    if "password_history" not in existing:
        op.add_column(
            "users",
            sa.Column("password_history", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "users"):
        existing = _column_names(inspector, "users")
        for column in (
            "password_history",
            "locked_until",
            "failed_login_count",
            "password_changed_at",
            "must_change_password",
        ):
            if column in existing:
                op.drop_column("users", column)

    if _table_exists(inspector, "refresh_tokens"):
        # Only the indexes that are there are dropped: an index the
        # upgrade skipped is not there to be dropped, and dropping it
        # anyway fails with ORA-01418.
        for name in ("ix_refresh_tokens_family_id", "ix_refresh_tokens_user_id"):
            if drop_index_if_present(name, "refresh_tokens"):
                print(f"[0002_credential_lifecycle] dropped index {name}")
        op.drop_table("refresh_tokens")
