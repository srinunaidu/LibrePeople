"""Validate, store and mask configurable employee fields (LP-CORE-005).

A definition declares the type, whether a value is required, whether it
is personal (``is_sensitive``) and who may see it (``visibility``). Every
write path — the employee endpoints and the CSV importer — validates
through :func:`validate_value` and stores through :func:`set_values`, so
the rules cannot be bypassed by choosing a different door. Every read
path renders through :func:`visible_fields`, so a personal value never
leaks through a directory read, an export, or a row-error message.

Storage
-------
Values are stored as text. Dates are ISO 8601, booleans the canonical
``true``/``false`` spelling, numbers their plain decimal form — the same
spellings the CSV importer accepts, so an export can be re-imported
without changing a header.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.core.booleans import is_true
from app.core.tenancy import tenant_id_for, tenant_matches
from app.imports.headers import neutralise_formula_injection
from app.models.custom_field import FIELD_TYPES, VISIBILITIES, CustomFieldDef

#: Roles that may manage definitions and see every value. Mirrors
#: :mod:`app.core.sensitive_fields` so the policy can be read off in one
#: place.
PRIVILEGED_ROLES: frozenset[str] = frozenset({"HR", "SuperAdmin"})

#: The import/export prefix. ``custom.tshirt_size`` names the definition
#: whose key is ``tshirt_size`` (matched case-insensitively).
PREFIX = "custom."


class CustomFieldError(ValueError):
    """One rejected custom-field value, naming the definition key.

    ``code`` mirrors :class:`app.imports.errors.ErrorCode` so the CSV
    importer can report the failure without re-interpreting it.
    """

    def __init__(self, key: str, message: str, code: str = "validation_error") -> None:
        super().__init__(message)
        self.key = key
        self.message = message
        self.code = code


def normalize_key(raw: str | None) -> str | None:
    """The definition key for an import/export header, or ``None``.

    ``custom.TShirt_Size`` resolves to the definition ``tshirt_size``.
    Anything without the ``custom.`` prefix is not a custom field.
    """
    if raw is None:
        return None
    text = raw.strip()
    if text.lower().startswith(PREFIX):
        key = text[len(PREFIX):].strip().lower()
        return key or None
    return None


def _tenant_scope(defs: list[CustomFieldDef], db: Session) -> list[CustomFieldDef]:
    """Keep the definitions visible to this request's tenant."""
    tenant_id = tenant_id_for(db)
    if tenant_id is None:
        return defs
    return [
        d for d in defs if tenant_matches(getattr(d, "tenant_id", None), tenant_id)
    ]


def list_defs(db: Session, *, active_only: bool = True) -> list[CustomFieldDef]:
    """Every definition this request's tenant may use, ordered by key."""
    query = db.query(CustomFieldDef).order_by(CustomFieldDef.key.asc())
    if active_only:
        query = query.filter(is_true(CustomFieldDef.is_active))
    return _tenant_scope(query.all(), db)


def def_map(db: Session, *, active_only: bool = True) -> dict[str, CustomFieldDef]:
    """Active definitions keyed by lowercased key."""
    return {d.key.lower(): d for d in list_defs(db, active_only=active_only)}


def validate_value(defn: CustomFieldDef, raw: Any) -> str | None:
    """Coerce ``raw`` to the stored text form, or raise :class:`CustomFieldError`.

    ``None`` and a blank string clear the value — unless the definition is
    required, in which case clearing is refused. The error message names
    the rule, never the rejected value when the definition is sensitive.
    """
    key = defn.key
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        if defn.required:
            raise CustomFieldError(key, f"'{key}' is required.", "missing_required")
        return None
    kind = (defn.field_type or "text").lower()
    if kind not in FIELD_TYPES:
        raise CustomFieldError(key, f"'{key}' has an unknown type '{defn.field_type}'.")
    if isinstance(raw, bool):
        text = "true" if raw else "false"
    else:
        text = str(raw).strip()

    def _masked(template: str, code: str) -> CustomFieldError:
        if defn.is_sensitive:
            return CustomFieldError(key, template.format(key=key), code)
        return CustomFieldError(key, template.format(key=key, value=text), code)

    if kind == "text":
        if len(text) > 500:
            raise _masked("'{key}' must be at most 500 characters.", "too_long")
        return neutralise_formula_injection(text)
    if kind == "email":
        if "@" not in text or len(text) > 255:
            raise _masked("'{key}' must be a valid email address.", "invalid_email")
        return text
    if kind == "integer":
        try:
            return str(int(Decimal(text)))
        except (InvalidOperation, ValueError):
            raise _masked("'{key}' must be a whole number.", "invalid_integer")
    if kind == "number":
        try:
            value = Decimal(text)
        except InvalidOperation:
            raise _masked("'{key}' must be a number.", "invalid_number")
        if value.is_nan():
            raise _masked("'{key}' must be a number.", "invalid_number")
        return format(value, "f")
    if kind == "boolean":
        lowered = text.lower()
        if lowered in ("1", "true", "yes", "y", "t", "on"):
            return "true"
        if lowered in ("0", "false", "no", "n", "f", "off"):
            return "false"
        raise _masked("'{key}' must be true or false.", "invalid_boolean")
    if kind == "date":
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                parsed = datetime.strptime(text, fmt)
                return parsed.date().isoformat() if fmt != "%Y-%m-%d" else text
            except ValueError:
                continue
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError:
            raise _masked("'{key}' must be an ISO 8601 date (YYYY-MM-DD).", "invalid_date")
    return text  # pragma: no cover - guarded by the FIELD_TYPES check


