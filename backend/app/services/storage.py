"""Compatibility shim for the old storage location.

The storage backends used to live at ``app.services.storage``. They now live
at ``app.storage``, which is the module this lane owns. This file keeps the
old import path working so that the rest of the codebase does not have to
change in the same commit.
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
