"""Integrity quarantine (NFR-014 / migration 0043).

Every row the 0043 backfill had to touch before the database could be
constrained is recorded here first: which table, which primary key, which
constraint it violated, and the pre-fix values as JSON. The quarantine is
append-only evidence — the downgrade of 0043 deliberately retains it —
so a finance or HR review can always reconstruct what moved and why.
Nothing is silently discarded: a repaired row always has its old state
in this table.
"""

from sqlalchemy import DateTime, Identity, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class IntegrityQuarantine(Base):
    """One repaired (or removed) row per (table, primary key, reason)."""

    __tablename__ = "integrity_quarantine"
    __table_args__ = (
        UniqueConstraint(
            "table_name", "row_pk", "reason", name="uq_quarantine_row_reason"
        ),
        Index("ix_quarantine_table", "table_name"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    table_name: Mapped[str] = mapped_column(String(60), nullable=False)
    row_pk: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(60), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
