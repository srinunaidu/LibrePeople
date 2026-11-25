"""Retention of employee documents (LP-DOC-002).

What this covers
----------------
Only the *documents*: the files HR keeps in an employee's file, with
their version history, acknowledgements and access logs.

The rule
--------
* A document whose ``expiry_date`` has passed is marked ``Expired``. It
  is still readable and downloadable; expiry is a state, not a deletion.
* A document is *purged* — its stored bytes and its rows — only when it
  is already ``Expired`` **and** its ``retention_until`` date has passed.
  ``Active`` and ``Archived`` documents are never purged, however old
  their retention date is, and an ``Expired`` document with no
  ``retention_until`` is kept: without a keep-until date there is nothing
  to enforce.

The sweep
---------
:func:`purge_expired_documents` is the place a periodic job belongs; it
takes no scheduler of its own, mirroring :mod:`app.retention.uploads`.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.observability import get_logger
from app.models.core_hr import (
    DocumentAccessLog,
    DocumentAck,
    DocumentVersion,
    EmployeeDocument,
)

log = get_logger("karmathy.retention.documents")


def mark_expired_documents(db: Session, today: date | None = None) -> int:
    """Mark the documents whose expiry date has passed as Expired.

    Only ``Active`` documents move: ``Archived`` is an explicit human
    state the sweep must not override, and ``Expired`` is already there.
    Returns the number of documents marked.
    """
    day = today or date.today()
    stale = (
        db.query(EmployeeDocument)
        .filter(
            EmployeeDocument.status == "Active",
            EmployeeDocument.expiry_date.is_not(None),
            EmployeeDocument.expiry_date < day,
        )
        .all()
    )
    for doc in stale:
        doc.status = "Expired"
        db.add(doc)
    if stale:
        db.commit()
        log.info("documents marked expired", count=len(stale))
    return len(stale)


def purge_expired_documents(db: Session, today: date | None = None) -> int:
    """Delete the Expired documents whose retention date has passed.

    For each one the stored bytes behind every version are deleted first
    (best effort, like the upload sweep: a backend failure keeps the row
    so the next sweep retries), then the version, acknowledgement and
    access-log rows, then the document itself. Anything that is not
    ``Expired``, or that carries no ``retention_until``, is left alone.
    Returns the number of documents purged.
    """
    from app.storage import get_storage

    day = today or date.today()
    due = (
        db.query(EmployeeDocument)
        .filter(
            EmployeeDocument.status == "Expired",
            EmployeeDocument.retention_until.is_not(None),
            EmployeeDocument.retention_until <= day,
        )
        .all()
    )
    if not due:
        return 0
    storage = get_storage()
    purged = 0
    for doc in due:
        # Collect the keys with a column query, not through the
        # ``versions`` relationship: loading the rows into the session and
        # then bulk-deleting them trips the unit of work (it tries to
        # null out a foreign key on rows that are already gone).
        keys = {doc.storage_key}
        keys.update(
            row[0]
            for row in db.query(DocumentVersion.storage_key)
            .filter(DocumentVersion.document_id == doc.id)
            .all()
        )
        try:
            for key in sorted(k for k in keys if k):
                storage.delete(key)
        except Exception:  # noqa: BLE001
            # The bytes are still there, so the rows stay too: the next
            # sweep retries this document. It is not counted as purged.
            log.warning(
                "could not delete a retained document file",
                document_id=doc.id,
            )
            continue
        db.query(DocumentAccessLog).filter(
            DocumentAccessLog.document_id == doc.id
        ).delete(synchronize_session=False)
        db.query(DocumentAck).filter(
            DocumentAck.document_id == doc.id
        ).delete(synchronize_session=False)
        db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc.id
        ).delete(synchronize_session=False)
        db.delete(doc)
        purged += 1
    db.commit()
    log.info("expired documents purged", count=purged)
    return purged
