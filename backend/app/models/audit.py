from sqlalchemy import String, Integer, DateTime, Text, Identity, event
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base


class AuditLog(Base):
    """Immutable, hash-chained trail of who did what, used for evidence.

    The chain columns are filled by :func:`app.core.audit_chain.append_entry`;
    a row is never written without them. ``prev_hash`` is the ``entry_hash``
    of the previous entry (the genesis hash for the first), and
    ``entry_hash`` is the SHA-256 of the canonical payload documented in
    :mod:`app.core.audit_chain`. The append-only triggers installed by the
    migration refuse an update or a delete of a row.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The tenant the action was attributed to, resolved from the request's
    # JWT ``tenant`` claim (fallback ``tid``) or verified hostname mapping.
    # Nullable: rows written before this column existed, and actions taken
    # outside a request (a seed, a job), carry none. It is never defaulted
    # to a real tenant — an unresolvable tenant fails closed upstream.
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    #: The break-glass grant that authorized the action, if any. Nullable for
    #: ordinary (non break-glass) writes.
    break_glass_grant_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The SHA-256 of the client address that performed the action, matching
    # the refresh-token convention. Nullable: rows written before this column
    # existed, and actions taken outside a request (a seed, a job), carry
    # none, and a missing digest means "not recorded", not "no address".
    source_ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # The chain. Not null after the contract revision: every row is hashed
    # when it is written, and the verification command fails on a row that
    # is not.
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditChainHead(Base):
    """The one row that names the end of the audit chain.

    A single row (``id = 1``) holds the hash of the newest entry. It exists
    so that (a) two writers cannot fork the chain — the writer takes the
    head with a compare-and-set, and a stale writer retries rather than
    branching — and (b) the verification command can detect entries removed
    from the tail, which a chain walk alone cannot see.

    It is not protected by the append-only trigger because the writer has to
    update it. Anchoring the head somewhere outside the database is what
    makes a rewrite of the whole chain detectable; the verification command
    prints it for exactly that purpose.
    """

    __tablename__ = "audit_chain_head"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    head_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    head_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


@event.listens_for(AuditChainHead.__table__, "after_create")
def _seed_chain_head(target, connection, **kwargs) -> None:
    """Give a freshly created chain table its genesis row.

    ``create_all()`` is used by the test suites, and the migration seeds the
    row itself for a database that already exists. Without the row the first
    writer has nothing to compare-and-set against.
    """
    from app.core.audit_chain import GENESIS_HASH

    connection.execute(
        target.insert().values(id=1, head_hash=GENESIS_HASH, head_id=None)
    )
