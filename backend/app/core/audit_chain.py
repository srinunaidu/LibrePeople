"""The audit hash chain: canonical form, append, verify, append-only guards.

Why a chain
-----------
The audit trail is the evidence base for every other claim the product makes.
Ordinary rows cannot distinguish an honest record from one that was edited in
place. Each entry therefore carries the hash of the entry before it, so
changing one row breaks the link at that row, and removing one breaks it at
the next.

The canonical form (version ``karmathy-audit-v1``)
--------------------------------------------------
``entry_hash`` is the lowercase hex SHA-256 of this byte string::

    karmathy-audit-v1\\n
    {"action":...,"actor_id":...,"actor_name":...,"created_at":...,
     "details":...,"entity_id":...,"entity_type":...,"prev_hash":...,
     "source_ip_hash":...,"version":"karmathy-audit-v1"}

where the JSON is serialised with ``sort_keys=True``,
``separators=(",", ":")`` and ``ensure_ascii=False``, encoded UTF-8.
``created_at`` is the UTC instant formatted with
``isoformat(timespec="microseconds")`` (for example
``2026-10-26T03:36:11.023294+00:00``); a timestamp read back without a zone is
taken to be UTC.

The row ``id`` is deliberately **not** in the payload: the database assigns it
after the hash is computed, and the order of the chain is established by
``prev_hash``, not by the primary key.

What the chain does and does not prove
--------------------------------------
* It detects an edited or removed row, and the append-only triggers refuse an
  ``UPDATE``/``DELETE`` from the application.
* It does **not** stop someone who can rewrite every row and the head: a
  plain hash chain needs no secret, so a full rewrite recomputes every hash.
  That is why the verification command prints the head hash — recording it
  outside the database (a ticket, a report, a second system) is what turns
  tamper *evidence* into tamper *detection* against a determined insider.

Concurrency
-----------
The head is taken with a compare-and-set on ``audit_chain_head.head_hash``,
not read-then-incremented. Two writers that saw the same head cannot both
win: the second update matches no row and the writer retries on top of the
new head, so the chain never forks. The cost is that an audited write holds
the head row until it commits; audited writes are therefore serialised at the
head, which is the price of a single chain.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.models.audit import AuditChainHead, AuditLog

#: The ``prev_hash`` of the first entry. Sixty-four zeros, a value no
#: SHA-256 digest can take in practice.
GENESIS_HASH = "0" * 64

#: The canonical-form version. Part of the hashed payload, so a future
#: change of form is a new version rather than a silent reinterpretation of
#: the old rows.
CHAIN_VERSION = "karmathy-audit-v1"

#: How many times an append retries when another writer moved the head. A
#: writer is only refused after this many lost races, which would mean the
#: head moved this many times inside one transaction.
APPEND_RETRIES = 16


def normalise_timestamp(value: Any) -> str:
    """The canonical text of a timestamp: a UTC instant, microsecond precision."""
    if isinstance(value, str):
        text_value = value.strip().replace(" ", "T", 1)
        if text_value.endswith("Z"):
            text_value = text_value[:-1] + "+00:00"
        value = datetime.fromisoformat(text_value)
    if not isinstance(value, datetime):
        raise TypeError(f"not a timestamp: {type(value).__name__}")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def canonical_payload(
    *,
    prev_hash: str,
    actor_id: int | None,
    actor_name: str | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: str | None,
    source_ip_hash: str | None,
    created_at: Any,
) -> bytes:
    """The exact bytes an entry hash is taken over. See the module docstring."""
    payload = {
        "action": action,
        "actor_id": actor_id,
        "actor_name": actor_name,
        "created_at": normalise_timestamp(created_at),
        "details": details,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "prev_hash": prev_hash,
        "source_ip_hash": source_ip_hash,
        "version": CHAIN_VERSION,
    }
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return f"{CHAIN_VERSION}\n{body}".encode("utf-8")


def compute_entry_hash(**fields: Any) -> str:
    """The SHA-256 of the canonical payload for one entry."""
    return hashlib.sha256(canonical_payload(**fields)).hexdigest()


def _read_head(db: Session) -> tuple[str, int | None]:
    """The current head hash and the id of the entry it names."""
    row = db.execute(
        select(AuditChainHead.head_hash, AuditChainHead.head_id).where(
            AuditChainHead.id == 1
        )
    ).first()
    if row is None:
        return GENESIS_HASH, None
    return row[0] or GENESIS_HASH, row[1]


def _ensure_head(db: Session) -> None:
    """Create the head row if a database predates the seeding.

    The migration and ``create_all()`` both seed it; this is the fallback for
    a database built by hand. A savepoint contains the insert so that losing
    the race to another writer does not abort the caller's transaction.
    """
    if db.execute(
        select(AuditChainHead.id).where(AuditChainHead.id == 1)
    ).first() is not None:
        return
    nested = db.begin_nested()
    try:
        db.execute(
            AuditChainHead.__table__.insert().values(
                id=1, head_hash=GENESIS_HASH, head_id=None
            )
        )
        nested.commit()
    except Exception:  # noqa: BLE001 - the other writer created it
        nested.rollback()


def _compare_and_set_head(db: Session, expected: str, new_hash: str) -> bool:
    """Move the head from ``expected`` to ``new_hash``, or report that it moved.

    A rowcount of zero means another writer advanced the head between our
    read and this statement: the caller must retry rather than fork.
    """
    result = db.execute(
        update(AuditChainHead)
        .where(
            AuditChainHead.id == 1,
            AuditChainHead.head_hash == expected,
        )
        .values(head_hash=new_hash)
    )
    return result.rowcount == 1


def append_entry(
    db: Session,
    *,
    actor_id: int | None,
    actor_name: str | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: str | None = None,
    source_ip_hash: str | None = None,
    created_at: datetime | None = None,
    tenant_id: str | None = None,
    break_glass_grant_id: int | None = None,
) -> AuditLog:
    """Stage one chained audit entry on the session.

    The entry and the head move are part of the caller's transaction: a
    rollback removes both, so a mutation that did not happen leaves no chain
    entry. ``tenant_id`` and ``break_glass_grant_id`` are stored on the row
    but are not part of the canonical hash payload (the chain format is
    unchanged), so existing entries verify without them.
    """
    created = created_at or datetime.now(timezone.utc)
    _ensure_head(db)
    for _attempt in range(APPEND_RETRIES):
        prev_hash, _prev_id = _read_head(db)
        entry_hash = compute_entry_hash(
            prev_hash=prev_hash,
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            source_ip_hash=source_ip_hash,
            created_at=created,
        )
        if not _compare_and_set_head(db, prev_hash, entry_hash):
            continue
        entry = AuditLog(
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            source_ip_hash=source_ip_hash,
            tenant_id=tenant_id,
            break_glass_grant_id=break_glass_grant_id,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            created_at=created,
        )
        db.add(entry)
        db.flush()
        db.execute(
            update(AuditChainHead)
            .where(AuditChainHead.id == 1)
            .values(head_id=entry.id)
        )
        return entry
    raise RuntimeError(
        "the audit chain head moved on every attempt; the entry was not written"
    )


def backfill_chain(bind) -> tuple[int, int | None, str]:
    """Chain every row that has no hash yet, in id order.

    Returns ``(rows_chained, last_id, last_hash)``. A row that already carries
    a hash is left alone and becomes the predecessor of the next one, so the
    function is safe to run again — which is what the contract revision does,
    to catch a row the old code wrote during the expand migration.

    The caller owns the transaction. ``bind`` is a Connection.
    """
    rows = bind.execute(
        text(
            "SELECT id, actor_id, actor_name, action, entity_type, entity_id, "
            "details, source_ip_hash, entry_hash, created_at "
            "FROM audit_logs ORDER BY id"
        )
    ).mappings().all()
    previous = GENESIS_HASH
    last_id: int | None = None
    chained = 0
    for row in rows:
        if row["entry_hash"]:
            previous = row["entry_hash"]
            last_id = row["id"]
            continue
        entry_hash = compute_entry_hash(
            prev_hash=previous,
            actor_id=row["actor_id"],
            actor_name=row["actor_name"],
            action=row["action"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            details=row["details"],
            source_ip_hash=row["source_ip_hash"],
            created_at=row["created_at"],
        )
        bind.execute(
            text(
                "UPDATE audit_logs SET prev_hash = :prev, entry_hash = :entry "
                "WHERE id = :id"
            ),
            {"prev": previous, "entry": entry_hash, "id": row["id"]},
        )
        previous = entry_hash
        last_id = row["id"]
        chained += 1
    return chained, last_id, previous


def set_head(bind, head_hash: str, head_id: int | None) -> None:
    """Point the head row at an entry, creating the row if it is absent."""
    existing = bind.execute(
        text("SELECT id FROM audit_chain_head WHERE id = 1")
    ).first()
    if existing is None:
        bind.execute(
            text(
                "INSERT INTO audit_chain_head (id, head_hash, head_id) "
                "VALUES (1, :hash, :entry_id)"
            ),
            {"hash": head_hash, "entry_id": head_id},
        )
        return
    bind.execute(
        text(
            "UPDATE audit_chain_head SET head_hash = :hash, head_id = :entry_id "
            "WHERE id = 1"
        ),
        {"hash": head_hash, "entry_id": head_id},
    )


@dataclass
class ChainVerification:
    """The result of walking the chain."""

    ok: bool
    entries: int = 0
    head: str | None = None
    head_id: int | None = None
    failure_id: int | None = None
    #: Machine-readable reason, stable enough for a client to branch on:
    #: ``hash_mismatch`` (a row was edited), ``missing_predecessor`` (a row
    #: was inserted, removed or reordered in the middle) or ``head_mismatch``
    #: (entries were removed from the tail, or the head was rewritten).
    failure_code: str | None = None
    failure_reason: str | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "entries": self.entries,
            "head": self.head,
            "head_id": self.head_id,
            "failure_id": self.failure_id,
            "failure_code": self.failure_code,
            "failure_reason": self.failure_reason,
            "message": self.message,
        }


def verify_chain(db: Session, *, check_head: bool = True) -> ChainVerification:
    """Walk the chain in id order and report the first entry that fails.

    The walk checks two things per entry: that ``prev_hash`` is the previous
    entry's ``entry_hash``, and that ``entry_hash`` recomputes from the row.
    It then compares the last entry with the recorded head, which is what
    detects entries removed from the tail.
    """
    # Read the head once. It is reported on every outcome — a caller that is
    # told "the chain is broken" still needs the head it was compared with,
    # because that is the value an operator anchors outside the database.
    head_hash, head_id = _read_head(db)
    rows = (
        db.execute(select(AuditLog).order_by(AuditLog.id))
        .scalars()
        .all()
    )
    expected_prev = GENESIS_HASH
    last_hash: str | None = None
    last_id: int | None = None
    verified = 0

    for row in rows:
        if (row.prev_hash or "") != expected_prev:
            return ChainVerification(
                ok=False,
                entries=verified,
                head=head_hash,
                head_id=head_id,
                failure_id=row.id,
                failure_code="missing_predecessor",
                failure_reason=(
                    "prev_hash does not match the entry before it: the row was "
                    "inserted, removed or reordered"
                ),
                message=(
                    f"audit chain: entry {row.id} does not verify "
                    f"(prev_hash={row.prev_hash or 'null'}, "
                    f"expected={expected_prev})"
                ),
            )
        recomputed = compute_entry_hash(
            prev_hash=row.prev_hash,
            actor_id=row.actor_id,
            actor_name=row.actor_name,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            details=row.details,
            source_ip_hash=row.source_ip_hash,
            created_at=row.created_at,
        )
        if recomputed != row.entry_hash:
            return ChainVerification(
                ok=False,
                entries=verified,
                head=head_hash,
                head_id=head_id,
                failure_id=row.id,
                failure_code="hash_mismatch",
                failure_reason=(
                    "entry_hash does not match the row: the row was edited "
                    "after it was written"
                ),
                message=(
                    f"audit chain: entry {row.id} does not verify "
                    f"(stored={row.entry_hash}, recomputed={recomputed})"
                ),
            )
        expected_prev = row.entry_hash
        last_hash = row.entry_hash
        last_id = row.id
        verified += 1

    if check_head:
        if rows and head_hash != last_hash:
            return ChainVerification(
                ok=False,
                entries=verified,
                head=head_hash,
                head_id=head_id,
                failure_id=last_id,
                failure_code="head_mismatch",
                failure_reason=(
                    "the recorded head does not match the last entry: entries "
                    "were removed from the tail, or the head was rewritten"
                ),
                message=(
                    f"audit chain: the head is {head_hash} but the last entry "
                    f"({last_id}) is {last_hash}"
                ),
            )
        if not rows and head_hash != GENESIS_HASH:
            return ChainVerification(
                ok=False,
                entries=0,
                head=head_hash,
                head_id=head_id,
                failure_code="head_mismatch",
                failure_reason="the head names entries that are not present",
                message=(
                    f"audit chain: the head is {head_hash} but the table is empty"
                ),
            )

    return ChainVerification(
        ok=True,
        entries=verified,
        head=last_hash or GENESIS_HASH,
        head_id=last_id,
        message=(
            f"audit chain: {verified} entries verified, head {last_hash or GENESIS_HASH}"
        ),
    )


# ---------------------------------------------------------------------------
# Append-only enforcement at the database level
# ---------------------------------------------------------------------------
#
# The application connects to Oracle as the schema owner, and an owner cannot
# have UPDATE/DELETE revoked from itself. A trigger is therefore the mechanism
# that actually refuses the statement, on both Oracle and SQLite, for the
# application and for anyone else using the same credentials. Someone with
# DDL rights can drop the trigger; the chain is what catches that.

_APPEND_ONLY_TABLES = ("audit_logs",)


def _dialect_name(bind) -> str:
    return bind.dialect.name


def install_append_only(bind) -> None:
    """Refuse UPDATE and DELETE on the audit table at the database level."""
    dialect = _dialect_name(bind)
    for table in _APPEND_ONLY_TABLES:
        for operation in ("UPDATE", "DELETE"):
            trigger = f"{table}_no_{operation.lower()}"
            if dialect == "postgresql":
                function = f"{trigger}_fn"
                bind.execute(
                    text(
                        f"CREATE OR REPLACE FUNCTION {function}() "
                        f"RETURNS trigger AS $$ BEGIN RAISE EXCEPTION "
                        f"'{table} is append-only'; END; $$ LANGUAGE plpgsql"
                    )
                )
                bind.execute(
                    text(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
                )
                bind.execute(
                    text(
                        f"CREATE TRIGGER {trigger} "
                        f"BEFORE {operation} ON {table} "
                        f"FOR EACH ROW EXECUTE FUNCTION {function}()"
                    )
                )
            elif dialect == "oracle":
                bind.execute(
                    text(
                        f"CREATE OR REPLACE TRIGGER {trigger} "
                        f"BEFORE {operation} ON {table} "
                        f"BEGIN RAISE_APPLICATION_ERROR(-20001, "
                        f"'{table} is append-only'); END;"
                    )
                )
            else:
                bind.execute(
                    text(
                        f"CREATE TRIGGER IF NOT EXISTS {trigger} "
                        f"BEFORE {operation} ON {table} "
                        f"BEGIN SELECT RAISE(ABORT, "
                        f"'{table} is append-only'); END"
                    )
                )


def remove_append_only(bind) -> None:
    """Drop the append-only triggers (the downgrade path)."""
    dialect = _dialect_name(bind)
    for table in _APPEND_ONLY_TABLES:
        for operation in ("UPDATE", "DELETE"):
            trigger = f"{table}_no_{operation.lower()}"
            if dialect == "postgresql":
                bind.execute(
                    text(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
                )
                bind.execute(
                    text(f"DROP FUNCTION IF EXISTS {trigger}_fn()")
                )
            elif dialect == "oracle":
                try:
                    bind.execute(text(f"DROP TRIGGER {trigger}"))
                except Exception:  # noqa: BLE001 - absent on a partial upgrade
                    pass
            else:
                bind.execute(text(f"DROP TRIGGER IF EXISTS {trigger}"))
