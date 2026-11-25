#!/usr/bin/env python3
"""
Import hr_linked_dataset_650_csvs data into production Oracle database.

Steps:
1. Drop and recreate target tables (clean slate)
2. Reset identity sequences to start at 1
3. Load CSV files without specifying ID (let Oracle auto-generate)
4. Handle leave_balances cross-references by looking up employee_id and code

Usage:
    KARMA_SEED_RESET=yes python3 scripts/import_csv_production.py
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
backend_path = repo_root / "backend"
sys.path.insert(0, str(backend_path))
os.chdir(backend_path)

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session

ORACLE_DSN = os.environ.get("ORACLE_DSN", "karmkathyadb_high")
ORACLE_USER = os.environ.get("ORACLE_USER", "admin")
ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", "")
ORACLE_WALLET_DIR = os.environ.get("ORACLE_WALLET_DIR", "")
ORACLE_WALLET_PASSWORD = os.environ.get("ORACLE_WALLET_PASSWORD", "")

CSV_DIR = Path(os.environ.get("CSV_DIR", repo_root.parent / "hr_linked_dataset_650_csvs"))

connect_args = {
    "config_dir": ORACLE_WALLET_DIR,
    "wallet_location": ORACLE_WALLET_DIR,
    "user": ORACLE_USER,
    "password": ORACLE_PASSWORD,
    "dsn": ORACLE_DSN,
}
if ORACLE_WALLET_PASSWORD:
    connect_args["wallet_password"] = ORACLE_WALLET_PASSWORD

engine = create_engine(
    "oracle+oracledb://:@",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args,
)

TABLE_ORDER = [
    "departments",
    "locations",
    "leave_types",
    "jobs",
    "shift_templates",
    "cost_centers",
    "pay_components",
    "compliance_rules",
    "benefit_plans",
    "courses",
    "candidates",
    "employees",
    "leave_balances",
]

CSV_FILES = {
    "departments": "departments.csv",
    "locations": "locations.csv",
    "leave_types": "leave_types.csv",
    "jobs": "jobs.csv",
    "shift_templates": "shift_templates.csv",
    "cost_centers": "cost_centers.csv",
    "pay_components": "pay_components.csv",
    "compliance_rules": "compliance_rules.csv",
    "benefit_plans": "benefit_plans.csv",
    "courses": "courses.csv",
    "candidates": "candidates.csv",
    "employees": "employees.csv",
    "leave_balances": "leave_balances.csv",
}

COLUMN_MAP = {
    "departments": {"name": "name", "code": "code", "description": "description", "is_active": "is_active"},
    "locations": {"name": "name", "code": "code", "address": "address", "city": "city", "country": "country", "timezone": "timezone", "is_active": "is_active"},
    "leave_types": {"name": "name", "code": "code", "is_paid": "is_paid", "max_days_per_year": "max_days_per_year", "is_active": "is_active"},
    "jobs": {"title": "title", "code": "code", "department_id": "department_id", "min_salary": "min_salary", "max_salary": "max_salary", "is_active": "is_active"},
    "shift_templates": {"name": "name", "code": "code", "start_time": "start_time", "end_time": "end_time", "break_minutes": "break_minutes", "is_night": "is_night", "is_active": "is_active"},
    "cost_centers": {"code": "code", "name": "name", "department_id": "department_id", "is_active": "is_active"},
    "pay_components": {"code": "code", "name": "name", "component_type": "component_type", "is_taxable": "is_taxable", "is_pre_tax": "is_pre_tax", "is_active": "is_active"},
    "compliance_rules": {"code": "code", "name": "name", "category": "category", "description": "description", "severity": "severity", "is_active": "is_active"},
    "benefit_plans": {"name": "name", "code": "code", "plan_type": "plan_type", "provider": "provider", "employer_contribution": "employer_contribution", "employee_contribution": "employee_contribution", "is_active": "is_active"},
    "courses": {"title": "title", "code": "code", "description": "description", "category": "category", "duration_hours": "duration_hours", "is_mandatory": "is_mandatory", "is_active": "is_active"},
    "candidates": {"first_name": "first_name", "last_name": "last_name", "email": "email", "phone": "phone", "source": "source", "status": "status"},
    "employees": {"employee_id": "employee_id", "first_name": "first_name", "last_name": "last_name", "email": "email", "phone": "phone", "hire_date": "hire_date", "job_id": "job_id", "department_id": "department_id", "manager_id": "manager_id", "status": "status", "salary": "salary"},
    "leave_balances": {"employee_number": "emp_num_raw", "leave_type_code": "lt_code_raw", "entitlement_year": "entitlement_year", "entitled_days": "entitled_days", "carried_over_days": "carried_over_days", "used_days": "used_days"},
}

BOOLEAN_TRUE = {"true", "1", "yes", "y", "t"}


def _to_bool(val):
    if val is None:
        return None
    return str(val).strip().lower() in BOOLEAN_TRUE


def _to_int(val):
    if val is None or str(val).strip() == "":
        return None
    return int(float(str(val).strip()))


def _to_float(val):
    if val is None or str(val).strip() == "":
        return None
    return float(str(val).strip())


def drop_tables() -> None:
    """Drop all target tables and their constraints."""
    print("Dropping existing tables...")
    with engine.begin() as conn:
        for table in reversed(TABLE_ORDER):
            try:
                conn.execute(
                    text(
                        f"""
                        BEGIN
                          FOR c IN (SELECT constraint_name FROM user_constraints
                                    WHERE table_name = UPPER('{table}')
                                    AND constraint_type = 'R') LOOP
                            EXECUTE IMMEDIATE 'ALTER TABLE {table} DISABLE CONSTRAINT ' || c.constraint_name;
                          END LOOP;
                        END;
                        """
                    )
                )
            except Exception:
                pass

        for table in reversed(TABLE_ORDER):
            try:
                conn.execute(text(f"DROP TABLE {table} CASCADE CONSTRAINTS"))
                print(f"  {table}: dropped")
            except Exception as exc:
                print(f"  {table}: SKIP ({exc})")

    print("Tables dropped.\n")


def recreate_tables() -> None:
    """Recreate tables using SQLAlchemy metadata."""
    print("Recreating tables...")

    import app.models  # noqa: F401
    from app.models import (
        audit, benefits, client_onboarding, compliance, core_hr, department,
        employee, ess_hr, integrations_platform, job, learning, leave, offboarding,
        onboarding, payroll, performance, recruiting, refresh_token, scheduling,
        time_attendance, user,
    )
    from app.models.base import Base

    target_tables = {t.upper() for t in TABLE_ORDER}
    tables_to_create = [
        t for t in Base.metadata.sorted_tables
        if t.name.upper() in target_tables
    ]

    with engine.begin() as conn:
        for table in tables_to_create:
            try:
                table.create(conn, checkfirst=True)
                print(f"  {table.name}: created")
            except Exception as exc:
                print(f"  {table.name}: SKIP ({exc})")

    # Reset identity sequences to start at 1
    print("\nResetting identity sequences...")
    with engine.begin() as conn:
        for table in TABLE_ORDER:
            try:
                conn.execute(
                    text(
                        f"""
                        BEGIN
                          FOR s IN (SELECT sequence_name FROM user_sequences
                                    WHERE sequence_name = UPPER('{table}_SEQ')) LOOP
                            EXECUTE IMMEDIATE 'ALTER SEQUENCE ' || s.sequence_name ||
                              ' INCREMENT BY -999999';
                            EXECUTE IMMEDIATE 'SELECT ' || s.sequence_name || '.NEXTVAL FROM DUAL';
                            EXECUTE IMMEDIATE 'ALTER SEQUENCE ' || s.sequence_name ||
                              ' INCREMENT BY 1';
                          END LOOP;
                        END;
                        """
                    )
                )
            except Exception:
                pass

    print("Tables created.\n")


def load_csv(table: str) -> list[dict]:
    csv_file = CSV_DIR / CSV_FILES[table]
    if not csv_file.exists():
        print(f"  {table}: SKIPPED (CSV not found: {CSV_FILES[table]})")
        return []
    with open(csv_file, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def import_table(
    table: str,
    db: Session,
    lookups: dict | None = None,
) -> int:
    """Import one CSV file into one table. ID is auto-generated by Oracle."""
    rows = load_csv(table)
    if not rows:
        return 0

    col_map = COLUMN_MAP[table]
    count = 0

    for row in rows:
        params = {}
        inline_parts = {}

        for csv_col, db_col in col_map.items():
            val = row.get(csv_col, "").strip()
            if val == "":
                params[db_col] = None
                continue

            if db_col in ("is_active", "is_paid", "is_taxable", "is_pre_tax", "is_mandatory", "is_night"):
                params[db_col] = str(val).strip().lower() in BOOLEAN_TRUE
            elif db_col in (
                "department_id", "job_id", "manager_id", "min_salary", "max_salary",
                "break_minutes", "max_days_per_year", "employer_contribution",
                "employee_contribution", "duration_hours",
            ):
                params[db_col] = _to_int(val)
            elif db_col in ("entitled_days", "carried_over_days", "used_days", "salary"):
                params[db_col] = _to_float(val)
            elif db_col == "hire_date":
                inline_parts[db_col] = f"TO_DATE('{val}', 'YYYY-MM-DD')"
            else:
                params[db_col] = val

        if table == "leave_balances" and lookups:
            emp_num = row.get("employee_number", "").strip()
            lt_code = row.get("leave_type_code", "").strip()
            emp_id = lookups["employee_map"].get(emp_num)
            lt_id = lookups["leave_type_map"].get(lt_code)
            if emp_id is None:
                continue
            if lt_id is None:
                continue
            params["employee_id"] = emp_id
            params["leave_type_id"] = lt_id
            params.pop("emp_num_raw", None)
            params.pop("lt_code_raw", None)

        # Build INSERT
        all_cols = list(params.keys()) + list(inline_parts.keys())
        param_vals = ", ".join(f":{k}" for k in params.keys())
        inline_vals = ", ".join(inline_parts.values())
        if param_vals and inline_vals:
            vals = f"{param_vals}, {inline_vals}"
        elif param_vals:
            vals = param_vals
        else:
            vals = inline_vals
        cols = ", ".join(all_cols)
        sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
        try:
            db.execute(text(sql), params)
            count += 1
        except Exception as exc:
            print(f"    ERROR: {exc}")

    db.commit()
    print(f"  {table}: imported {count} rows")
    return count


def main() -> int:
    reset = os.environ.get("KARMA_SEED_RESET", "").strip().lower() == "yes"
    if not reset:
        print("ERROR: Set KARMA_SEED_RESET=yes to confirm destructive cleanup of production data.")
        return 1

    print(f"CSV directory: {CSV_DIR}")
    print(f"Files found: {len(list(CSV_DIR.glob('*.csv')))}")
    print()

    missing = [CSV_FILES[t] for t in TABLE_ORDER if not (CSV_DIR / CSV_FILES[t]).exists()]
    if missing:
        print(f"ERROR: Missing CSV files: {missing}")
        return 1

    drop_tables()
    recreate_tables()

    db = Session(bind=engine)
    try:
        # Phase 1: Import all tables except leave_balances
        phase1_tables = [t for t in TABLE_ORDER if t != "leave_balances"]
        total = 0
        for table in phase1_tables:
            n = import_table(table, db, lookups={})
            total += n

        # Phase 2: Build lookups for leave_balances cross-references
        lookups = {}
        rows = db.execute(text("SELECT employee_id, id FROM employees")).fetchall()
        lookups["employee_map"] = {r[0]: r[1] for r in rows}
        rows = db.execute(text("SELECT code, id FROM leave_types")).fetchall()
        lookups["leave_type_map"] = {r[0]: r[1] for r in rows}

        # Phase 3: Import leave_balances
        n = import_table("leave_balances", db, lookups=lookups)
        total += n

        print(f"\nTotal imported: {total} rows across {len(TABLE_ORDER)} tables")
    finally:
        db.close()

    print("\nImport complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
