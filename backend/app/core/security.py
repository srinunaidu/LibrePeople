"""Cryptographic primitives: password hashing, JWT issuance, field encryption.

Three concerns live here, and each one has a failure mode that was present in
earlier revisions of this file and is now closed explicitly:

1. **JWT algorithm confusion.** The accepted algorithm used to be read from
   configuration, so a misconfigured deployment would accept a token signed
   with an algorithm the operator did not intend. The algorithm is now pinned
   to HS256 and any other value is rejected at startup.

2. **bcrypt's 72-byte truncation.** bcrypt silently ignores bytes past 72, so
   two different long passwords that share a 72-byte prefix are the same
   password. Passwords are now pre-hashed with SHA-256 and base64-encoded
   (44 bytes) before bcrypt sees them, which makes truncation impossible while
   keeping bcrypt's cost factor. The stored hash carries a scheme marker so
   legacy hashes can still be verified and are transparently upgraded on the
   next successful login.

3. **Silent decryption failure.** ``decrypt_secret`` used to return the
   ciphertext unchanged when decryption failed, which meant a caller could
   read a ciphertext as if it were a plaintext secret. Decryption now raises
   :class:`SecretDecryptionError` instead. Field encryption is versioned
   (``ENCv1:<key_id>:<token>``) so keys can be rotated without a data
   migration: the active key encrypts, and any key in the registry decrypts.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Union

import bcrypt
from jose import jwt

from app.core.config import settings

#: The only JWT signing algorithm this application accepts.
PINNED_JWT_ALGORITHM = "HS256"

#: Password hashing scheme marker. ``$krb1$<bcrypt>``.
#:
#: ``krb1`` = "karmathy bcrypt revision 1" — bcrypt over a SHA-256/base64
#: pre-hash. The pre-hash makes the input 44 bytes, so bcrypt never truncates.
PASSWORD_SCHEME = "krb1"
_PASSWORD_SCHEME_PREFIX = f"${PASSWORD_SCHEME}$"

#: Version tag for encrypted field values.
ENCRYPTION_VERSION = "ENCv1"
_ENCRYPTION_PREFIX = f"{ENCRYPTION_VERSION}:"


class SecretDecryptionError(Exception):
    """Raised when an encrypted field value cannot be decrypted.

    This is deliberately an exception rather than a fallback. Returning the
    ciphertext (or the plaintext) on failure would let a caller treat
    unreadable data as real data. Callers should surface this as a dependency
    failure.
    """


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #


def _prehash(password: str) -> bytes:
    """SHA-256 + base64 of the UTF-8 password: a fixed 44 bytes.

    bcrypt hashes at most 72 bytes of input. Pre-hashing makes every input
    exactly 44 bytes, so two distinct long passwords can never collide
    through truncation, and no password can be longer than the limit.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def _legacy_bytes(password: str) -> bytes:
    """The old scheme: raw UTF-8 truncated to 72 bytes.

    Kept only to verify hashes created before the scheme marker existed.
    """
    return password.encode("utf-8")[:72]


