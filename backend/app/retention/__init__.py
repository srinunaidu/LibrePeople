"""Retention: how long the platform keeps the things it stores.

This lane owns *upload* retention only. Erasure — removing a person's data
from the system on request — belongs to the security lane and is not
implemented here.
"""
from app.retention.uploads import (  # noqa: F401
    delete_upload,
    expiry_from_now,
    purge_expired_uploads,
    retention_days,
)

__all__ = [
    "delete_upload",
    "expiry_from_now",
    "purge_expired_uploads",
    "retention_days",
]
