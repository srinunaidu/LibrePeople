"""Helpers for writing audit trail entries.

Audit rows are added to the current session and committed together with the
operation they describe, so an action and its audit entry stay atomic.

Three properties are enforced here rather than left to each call site:

* **The source address is recorded**, as a SHA-256 digest, from the request
  the middleware is serving. An action outside a request (a seed, a job)
  carries none.
* **Sensitive values are redacted** from ``details`` before they reach the
  column. The audit trail must not become the place a salary, a bank detail,
  a national identifier or a date of birth is copied into a second table
  with weaker access control than the one it came from.
* **The entry is chained.** ``prev_hash`` and ``entry_hash`` are written with
  the row, so the trail is tamper-evident; see :mod:`app.core.audit_chain`
  for the canonical form and the verification command.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.core.audit_chain import append_entry
from app.core.observability import get_client_ip_hash
from app.core.tenancy import tenant_id_for
from app.models.audit import AuditLog
from app.models.user import User

#: ``key=value`` pairs whose value is personal or financial data. The key is
#: kept, because "a salary changed" is the fact the trail exists to record;
#: the value is not.
_SENSITIVE_DETAIL_KEY = re.compile(
    r"(?i)\b("
    r"salary|base_salary|gross_pay|net_pay|bank|bank_account|account_number|"
    r"iban|sort_code|routing_number|ssn|social_security|national_id|"
    r"national_insurance|tax_id|date_of_birth|dob|card_number|cvv"
    r")\b(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)

#: A run of 12 to 19 digits is a card or account number. Dates (8 digits with
#: separators) and short counts (a retry-after) do not match.
_LONG_DIGITS = re.compile(r"\b\d{12,19}\b")

REDACTED = "[redacted]"


def redact_details(details: str | None) -> str | None:
    """Remove personal and financial values from an audit detail string.

    The key survives, the value does not. A detail that carries no sensitive
    value is returned unchanged.
    """
    if not details:
        return details
    cleaned = _SENSITIVE_DETAIL_KEY.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", details
    )
    return _LONG_DIGITS.sub(REDACTED, cleaned)


def record_audit(
    db: Session,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: str | None = None,
    break_glass_grant_id: int | None = None,
) -> AuditLog:
    """Stage a chained audit entry on the session (commit with the operation).

    Captures the request's resolved tenant id (from the tenancy context) so
    every audited write is attributable to a tenant, and the break-glass
    grant id when the action was authorized by a break-glass grant.
    """
    return append_entry(
        db,
        actor_id=getattr(actor, "id", None),
        actor_name=getattr(actor, "username", None),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=redact_details(details),
        source_ip_hash=get_client_ip_hash(),
        tenant_id=tenant_id_for(db),
        break_glass_grant_id=break_glass_grant_id,
    )
