"""Single source of truth for the SQLAlchemy declarative Base.

All models import Base from here, and it is the same object used by
`app.core.database` for `create_all` / Alembic metadata.
"""
from app.core.database import Base  # noqa: F401  (re-export)
