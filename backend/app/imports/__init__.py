"""The CSV import engine.

The pieces, in the order the data flows through them:

``spec``
    The contract. What columns each entity has, what type they are, which
    values are allowed, which point at another entity, and which hold
    personal data that must never be echoed back.
``headers``
    Turning the header row into canonical column names, and making a cell
    safe to open in a spreadsheet.
``parser``
    Streaming RFC 4180 reading with the size and row limits enforced while
    the file is read.
``validation``
    Turning a cell into a value, and saying why it could not be one.
``analyse``
    The whole file, without writing anything. This is what the dry run
    runs and what the commit re-runs.
``apply``
    Writing the rows, as an upsert on the entity's natural key.
``runner``
    The dry run, the confirmation token, and the single-transaction commit.
``templates``
    The header row and example row an operator downloads.
"""
from app.imports.spec import (  # noqa: F401
    CORE_ENTITIES,
    ENTITIES,
    ColumnSpec,
    EntitySpec,
    entity_models,
    get_spec,
)

__all__ = [
    "CORE_ENTITIES",
    "ENTITIES",
    "ColumnSpec",
    "EntitySpec",
    "entity_models",
    "get_spec",
]
