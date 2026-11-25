"""integrity expand: enforce the safe NFR-014 constraints (LP-NFR-014)

Revision ID: 0043_integrity_expand
Revises: 0042_notification_delivery
Create Date: 2026-11-22

What this adds (NFR-014: preserve financial, employment, approval and
audit history with database constraints and transaction rules)
----------------------------------------------------------------
The constraint catalogue has thirteen candidates (C1..C13, documented in
``docs/engineering/data-integrity-constraints.md``). This revision enacts
the ten that are safe to enforce on a database that already holds data:

* C2  ``uq_payslip_run_employee`` — UNIQUE(pay_run_id, employee_id) on
  ``pay_slips``: a retried or concurrent process cannot write two slips
  for one employee in one run. The models already declare it; a database
  built by ``create_all()`` carries it, a legacy database may not.
* C4  ``ck_claim_amount_nonneg`` — ``expense_claims.amount >= 0``.
* C5  ``ck_claim_status_fsm`` — ``expense_claims.status`` in the claim FSM.
* C6  ``ck_claim_paystat_fsm`` — ``expense_claims.payment_status`` in
  ``('UNPAID','PAID')``.
* C7  ``ck_leave_req_dates`` — ``leave_requests.start_date <= end_date``.
* C8  ``ck_leave_req_status`` — ``leave_requests.status`` in the request FSM.
* C9  ``ck_ledger_signed_nonzero`` — ``leave_ledger.signed_days <> 0``:
  a zero-effect row moves no balance and only hides in the ledger.
* C11 ``ck_emphist_dates`` — ``employee_history.effective_to IS NULL OR
  effective_to >= effective_from``.
* C12 ``ck_payslip_amounts_nonneg`` — ``pay_slips`` money ``>= 0``.
* C13 ``ck_receipt_size_nonneg`` — ``expense_receipts.size_bytes >= 0``.

Deferred (NOT in this revision): C1 (email canonicalisation needs the
application normaliser first), C3 (leave ledger invariant needs the
reconciliation job) and C10 (pay-run cross-column arithmetic needs the
rounding review). They stay application-checked until their follow-up;
nothing here claims them.

* ``integrity_quarantine`` — the table that holds every row this revision
  had to touch before constraining: the table, the primary key, which
  constraint it violated and the pre-fix values as JSON. Nothing is
  silently discarded: a row is only changed after its old state is
  recorded, and the counts are printed (the backfill report).
* FK indexes for the foreign keys added after 0008 (expense approver
  chain, receipt uploader, custom-field definition, employee documents),
  created only where the column list is not already indexed.

Backfill (no silent discard)
----------------------------
Every violation found is inserted into ``integrity_quarantine`` first and
then repaired with the only loss-free (or loss-recorded) fix, mirroring
the 0009 precedent of normalising towards the least-privilege safe value:

* unknown claim/request status -> the initial state (``DRAFT``/``Pending``,
  ``UNPAID`` for money — never mark paid by guess);
* negative money/size -> quarantined with the old value, then zeroed;
* inverted leave dates -> start/end swapped (order preserved, no data lost);
* inverted history dates -> ``effective_to`` nulled (still in force);
* zero-effect ledger rows -> quarantined with the full row, then removed
  (the ledger sum is unchanged by construction);
* duplicate payslips -> later copies quarantined with the full row, then
  removed, keeping the earliest (the retry artefact, not the first write).

Each step prints ``[0043_integrity_expand] ...`` lines: quarantined row
counts, repaired row counts, and the final per-constraint verdict. An
operator reading the migration log sees exactly what moved and why. No
account, employee or money identifier beyond the numeric primary key is
printed.

Idempotency
-----------
Both directions ask the catalog first (the 0036/0037/0039/0040/0041
pattern): a database the current models already built via ``create_all()``
carries the constraints, so the upgrade skips them there. Re-running is a
no-op: quarantine inserts are guarded by a UNIQUE(table_name, row_pk,
reason), so a second run finds nothing to repair and inserts nothing.

Dialects
--------
* Oracle: ``ALTER TABLE ... ADD CONSTRAINT`` / ``DROP CONSTRAINT``;
  every name is capped at 30 characters (the limit older Oracle releases
  impose).
* PostgreSQL: ``ADD CONSTRAINT`` / ``DROP CONSTRAINT`` (invalid legacy
  rows are repaired first, so no ``NOT VALID`` escape is needed).
* SQLite: ``batch_alter_table`` rebuilds the table (the only way SQLite
  can add a table-level constraint). The batch path re-emits the models'
  inline column CHECKs from reflection, so the rebuild is scoped to one
  table at a time and each constraint is added only when absent.

The downgrade drops the constraints, the unique key and the indexes this
revision created — and only those. ``integrity_quarantine`` is retained
when it holds repair records and dropped when it is empty: a non-empty
quarantine is evidence, and dropping it would silently discard exactly
the record this revision promises to keep; an empty one is scaffolding,
and dropping it keeps ``downgrade base`` a true empty schema.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names, create_index_if_missing

revision = "0043_integrity_expand"
down_revision = "0042_notification_delivery"
branch_labels = None
depends_on = None

QUARANTINE = "integrity_quarantine"

#: (table, column) foreign keys added after 0008 whose columns have no
#: index of their own. Written out, not derived from the models (the 0008
#: rule): the revision says exactly what it does. Each entry is created
#: only when its column list is not already indexed and is skipped
#: (not failed) when the table or the column is absent, so the revision
#: stays applicable to a database that is behind the models.
NEW_FK_INDEXES: tuple[tuple[str, str], ...] = (
    ("expense_claims", "submitted_by"),
    ("expense_claims", "l1_approved_by"),
    ("expense_claims", "approved_by"),
    ("expense_claims", "rejected_by"),
    ("expense_claims", "paid_by"),
    ("expense_receipts", "uploaded_by"),
    ("custom_field_values", "def_id"),
    ("employee_documents", "employee_id"),
)

#: The longest identifier older Oracle releases accept.
MAX_NAME_LENGTH = 30


def _shorten(name: str) -> str:
    """Cap an identifier at the Oracle limit without collisions."""
    if len(name) <= MAX_NAME_LENGTH:
        return name
    import hashlib

    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return name[: MAX_NAME_LENGTH - len(digest) - 1] + "_" + digest


def _fk_index_name(table: str, column: str) -> str:
    """The index name for a foreign-key column (the 0008 convention)."""
    return _shorten(f"ix_fk_{table}_{column}")


#: The CHECK constraints this revision owns: (table, name, sql).
#: Every name is at most 30 characters and every SQL text is plain
#: ``length``/comparison logic that compiles on Oracle, PostgreSQL and
#: SQLite (no regexp_like, no GLOB) — the same portability rule the
#: india-payroll CHECKs follow.
SAFE_CHECKS: tuple[tuple[str, str, str], ...] = (
    (
        "expense_claims",
        "ck_claim_amount_nonneg",
        "amount >= 0",
    ),
    (
        "expense_claims",
        "ck_claim_status_fsm",
        "status IN ('DRAFT','SUBMITTED','L1_APPROVED','APPROVED','REJECTED')",
    ),
    (
        "expense_claims",
        "ck_claim_paystat_fsm",
        "payment_status IN ('UNPAID','PAID')",
    ),
    (
        "leave_requests",
        "ck_leave_req_dates",
        "start_date <= end_date",
    ),
    (
        "leave_requests",
        "ck_leave_req_status",
        "status IN ('Pending','Approved','Rejected','Cancelled')",
    ),
    (
        "leave_ledger",
        "ck_ledger_signed_nonzero",
        "signed_days <> 0",
    ),
    (
        "employee_history",
        "ck_emphist_dates",
        "effective_to IS NULL OR effective_to >= effective_from",
    ),
    (
        "pay_slips",
        "ck_payslip_amounts_nonneg",
        "gross_pay >= 0 AND net_pay >= 0 AND total_deductions >= 0",
    ),
    (
        "expense_receipts",
        "ck_receipt_size_nonneg",
        "size_bytes >= 0",
    ),
)

#: The UNIQUE constraint this revision owns (C2).
PAYSLIPS = "pay_slips"
PAYSLIP_UNIQUE = "uq_payslip_run_employee"
PAYSLIP_UNIQUE_COLUMNS = ("pay_run_id", "employee_id")


# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------


def _has_check(inspector, table: str, name: str) -> bool:
    try:
        constraints = inspector.get_check_constraints(table)
    except Exception:  # noqa: BLE001 - SQLite reflections vary by version
        return False
    return any(
        str(c.get("name") or "").casefold() == name.casefold()
        for c in constraints
    )


def _has_unique(inspector, table: str, name: str) -> bool:
    try:
        uniques = inspector.get_unique_constraints(table)
    except Exception:  # noqa: BLE001
        return False
    if any(str(u.get("name") or "").casefold() == name.casefold() for u in uniques):
        return True
    # SQLite reports a UNIQUE constraint as an auto-index; a unique index
    # over the same column list enforces the same rule, so it counts.
    try:
        indexes = inspector.get_indexes(table)
    except Exception:  # noqa: BLE001
        return False
    wanted = tuple(c.casefold() for c in PAYSLIP_UNIQUE_COLUMNS)
    return any(
        idx.get("unique")
        and tuple(str(c).casefold() for c in (idx.get("column_names") or []))
        == wanted
        for idx in indexes
    )


def _ensure_quarantine_table() -> str | None:
    """Create ``integrity_quarantine`` unless it is already there."""
    bind = op.get_bind()
    catalog = catalog_names(bind)
    live = catalog.table(QUARANTINE)
    if live is not None:
        print(f"[0043_integrity_expand] {QUARANTINE} already present; skipping")
        return live
    # The table name is fresh in this revision, so the catalog holds it
    # exactly as written; no case folding is needed for the create.
    op.create_table(
        QUARANTINE,
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("table_name", sa.String(60), nullable=False),
        sa.Column("row_pk", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(60), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "table_name", "row_pk", "reason", name="uq_quarantine_row_reason"
        ),
    )
    op.create_index(
        _shorten("ix_quarantine_table"), QUARANTINE, ["table_name"]
    )
    print(f"[0043_integrity_expand] created {QUARANTINE}")
    return QUARANTINE


def _quarantine(
    bind, live_quarantine: str, table: str, row_pk: int, reason: str, details: dict
) -> bool:
    """Record a repaired row. Returns True when the record was new."""
    payload = json.dumps(details, sort_keys=True, default=str)
    existing = bind.execute(
        sa.text(
            f"SELECT id FROM {live_quarantine} "
            "WHERE table_name = :t AND row_pk = :pk AND reason = :r"
        ),
        {"t": table, "pk": row_pk, "r": reason},
    ).first()
    if existing is not None:
        return False
    bind.execute(
        sa.text(
            f"INSERT INTO {live_quarantine} (table_name, row_pk, reason, details) "
            "VALUES (:t, :pk, :r, :d)"
        ),
        {"t": table, "pk": row_pk, "r": reason, "d": payload},
    )
    return True


# ---------------------------------------------------------------------------
# Backfill: quarantine first, repair second, report always
# ---------------------------------------------------------------------------


def _backfill(bind, live_quarantine: str) -> dict[str, int]:
    """Move every constraint violation into quarantine and repair it.

    Returns the per-constraint quarantine counts for the backfill report.
    Repairs are the only fixes that lose nothing (or lose only what the
    quarantine record preserves): statuses fall back to their initial
    state, never to a privileged one; money keeps its row with the old
    value recorded; ordering mistakes are reordered, not deleted.
    """
    report: dict[str, int] = {}

    def note(reason: str, count: int) -> None:
        report[reason] = report.get(reason, 0) + count

    # -- C5/C6/C8: unknown statuses -> initial state (least privilege) ----
    for table, column, allowed, fallback, reason in (
        (
            "expense_claims",
            "status",
            ("DRAFT", "SUBMITTED", "L1_APPROVED", "APPROVED", "REJECTED"),
            "DRAFT",
            "ck_claim_status_fsm",
        ),
        (
            "expense_claims",
            "payment_status",
            ("UNPAID", "PAID"),
            "UNPAID",
            "ck_claim_paystat_fsm",
        ),
        (
            "leave_requests",
            "status",
            ("Pending", "Approved", "Rejected", "Cancelled"),
            "Pending",
            "ck_leave_req_status",
        ),
    ):
        catalog = catalog_names(bind, tables=[table])
        live = catalog.table(table)
        col = catalog.column(live, column) if live else None
        if live is None or col is None:
            print(f"[0043_integrity_expand] {table}.{column} absent; skipping")
            continue
        placeholders = ", ".join(f"'{v}'" for v in allowed)
        rows = bind.execute(
            sa.text(
                f"SELECT id, {col} FROM {live} "
                f"WHERE {col} IS NULL OR {col} NOT IN ({placeholders})"
            )
        ).fetchall()
        fixed = 0
        for row_id, old in rows:
            _quarantine(
                bind,
                live_quarantine,
                live,
                int(row_id),
                reason,
                {"column": column, "old_value": old, "new_value": fallback},
            )
            bind.execute(
                sa.text(f"UPDATE {live} SET {col} = :v WHERE id = :i"),
                {"v": fallback, "i": row_id},
            )
            fixed += 1
        note(reason, fixed)
        print(
            f"[0043_integrity_expand] {reason}: quarantined+repaired {fixed} row(s)"
        )

    # -- C4/C12/C13: negative money/size -> quarantine, then zero ---------
    for table, columns, reason in (
        ("expense_claims", ("amount",), "ck_claim_amount_nonneg"),
        (
            "pay_slips",
            ("gross_pay", "net_pay", "total_deductions"),
            "ck_payslip_amounts_nonneg",
        ),
        ("expense_receipts", ("size_bytes",), "ck_receipt_size_nonneg"),
    ):
        catalog = catalog_names(bind, tables=[table])
        live = catalog.table(table)
        if live is None:
            print(f"[0043_integrity_expand] {table} absent; skipping")
            continue
        live_cols = [
            catalog.column(live, c) for c in columns if catalog.column(live, c)
        ]
        if not live_cols:
            print(f"[0043_integrity_expand] {table} money columns absent; skipping")
            continue
        condition = " OR ".join(f"{c} < 0" for c in live_cols)
        select_cols = ", ".join(["id"] + live_cols)
        rows = bind.execute(
            sa.text(f"SELECT {select_cols} FROM {live} WHERE {condition}")
        ).fetchall()
        fixed = 0
        for row in rows:
            row_id = int(row[0])
            old = {c: row[i + 1] for i, c in enumerate(live_cols)}
            _quarantine(
                bind,
                live_quarantine,
                live,
                row_id,
                reason,
                {"old_values": old, "new_value": 0},
            )
            bind.execute(
                sa.text(
                    f"UPDATE {live} SET "
                    + ", ".join(f"{c} = CASE WHEN {c} < 0 THEN 0 ELSE {c} END" for c in live_cols)
                    + " WHERE id = :i"
                ),
                {"i": row_id},
            )
            fixed += 1
        note(reason, fixed)
        print(
            f"[0043_integrity_expand] {reason}: quarantined+repaired {fixed} row(s)"
        )

    # -- C7: inverted leave dates -> swap (order preserved, none lost) ----
    catalog = catalog_names(bind, tables=["leave_requests"])
    live = catalog.table("leave_requests")
    if live is not None:
        start = catalog.column(live, "start_date")
        end = catalog.column(live, "end_date")
        if start is None or end is None:
            print("[0043_integrity_expand] leave_requests dates absent; skipping")
        else:
            rows = bind.execute(
                sa.text(
                    f"SELECT id, {start}, {end} FROM {live} "
                    f"WHERE {start} IS NOT NULL AND {end} IS NOT NULL "
                    f"AND {start} > {end}"
                )
            ).fetchall()
            fixed = 0
            for row_id, old_start, old_end in rows:
                _quarantine(
                    bind,
                    live_quarantine,
                    live,
                    int(row_id),
                    "ck_leave_req_dates",
                    {"old_start": old_start, "old_end": old_end,
                     "new_start": old_end, "new_end": old_start},
                )
                bind.execute(
                    sa.text(
                        f"UPDATE {live} SET {start} = :s, {end} = :e WHERE id = :i"
                    ),
                    {"s": old_end, "e": old_start, "i": row_id},
                )
                fixed += 1
            note("ck_leave_req_dates", fixed)
            print(
                "[0043_integrity_expand] ck_leave_req_dates: "
                f"quarantined+repaired {fixed} row(s)"
            )
    else:
        print("[0043_integrity_expand] leave_requests absent; skipping")

    # -- C11: inverted history dates -> still in force (NULL), recorded --
    catalog = catalog_names(bind, tables=["employee_history"])
    live = catalog.table("employee_history")
    if live is not None:
        eff_from = catalog.column(live, "effective_from")
        eff_to = catalog.column(live, "effective_to")
        if eff_from is None or eff_to is None:
            print("[0043_integrity_expand] employee_history dates absent; skipping")
        else:
            rows = bind.execute(
                sa.text(
                    f"SELECT id, {eff_from}, {eff_to} FROM {live} "
                    f"WHERE {eff_to} IS NOT NULL AND {eff_to} < {eff_from}"
                )
            ).fetchall()
            fixed = 0
            for row_id, old_from, old_to in rows:
                _quarantine(
                    bind,
                    live_quarantine,
                    live,
                    int(row_id),
                    "ck_emphist_dates",
                    {"effective_from": old_from, "old_effective_to": old_to,
                     "new_effective_to": None},
                )
                bind.execute(
                    sa.text(f"UPDATE {live} SET {eff_to} = NULL WHERE id = :i"),
                    {"i": row_id},
                )
                fixed += 1
            note("ck_emphist_dates", fixed)
            print(
                "[0043_integrity_expand] ck_emphist_dates: "
                f"quarantined+repaired {fixed} row(s)"
            )
    else:
        print("[0043_integrity_expand] employee_history absent; skipping")

    # -- C9: zero-effect ledger rows -> quarantine the row, then remove --
    # A row with signed_days = 0 contributes nothing to the ledger sum, so
    # removing it after recording it changes no balance by construction.
    catalog = catalog_names(bind, tables=["leave_ledger"])
    live = catalog.table("leave_ledger")
    if live is not None:
        signed = catalog.column(live, "signed_days")
        if signed is None:
            print("[0043_integrity_expand] leave_ledger.signed_days absent; skipping")
        else:
            cols = ["id", "balance_id", "employee_id", "leave_type_id",
                    "entitlement_year", "entry_type", signed]
            have = [c for c in cols if catalog.column(live, c) or c in ("id", signed)]
            rows = bind.execute(
                sa.text(
                    f"SELECT {', '.join(have)} FROM {live} WHERE {signed} = 0"
                )
            ).fetchall()
            fixed = 0
            for row in rows:
                row_id = int(row[0])
                _quarantine(
                    bind,
                    live_quarantine,
                    live,
                    row_id,
                    "ck_ledger_signed_nonzero",
                    {"row": {c: row[i] for i, c in enumerate(have)}},
                )
                bind.execute(sa.text(f"DELETE FROM {live} WHERE id = :i"), {"i": row_id})
                fixed += 1
            note("ck_ledger_signed_nonzero", fixed)
            print(
                "[0043_integrity_expand] ck_ledger_signed_nonzero: "
                f"quarantined+removed {fixed} row(s)"
            )
    else:
        print("[0043_integrity_expand] leave_ledger absent; skipping")

    # -- C2: duplicate payslips -> keep earliest, quarantine+remove rest --
    catalog = catalog_names(bind, tables=["pay_slips"])
    live = catalog.table("pay_slips")
    if live is not None:
        run_col = catalog.column(live, "pay_run_id")
        emp_col = catalog.column(live, "employee_id")
        if run_col is None or emp_col is None:
            print("[0043_integrity_expand] pay_slips keys absent; skipping")
        else:
            dup_groups = bind.execute(
                sa.text(
                    f"SELECT {run_col}, {emp_col}, COUNT(*) AS n FROM {live} "
                    f"GROUP BY {run_col}, {emp_col} HAVING COUNT(*) > 1"
                )
            ).fetchall()
            fixed = 0
            for run_id, emp_id, _n in dup_groups:
                ids = [
                    r[0]
                    for r in bind.execute(
                        sa.text(
                            f"SELECT id FROM {live} "
                            f"WHERE {run_col} = :r AND {emp_col} = :e "
                            "ORDER BY id ASC"
                        ),
                        {"r": run_id, "e": emp_id},
                    ).fetchall()
                ]
                for extra in ids[1:]:
                    detail = bind.execute(
                        sa.text(f"SELECT * FROM {live} WHERE id = :i"), {"i": extra}
                    ).mappings().first()
                    _quarantine(
                        bind,
                        live_quarantine,
                        live,
                        int(extra),
                        PAYSLIP_UNIQUE,
                        {"kept_id": ids[0], "removed_row": dict(detail or {})},
                    )
                    bind.execute(
                        sa.text(f"DELETE FROM {live} WHERE id = :i"), {"i": extra}
                    )
                    fixed += 1
            note(PAYSLIP_UNIQUE, fixed)
            print(
                f"[0043_integrity_expand] {PAYSLIP_UNIQUE}: "
                f"quarantined+removed {fixed} duplicate row(s)"
            )
    else:
        print("[0043_integrity_expand] pay_slips absent; skipping")

    quarantined = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {live_quarantine}")
    ).scalar() or 0
    print(
        f"[0043_integrity_expand] backfill report: "
        f"{json.dumps(report, sort_keys=True)}; "
        f"quarantine now holds {quarantined} row(s)"
    )
    return report


# ---------------------------------------------------------------------------
# Constraint DDL, one dialect-aware step per constraint
# ---------------------------------------------------------------------------


def _add_check(table: str, name: str, sql: str) -> None:
    """Add a named CHECK, asking the catalog first.

    Oracle and PostgreSQL take ``ADD CONSTRAINT``; SQLite rebuilds the
    table through batch mode (its only path to a new table-level
    constraint). Either way the constraint is added only when absent, so
    re-running is a no-op.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind, tables=[table])
    live = catalog.table(table)
    if live is None:
        print(f"[0043_integrity_expand] {table} is not present; skipping {name}")
        return
    if _has_check(inspector, live, name):
        print(f"[0043_integrity_expand] {live}.{name} already present; skipping")
        return
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(live) as batch:
            batch.create_check_constraint(name, sql)
    else:
        op.create_check_constraint(name, live, sql)
    print(f"[0043_integrity_expand] added {live}.{name}")


