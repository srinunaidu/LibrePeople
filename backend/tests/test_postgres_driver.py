"""Postgres driver regression test (Agent E / Render deploy).

The testing deploy points DATABASE_URL at external Neon Postgres, so the
image must ship a Postgres DBAPI driver. The first Render deploy failed
with ``ModuleNotFoundError: No module named 'psycopg2'`` because
requirements.txt had no postgres driver while SQLAlchemy's
``postgresql://`` dialect defaults to psycopg2. These tests pin the
requirement: one guards the pin itself, the other proves SQLAlchemy can
actually load the driver.
"""

import re
from pathlib import Path

import pytest

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"

_DRIVER_RES = (
    re.compile(r"^psycopg2-binary==\S+", re.M),
    re.compile(r"^psycopg(\[binary\])?==\S+", re.M),
)


def test_requirements_pins_postgres_driver():
    text = REQUIREMENTS.read_text()
    assert any(rx.search(text) for rx in _DRIVER_RES), (
        "requirements.txt must pin a Postgres DBAPI driver "
        "(psycopg2-binary or psycopg[binary]); a Neon DATABASE_URL "
        "cannot connect without one"
    )


def test_sqlalchemy_can_load_postgres_dbapi():
    # Skipped where the driver is not installed (e.g. a local interpreter
    # with no wheel for its version); the pin test above still guards the
    # requirement. Runs for real in CI and in the Docker image.
    pytest.importorskip("psycopg2")
    from sqlalchemy.dialects import registry

    dialect_cls = registry.load("postgresql")
    # Accessing .dbapi imports the driver (psycopg2); without the
    # requirements pin this raises ImportError — the exact Render failure.
    assert dialect_cls.dbapi is not None
