"""Postgres driver regression tests (render-watch / deploy fix).

Render deploy dep-dc3hph49v7es73875p8g (2026-11-25, SHA 8688183) failed in
`preDeployCommand` (`python -m scripts.migrate upgrade`) with::

    ModuleNotFoundError: No module named 'psycopg2'

The backend image installs only `backend/requirements.txt`, which carried
the Oracle driver (`oracledb`) but no Postgres driver, while the Render
testing deploy points `DATABASE_URL` at Neon Postgres. SQLAlchemy's default
`postgresql://` dialect needs `psycopg2`, so engine import died before any
migration ran. These tests pin the driver in both directions: declared in
requirements, and importable as the default Postgres DBAPI.
"""

import pathlib

_REQUIREMENTS = pathlib.Path(__file__).resolve().parents[1] / "requirements.txt"


def _requirement_lines():
    return [
        line.split("#", 1)[0].strip()
        for line in _REQUIREMENTS.read_text().splitlines()
    ]


def test_requirements_declares_psycopg2_binary():
    lines = _requirement_lines()
    assert any(
        line.startswith("psycopg2-binary==") for line in lines
    ), "requirements.txt must pin psycopg2-binary for the Neon DATABASE_URL"


def test_psycopg2_dbapi_importable():
    # This is the exact import SQLAlchemy's default postgresql dialect
    # performs at engine creation on Render (database.py: create_engine).
    import psycopg2  # noqa: F401


def test_default_postgres_dialect_resolves_to_psycopg2():
    from sqlalchemy.dialects.postgresql.psycopg2 import dialect as pg_dialect

    assert pg_dialect.driver == "psycopg2"
