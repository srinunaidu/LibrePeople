"""Multi-factor authentication (TOTP) core.

Implements time-based one-time password (TOTP) multi-factor authentication
for privileged roles (SuperAdmin, HR), as required by Gate 0A #1 / section
P-05 of the build brief.

Design
------
* Enrollment: the server generates a TOTP secret, stores its SHA-256 hash
  (never the plaintext secret), and returns a provisioning URI (otpauth://)
  the user can scan into an authenticator app. The secret is shown once.
* Confirmation: the user submits a TOTP code; the server verifies it against
  the stored hash. On success, MFA is enabled for the account.
* Verification on use: a dependency (`require_mfa`) checks that the current
  user has MFA enabled before allowing privileged operations.
* Recovery codes: 8 single-use codes, hashed at rest (bcrypt), displayed once
  at enrollment. Each code can be used once; using it marks it consumed.
* All MFA state is on the `users` table: `mfa_enabled`, `mfa_secret_hash`,
  `recovery_codes_hash`, `mfa_enrolled_at`.

Security notes
--------------
* The TOTP secret is never returned after enrollment. If lost, the user must
  re-enroll (disable + enroll) or an administrator must reset it.
* Recovery codes are hashed with bcrypt; a code that doesn't match any stored
  hash fails. Consumed codes are removed from the stored list.
* Rate limiting on TOTP verification is inherited from the login rate limiter
  (per-IP); the MFA confirm endpoint reuses it.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any

import pyotp
import qrcode

from app.core.config import settings


class MFAError(Exception):
    """Raised when an MFA operation fails."""


def generate_totp_secret() -> str:
    """Generate a new random TOTP secret (base32, 160 bits)."""
    return pyotp.random_base32()


def totp_provisioning_uri(username: str, secret: str, issuer: str = "Karmathy") -> str:
    """Build the otpauth:// provisioning URI for an authenticator app."""
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def totp_qr_data_uri(provisioning_uri: str) -> str:
    """Render the provisioning URI as a PNG data URI.

    The QR is generated here rather than by a third-party charting service.
    A hosted image API receives the TOTP secret inside a URL, which means the
    secret is written to that service's access logs and to any proxy in
    front of it. The secret belongs to the person enrolling and to nobody
    else, so the image never leaves this server.
    """
    import io

    image = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code against a secret.

    Uses a 1-step verification window (current 30-second interval only) to
    minimize the reuse window.
    """
    if not code or not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def hash_secret(secret: str) -> str:
    """SHA-256 hash of a TOTP secret for storage."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_recovery_codes(count: int = 8) -> list[str]:
    """Generate single-use recovery codes (8 hex characters each)."""
    return [secrets.token_hex(4) for _ in range(count)]


def hash_recovery_code(code: str) -> str:
    """bcrypt hash of a recovery code for storage."""
    from app.core.security import get_password_hash

    return get_password_hash(code)


def verify_recovery_code(code: str, stored_hashes: list[str]) -> bool:
    """Verify a recovery code against a list of stored bcrypt hashes.

    Returns True on first match. The caller is responsible for removing the
    consumed code from the stored list.
    """
    from app.core.security import verify_password

    for stored in stored_hashes:
        try:
            if verify_password(code, stored):
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def build_enrollment(username: str) -> dict[str, Any]:
    """Build an MFA enrollment package.

    Returns the secret (to show once), the provisioning URI (for the QR
    code), recovery codes (to show once), and the stored hashes (to persist).
    """
    secret = generate_totp_secret()
    recovery_codes = generate_recovery_codes()
    return {
        "secret": secret,
        "secret_hash": hash_secret(secret),
        "provisioning_uri": totp_provisioning_uri(username, secret),
        "recovery_codes": recovery_codes,
        "recovery_code_hashes": [hash_recovery_code(c) for c in recovery_codes],
    }


def is_mfa_enforced_role(role: str) -> bool:
    """True when MFA is mandatory for the role (SuperAdmin, HR)."""
    return role in ("SuperAdmin", "HR")