def get_password_hash(password: str) -> str:
    """Hash a password for storage.

    The result is ``$krb1$<bcrypt hash>``. Use :func:`verify_password` to
    check a candidate — it understands every scheme this application has
    written.
    """
    hashed = bcrypt.hashpw(_prehash(password), bcrypt.gensalt())
    return f"{_PASSWORD_SCHEME_PREFIX}{hashed.decode('utf-8')}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a candidate against a stored hash, whatever scheme it uses."""
    if not hashed_password:
        return False
    try:
        if hashed_password.startswith(_PASSWORD_SCHEME_PREFIX):
            stored = hashed_password[len(_PASSWORD_SCHEME_PREFIX):]
            return bcrypt.checkpw(_prehash(plain_password), stored.encode("utf-8"))
        # Legacy hash: raw bcrypt over the truncated password.
        return bcrypt.checkpw(_legacy_bytes(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError, AttributeError):
        return False


def password_hash_needs_upgrade(hashed_password: str) -> bool:
    """True when a stored hash uses a superseded scheme."""
    if not isinstance(hashed_password, str):
        return True
    return not hashed_password.startswith(_PASSWORD_SCHEME_PREFIX)


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #


def create_access_token(
    subject: Union[str, Any],
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Issue a signed access token.

    The algorithm is always :data:`PINNED_JWT_ALGORITHM`; it is not
    configurable.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode: dict[str, Any] = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(subject),
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=PINNED_JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a token.

    The algorithm allow-list is a literal, not configuration, so no runtime
    setting can widen it.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[PINNED_JWT_ALGORITHM])


# --------------------------------------------------------------------------- #
# Field encryption with key versions
# --------------------------------------------------------------------------- #


def _key_registry() -> dict[str, str]:
    """Parse ``FIELD_ENCRYPTION_KEYS`` into ``{key_id: secret}``.

    Format: ``key_id:secret,key_id2:secret2``. Secrets are base64 or raw
    strings; they are never logged.
    """
    raw = (settings.FIELD_ENCRYPTION_KEYS or "").strip()
    if not raw:
        return {}
    out: dict[str, str] = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        key_id, secret = chunk.split(":", 1)
        key_id = key_id.strip()
        secret = secret.strip()
        if key_id and secret:
            out[key_id] = secret
    return out


def _derive_fernet_key_stdlib(secret: str, key_id: str) -> bytes:
    """Derive a Fernet key from a master secret and a key id.

    HKDF-SHA256 (RFC 5869 extract-and-expand) implemented with the standard
    library. Key derivation is keyed by the key id so that two key ids never
    produce the same encryption key even from the same secret, and so the key
    id is bound into the derived material.
    """
    salt = f"karmathy-field-encryption:{key_id}".encode("utf-8")
    info = b"karmathy-fernet-v1"

    # Extract
    prk = hmac.new(salt, secret.encode("utf-8"), hashlib.sha256).digest()

    # Expand (single block is enough: 32 bytes needed, L=255 max)
    okm = hmac.new(prk, info + b"\x01", hashlib.sha256).digest()

    return base64.urlsafe_b64encode(okm)


def _fernet_for(key_id: str):
    from cryptography.fernet import Fernet

    secret = _key_registry().get(key_id)
    if not secret:
        # No SECRET_KEY fallback exists: a missing or unknown key id is an
        # error, not a reason to read or write data in the clear.
        raise SecretDecryptionError(f"No encryption key registered for id {key_id!r}")
    return Fernet(_derive_fernet_key_stdlib(secret, key_id))


def encrypt_secret(value: str | None) -> str | None:
    """Encrypt a sensitive field for storage.

    Output format: ``ENCv1:<key_id>:<fernet token>``.

    The active key id comes from ``FIELD_ENCRYPTION_ACTIVE_KEY_ID`` and must
    be present in the ``FIELD_ENCRYPTION_KEYS`` registry. There is no
    fallback to ``SECRET_KEY``: with no usable key this raises rather than
    writing a secret in the clear or silently weakening encryption.
    """
    if value is None:
        return None
    if value == "":
        return value

    key_id = (settings.FIELD_ENCRYPTION_ACTIVE_KEY_ID or "").strip()
    if not key_id or key_id not in _key_registry():
        raise SecretDecryptionError(
            "FIELD_ENCRYPTION_ACTIVE_KEY_ID is not set or is not in "
            "FIELD_ENCRYPTION_KEYS. Refusing to encrypt without a "
            "rotatable key: there is no SECRET_KEY fallback."
        )

    token = _fernet_for(key_id).encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{ENCRYPTION_VERSION}:{key_id}:{token}"


def field_encryption_status() -> dict:
    """Describe the field-encryption configuration.

    Surfaced by the admin configuration screen so an operator can see that
    encryption is not yet rotatable, rather than discovering it when a key
    rotation is needed.
    """
    registry = _key_registry()
    active = (settings.FIELD_ENCRYPTION_ACTIVE_KEY_ID or "").strip()
    rotatable = bool(registry) and active in registry
    return {
        "configured": rotatable,
        "rotatable": rotatable,
        "active_key_id": active if rotatable else "",
        "registered_key_ids": sorted(registry),
        "note": (
            "Field encryption is active and rotatable."
            if rotatable
            else (
                "Field encryption is inactive: set FIELD_ENCRYPTION_KEYS "
                "and FIELD_ENCRYPTION_ACTIVE_KEY_ID. There is no "
                "SECRET_KEY fallback."
            )
        ),
    }


def decrypt_secret(value: str | None) -> str | None:
    """Decrypt a value produced by :func:`encrypt_secret`.

    Accepts only ``ENCv1:<key_id>:<token>`` values whose ``key_id`` is in
    the ``FIELD_ENCRYPTION_KEYS`` registry; any other input is an error.

    Raises :class:`SecretDecryptionError` when the value cannot be decrypted
    or was written under a key that is no longer registered. It never
    returns the ciphertext or the plaintext unchanged.
    """
    if value is None:
        return None
    if value == "":
        return value
    if not isinstance(value, str):
        raise SecretDecryptionError("Encrypted value is not a string")

    if value.startswith(_ENCRYPTION_PREFIX):
        parts = value.split(":", 2)
        if len(parts) != 3:
            raise SecretDecryptionError("Malformed encrypted value")
        _, key_id, token = parts
        try:
            return _fernet_for(key_id).decrypt(token.encode("utf-8")).decode("utf-8")
        except SecretDecryptionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SecretDecryptionError(
                f"Failed to decrypt value with key id {key_id!r}"
            ) from exc

    # No SECRET_KEY fallback exists: a bare Fernet token written before
    # key versioning can no longer be decrypted, and we refuse to guess.
    raise SecretDecryptionError(
        "Legacy encrypted value: no SECRET_KEY fallback is configured. "
        "Set FIELD_ENCRYPTION_KEYS and FIELD_ENCRYPTION_ACTIVE_KEY_ID, or "
        "restore the pre-encryption value from backup."
    )


def is_encrypted(value: str | None) -> bool:
    """True when the value carries the versioned encryption envelope."""
    return bool(value) and isinstance(value, str) and value.startswith(_ENCRYPTION_PREFIX)


def secret_needs_reencrypt(value: str | None) -> bool:
    """True when a stored value should be rewritten in the current format."""
    if not value or not isinstance(value, str):
        return False
    return not value.startswith(_ENCRYPTION_PREFIX)


# --------------------------------------------------------------------------- #
# Opaque identifiers
# --------------------------------------------------------------------------- #


def generate_opaque_id(prefix: str = "") -> str:
    """A URL-safe, unguessable identifier for stored objects.

    Used for file references so that a storage path is never exposed to a
    client and cannot be enumerated.
    """
    token = secrets.token_urlsafe(24)
    return f"{prefix}{token}" if prefix else token