def _drop_check(table: str, name: str) -> None:
    """Drop a named CHECK, but only when it is there."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind, tables=[table])
    live = catalog.table(table) or table
    if not _has_check(inspector, live, name):
        print(f"[0043_integrity_expand] {live}.{name} already absent; skipping")
        return
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(live) as batch:
            batch.drop_constraint(name, type_="check")
    else:
        op.drop_constraint(name, live, type_="check")
    print(f"[0043_integrity_expand] dropped {live}.{name}")


def _add_payslip_unique() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind, tables=[PAYSLIPS])
    live = catalog.table(PAYSLIPS)
    if live is None:
        print(f"[0043_integrity_expand] {PAYSLIPS} is not present; skipping C2")
        return
    if _has_unique(inspector, live, PAYSLIP_UNIQUE):
        print(
            f"[0043_integrity_expand] {live}.{PAYSLIP_UNIQUE} already present; skipping"
        )
        return
    with op.batch_alter_table(live) as batch:
        batch.create_unique_constraint(PAYSLIP_UNIQUE, list(PAYSLIP_UNIQUE_COLUMNS))
    print(f"[0043_integrity_expand] added {live}.{PAYSLIP_UNIQUE}")


def _drop_payslip_unique() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind, tables=[PAYSLIPS])
    live = catalog.table(PAYSLIPS) or PAYSLIPS
    if not _has_unique(inspector, live, PAYSLIP_UNIQUE):
        print(f"[0043_integrity_expand] {live}.{PAYSLIP_UNIQUE} already absent; skipping")
        return
    with op.batch_alter_table(live) as batch:
        batch.drop_constraint(PAYSLIP_UNIQUE, type_="unique")
    print(f"[0043_integrity_expand] dropped {live}.{PAYSLIP_UNIQUE}")


def upgrade() -> None:
    bind = op.get_bind()
    live_quarantine = _ensure_quarantine_table() or QUARANTINE

    _backfill(bind, live_quarantine)

    _add_payslip_unique()
    for table, name, sql in SAFE_CHECKS:
        _add_check(table, name, sql)

    # FK indexes for the post-0008 foreign keys. Each creation asks the
    # catalog (via the shared helper) whether the column list is already
    # indexed, so a column that already has one — Oracle refuses a second
    # (ORA-01408) — is left alone in both directions.
    from app.core.migrations import indexed_column_lists  # noqa: E402

    inspector = sa.inspect(bind)
    for table, column in NEW_FK_INDEXES:
        catalog = catalog_names(bind, tables=[table])
        live = catalog.table(table)
        if live is None:
            print(f"[0043_integrity_expand] {table} is not present; skipping index")
            continue
        live_column = catalog.column(live, column)
        if live_column is None:
            print(
                f"[0043_integrity_expand] {live}.{column} is not present; "
                "skipping index"
            )
            continue
        if (live_column.casefold(),) in indexed_column_lists(inspector, live):
            print(
                f"[0043_integrity_expand] {live}.{live_column} already indexed; "
                "skipping"
            )
            continue
        created = create_index_if_missing(
            _fk_index_name(table, column), live, [live_column]
        )
        if not created:
            print(
                f"[0043_integrity_expand] {live}.{live_column} already indexed; "
                "skipping"
            )
        else:
            print(
                f"[0043_integrity_expand] created index "
                f"{_fk_index_name(table, column)} on {live}({live_column})"
            )

    print("[0043_integrity_expand] upgrade complete")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _drop_payslip_unique()
    for table, name, _sql in reversed(SAFE_CHECKS):
        _drop_check(table, name)

    # Drop only the indexes this revision could have created: the names
    # carry the ``ix_fk_`` prefix no model-generated index can have (the
    # 0008 rule), so the downgrade can never take an index that belongs
    # to somebody else.
    from app.core.migrations import drop_index_if_present  # noqa: E402

    for table, column in NEW_FK_INDEXES:
        catalog = catalog_names(bind, tables=[table])
        live = catalog.table(table) or table
        if drop_index_if_present(_fk_index_name(table, column), live):
            print(
                f"[0043_integrity_expand] dropped index "
                f"{_fk_index_name(table, column)}"
            )
        else:
            print(
                f"[0043_integrity_expand] index "
                f"{_fk_index_name(table, column)} already absent; skipping"
            )

    # ``integrity_quarantine`` is retained when it holds evidence and
    # dropped when it is empty: a non-empty quarantine is the record of
    # what the upgrade repaired, and dropping it would silently discard
    # exactly the record this revision promises to keep; an empty one is
    # scaffolding, and dropping it keeps ``downgrade base`` a true empty
    # schema (the migration suite's invariant).
    catalog = catalog_names(bind, tables=[QUARANTINE])
    live_quarantine = catalog.table(QUARANTINE)
    if live_quarantine is None:
        print(f"[0043_integrity_expand] {QUARANTINE} already absent; skipping")
        return
    count = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {live_quarantine}")
    ).scalar() or 0
    if count == 0:
        op.drop_table(live_quarantine)
        print(
            f"[0043_integrity_expand] dropped empty {live_quarantine}"
        )
    else:
        print(
            f"[0043_integrity_expand] downgrade complete "
            f"({live_quarantine} retained: {count} repair record(s))"
        )