def validate_all(
    values: dict[str, Any] | None,
    defs: dict[str, CustomFieldDef],
) -> dict[str, str | None]:
    """Coerce every supplied value, raising on the first unknown key or
    invalid value — before anything is written."""
    coerced: dict[str, str | None] = {}
    for raw_key, raw_value in (values or {}).items():
        key = (raw_key or "").strip().lower()
        defn = defs.get(key)
        if defn is None:
            raise CustomFieldError(raw_key, f"Unknown custom field '{raw_key}'.")
        coerced[defn.key.lower()] = validate_value(defn, raw_value)
    return coerced


def set_values(
    db: Session,
    employee_id: int,
    values: dict[str, Any] | None,
    defs: dict[str, CustomFieldDef] | None = None,
) -> None:
    """Validate and stage custom-field values for one employee.

    Unknown keys and values that fail :func:`validate_value` raise
    :class:`CustomFieldError` before anything is staged. A ``None`` value
    clears the stored row. The rows are flushed, not committed — the
    caller owns the transaction.
    """
    from app.models.custom_field import CustomFieldValue

    if not values:
        return
    known = defs if defs is not None else def_map(db)
    staged: dict[str, str | None] = {}
    for raw_key, raw_value in values.items():
        key = (raw_key or "").strip().lower()
        defn = known.get(key)
        if defn is None:
            raise CustomFieldError(raw_key, f"Unknown custom field '{raw_key}'.")
        staged[defn.key.lower()] = validate_value(defn, raw_value)

    tenant_id = tenant_id_for(db)
    for lowered, value_text in staged.items():
        defn = known[lowered]
        row = (
            db.query(CustomFieldValue)
            .filter(
                CustomFieldValue.employee_id == employee_id,
                CustomFieldValue.def_id == defn.id,
            )
            .first()
        )
        if value_text is None:
            if row is not None:
                db.delete(row)
            continue
        if row is None:
            row = CustomFieldValue(
                tenant_id=tenant_id,
                employee_id=employee_id,
                def_id=defn.id,
                value_text=value_text,
            )
            db.add(row)
        else:
            row.value_text = value_text
    db.flush()


def read_values(
    db: Session, employee_ids: list[int]
) -> dict[int, dict[str, str]]:
    """Stored custom values, keyed by employee id then definition key."""
    from app.models.custom_field import CustomFieldValue

    if not employee_ids:
        return {}
    rows = (
        db.query(CustomFieldValue, CustomFieldDef.key)
        .join(CustomFieldDef, CustomFieldDef.id == CustomFieldValue.def_id)
        .filter(CustomFieldValue.employee_id.in_(employee_ids))
        .all()
    )
    out: dict[int, dict[str, str]] = {}
    for value_row, key in rows:
        if value_row.value_text is None:
            continue
        out.setdefault(value_row.employee_id, {})[key] = value_row.value_text
    return out


def visible_fields(
    stored: dict[str, str] | None,
    defs: dict[str, CustomFieldDef] | None,
    role: str | None,
) -> dict[str, str | None]:
    """Render stored values for ``role`` (LP-CORE-005 access rules).

    * ``visibility == "hr_only"`` and a non-privileged role: the key is
      omitted entirely — the caller cannot tell whether a value exists.
    * ``is_sensitive`` and a non-privileged role: the key stays (the
      shape is stable) but the value is masked to ``None``.
    * A value whose definition is gone (or inactive) is never rendered:
      the directory must not serve data its own contract no longer
      describes.
    """
    if not stored:
        return {}
    known = defs or {}
    privileged = role in PRIVILEGED_ROLES
    out: dict[str, str | None] = {}
    for key, value in stored.items():
        defn = known.get((key or "").lower())
        if defn is None or not defn.is_active:
            continue
        if not privileged and (defn.visibility or "all").lower() == "hr_only":
            continue
        if not privileged and defn.is_sensitive:
            out[key] = None
            continue
        out[key] = value
    return out


def ensure_valid_def_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Check a definition create/update payload, raising ``ValueError``."""
    field_type = str(data.get("field_type", "text") or "text").lower()
    if field_type not in FIELD_TYPES:
        raise ValueError(
            f"field_type must be one of {', '.join(FIELD_TYPES)}."
        )
    visibility = str(data.get("visibility", "all") or "all").lower()
    if visibility not in VISIBILITIES:
        raise ValueError(f"visibility must be one of {', '.join(VISIBILITIES)}.")
    key = str(data.get("key", "") or "").strip().lower()
    if not key or len(key) > 60:
        raise ValueError("key must be 1-60 characters.")
    if not all(c.isalnum() or c == "_" for c in key):
        raise ValueError("key may only contain letters, digits and underscores.")
    cleaned = dict(data)
    cleaned["field_type"] = field_type
    cleaned["visibility"] = visibility
    cleaned["key"] = key
    return cleaned
