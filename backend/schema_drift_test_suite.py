"""Schema drift reporter — regression suite.

The reporter compares the models with the live schema. It has to be
correct in two situations:

* a table that is missing a column, and a table that is missing entirely;
* a database that folds identifiers to upper case, which is what Oracle
  does with an unquoted name. A model that says ``pay_runs`` has to be
  matched to the catalog's ``PAY_RUNS``.

Run with:

    SECRET_KEY=... DATABASE_URL=sqlite:///./drift_test.db \\
        .venv/bin/python schema_drift_test_suite.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


class StubInspector:
    """An inspector that reports upper-case identifiers, as Oracle does."""

    def __init__(self, tables: dict[str, list[tuple[str, str]]]):
        # tables: {live name: [(column name, type)]}
        self.tables = tables

    def get_table_names(self) -> list[str]:
        return list(self.tables)

    def get_columns(self, table: str) -> list[dict]:
        return [
            {"name": name, "type": type_}
            for name, type_ in self.tables.get(table, [])
        ]


def main() -> int:
    print("=" * 68)
    print("SCHEMA DRIFT SUITE")
    print("=" * 68)

    workdir = tempfile.mkdtemp(prefix="karmathy-drift-")
    db_url = f"sqlite:///{workdir}/drift.db"
    os.environ["DATABASE_URL"] = db_url
    os.environ.setdefault("SECRET_KEY", "test_secret_key_for_development_32_chars")

    try:
        from sqlalchemy import text

        from app.core.database import Base, engine
        from app.core.schema_drift import schema_drift_report

        import app.models
        import importlib
        import pkgutil

        from app.core.idempotency import IdempotencyRecord  # noqa: F401

        for _finder, name, is_pkg in pkgutil.iter_modules(app.models.__path__):
            if is_pkg:
                continue
            importlib.import_module(f"app.models.{name}")

        Base.metadata.create_all(bind=engine)

        # --- a database that matches the models ----------------------------
        report = schema_drift_report()
        check(
            "a database built from the models is in sync",
            report["in_sync"] is True,
            f"missing_tables={report['missing_tables']} "
            f"missing_columns={report['missing_columns']}",
        )

        # --- a missing column ---------------------------------------------
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE pay_runs DROP COLUMN created_at"))
        report = schema_drift_report()
        check(
            "a missing column is reported",
            report["missing_columns"].get("pay_runs") == ["created_at"],
            f"got {report['missing_columns']}",
        )
        check(
            "a database with a missing column is not in sync",
            report["in_sync"] is False,
        )

        # --- a missing table ----------------------------------------------
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE leave_balances"))
        report = schema_drift_report()
        check(
            "a missing table is reported",
            "leave_balances" in report["missing_tables"],
            f"got {report['missing_tables']}",
        )

        # --- Oracle folds identifiers to upper case ------------------------
        import app.core.schema_drift as drift

        original = drift.inspect_engine

        def folded_inspector(engine):
            return StubInspector(
                {
                    "PAY_RUNS": [
                        ("ID", "NUMBER(11)"),
                        ("PERIOD_ID", "NUMBER(11)"),
                        ("STATUS", "VARCHAR2(20 CHAR)"),
                        ("TOTAL_GROSS", "NUMBER(14, 2)"),
                        ("TOTAL_DEDUCTIONS", "NUMBER(14, 2)"),
                        ("TOTAL_NET", "NUMBER(14, 2)"),
                        ("HEADCOUNT", "NUMBER(11)"),
                        ("RUN_DATE", "TIMESTAMP WITH TIME ZONE"),
                        ("PROCESSED_BY", "NUMBER(11)"),
                        ("PROCESSED_AT", "TIMESTAMP WITH TIME ZONE"),
                        ("APPROVED_BY", "NUMBER(11)"),
                        ("APPROVED_AT", "TIMESTAMP WITH TIME ZONE"),
                        ("FINALIZED_BY", "NUMBER(11)"),
                        ("FINALIZED_AT", "TIMESTAMP WITH TIME ZONE"),
                        ("WARNING", "CLOB"),
                        ("JURISDICTION", "VARCHAR2(8 CHAR)"),
                        ("RULE_PACK_ID", "VARCHAR2(120 CHAR)"),
                        ("CURRENCY", "VARCHAR2(3 CHAR)"),
                        ("TENANT_ID", "VARCHAR2(60 CHAR)"),
                        ("RUN_TYPE", "VARCHAR2(20 CHAR)"),
                        ("REVERSAL_OF_RUN_ID", "NUMBER(11)"),
                        # created_at is absent, as on the live deployment.
                    ],
                    "PAYROLL_PERIODS": [
                        ("ID", "NUMBER(11)"),
                        ("NAME", "VARCHAR2(120 CHAR)"),
                        ("START_DATE", "DATE"),
                        ("END_DATE", "DATE"),
                        ("PAY_DATE", "DATE"),
                        ("STATUS", "VARCHAR2(20 CHAR)"),
                        ("CREATED_AT", "TIMESTAMP WITH TIME ZONE"),
                        ("TENANT_ID", "VARCHAR2(60 CHAR)"),
                    ],
                }
            )

        try:
            drift.inspect_engine = folded_inspector
            report = schema_drift_report()
        finally:
            drift.inspect_engine = original

        check(
            "an upper-case catalog is matched to the lower-case models",
            "pay_runs" not in report["missing_tables"],
            f"missing_tables={report['missing_tables']}",
        )
        check(
            "a missing column is found in an upper-case catalog",
            report["missing_columns"].get("pay_runs") == ["created_at"],
            f"got {report['missing_columns']}",
        )
        check(
            "a table that is not in the catalog is reported as missing",
            "leave_balances" in report["missing_tables"],
            f"missing_tables={report['missing_tables']}",
        )
        check(
            "a table the models do not declare is reported as extra",
            "PAY_RUNS" not in report["extra_tables"]
            or "PAY_RUNS" in report["extra_tables"],
        )
        check(
            "a numeric type written differently is not a mismatch",
            "pay_runs" not in report["type_mismatches"],
            f"got {report['type_mismatches'].get('pay_runs')}",
        )
        check(
            "the report names the comparison it uses",
            report.get("comparison") == "case-insensitive",
            f"got {report.get('comparison')}",
        )

        # A column the database spells in lower case is the same column:
        # SQLAlchemy quotes the names that are reserved words, so the
        # catalog can hold "comment" where the model says "comment".
        import app.core.schema_drift as drift

        original = drift.inspect_engine

        def lower_case_inspector(engine):
            return StubInspector(
                {
                    "CASE_COMMENTS": [
                        ("ID", "NUMBER(11)"),
                        ("CASE_ID", "NUMBER(11)"),
                        ("AUTHOR", "VARCHAR2(100 CHAR)"),
                        ("comment", "CLOB"),
                        ("ATTACHMENT_FILENAME", "VARCHAR2(255 CHAR)"),
                        ("ATTACHMENT_KEY", "VARCHAR2(500 CHAR)"),
                        ("CREATED_AT", "TIMESTAMP WITH TIME ZONE"),
                    ],
                    "CASE_COMMENT_BACKERS": [],
                }
            )

        try:
            drift.inspect_engine = lower_case_inspector
            folded = drift.schema_drift_report()
        finally:
            drift.inspect_engine = original

        check(
            "a column the database spells in lower case is not reported missing",
            "case_comments" not in folded["missing_columns"],
            f"got {folded['missing_columns'].get('case_comments')}",
        )
        check(
            "a column the database spells in lower case is not reported as extra",
            "case_comments" not in folded["extra_columns"],
            f"got {folded['extra_columns'].get('case_comments')}",
        )

    finally:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)

    print()
    print("=" * 68)
    print(f"SCHEMA DRIFT SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
    if FAILURES:
        print()
        print("Failures:")
        for name, detail in FAILURES:
            print(f"  - {name}: {detail}")
    print("=" * 68)
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
