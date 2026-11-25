"""Storage: where uploaded files, offer letters and documents live.

See :mod:`app.storage.backends` for the backends themselves and for the
checksum contract that a write is verified against.
"""
from app.storage.backends import (  # noqa: F401
    CHECKSUM_METADATA_KEY,
    ChecksumMismatch,
    LocalStorage,
    OCIObjectStorage,
    StorageBackend,
    StorageError,
    checksum,
    get_storage,
)

__all__ = [
    "CHECKSUM_METADATA_KEY",
    "ChecksumMismatch",
    "LocalStorage",
    "OCIObjectStorage",
    "StorageBackend",
    "StorageError",
    "checksum",
    "get_storage",
]
