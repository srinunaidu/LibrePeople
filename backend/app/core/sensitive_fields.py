"""Central access policy for bank account and tax identifier fields.

Product decision (LibrePeople Phase 2): bank account and tax identifier fields
are readable and writable by HR and SuperAdmin (owner-confirmed); PayrollViewer
has no access by default.

Every endpoint that reads or writes one of :data:`BANK_TAX_FIELDS` applies this
module, so the policy can be changed in one place:

* read: a denied role receives the response with the field value set to
  ``None`` (the field is omitted from the data the caller can see);
* write: a denied role that supplies a non-null value is refused with 403,
  before anything is stored.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.errors import forbidden

#: The roles that may read and write bank and tax identifier fields.
#: Change this one constant to change the policy everywhere.
BANK_TAX_ROLES: frozenset[str] = frozenset({"HR", "SuperAdmin"})

#: Every field governed by the policy, across employee, pay profile and ESS.
BANK_TAX_FIELDS: tuple[str, ...] = (
    "bank_name",
    "bank_account",
    "bank_routing",
    "ifsc_code",
    "tax_id",
    "pan_number",
)


def can_access_bank_tax(role: str | None) -> bool:
    """True when ``role`` may read or write bank and tax identifier fields."""
    return role in BANK_TAX_ROLES


def mask_bank_tax(data: Mapping[str, Any], role: str | None) -> dict[str, Any]:
    """Return a copy of ``data`` with the bank and tax fields removed for ``role``.

    The copy is returned unchanged for an allowed role. A denied role gets the
    governed fields set to ``None``.
    """
    out = dict(data)
    if can_access_bank_tax(role):
        return out
    for name in BANK_TAX_FIELDS:
        if name in out:
            out[name] = None
    return out


def refuse_bank_tax_write(values: Mapping[str, Any], role: str | None) -> None:
    """Refuse a write that sets a bank or tax field when ``role`` may not.

    ``values`` should contain only the fields the caller actually supplied
    (for example ``model_dump(exclude_unset=True)``), so an omitted field is
    never mistaken for a supplied one. An explicit ``null`` is allowed.
    """
    if can_access_bank_tax(role):
        return
    for name in BANK_TAX_FIELDS:
        if values.get(name) is not None:
            raise forbidden(
                "Your role does not permit changing bank or tax identifier fields."
            )
