"""Exercise the forecasting migration against a database that already has
the forecasting tables — the production situation, where the tables were
created before Alembic existed.

Run from the backend directory:

    SECRET_KEY=... DATABASE_URL=sqlite:///./mig_test.db \
        .venv/bin/python scripts/mig_probe.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, inspect, text  # noqa: E402


def table_names(url: str) -> set[str]:
    engine = create_engine(url)
    with engine.connect() as conn:
        names = set(inspect(conn).get_table_names())
    engine.dispose()
    return names


def main() -> None:
    url = os.environ.get("DATABASE_URL", "sqlite:///./mig_probe.db")
    path = Path(url.replace("sqlite:///", "", 1))
    if path.exists():
        path.unlink()

    from app.core.database import Base, engine  # noqa: E402
    from app.core.migrations import run_pending_migrations  # noqa: E402

    # Import every model module, the way the Alembic environment does, so
    # create_all() really does build the forecast tables.
    import importlib
    import pkgutil

    import app.models

    for _finder, _name, _ispkg in pkgutil.iter_modules(app.models.__path__):
        if _ispkg:
            continue
        importlib.import_module(f"app.models.{_name}")

    # Simulate the legacy production database: the tables exist but there
    # is no migration history.
    print("[probe] creating the schema with create_all()...")
    Base.metadata.create_all(bind=engine)
    print("[probe] tables:", sorted(t for t in table_names(url) if "forecast" in t))

    print("[probe] running migrations...")
    state = run_pending_migrations()
    print("[probe] revision:", state.get("current_revision"))

    print("[probe] tables after:", sorted(t for t in table_names(url) if "forecast" in t))

    print("[probe] running migrations a second time (idempotency)...")
    state = run_pending_migrations()
    print("[probe] revision:", state.get("current_revision"))

    with engine.connect() as conn:
        conn.execute(text("SELECT COUNT(*) FROM forecast_runs"))
        conn.execute(text("SELECT COUNT(*) FROM forecast_results"))
        conn.execute(text("SELECT COUNT(*) FROM forecast_model_versions"))
    print("[probe] the three forecast tables are queryable")

    print("PROBE OK")


if __name__ == "__main__":
    main()
