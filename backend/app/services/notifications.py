"""Event-driven in-app notifications (LP-NOT-001).

Why this module exists
----------------------
Leave decisions, pay-run progress, onboarding and offboarding milestones are
state changes the affected person would otherwise only discover by asking.
Each of those endpoints therefore emits a notification at the moment the
change is decided — not before (a refused approval emits nothing) and not
twice (a retried request must not double-notify).

Two rules govern every emission:

* **Duplicate guard.** :func:`emit` is keyed on
  ``(recipient, category, entity_type, entity_id, notification_type, title)``.
  A row with the same key already in the session's database is returned
  instead of inserting a second row, so a retried approval, a replayed
  idempotency key, or a second ``Completed`` write for the same task does
  not fan out into two notifications. Emissions without an entity dedupe
  on ``(recipient, category, notification_type, title)`` with both entity
  columns NULL, so a retried entity-less emission cannot double-notify
  either (no production caller emits without an entity today; the rule
  closes the hole for future callers).
* **Preference gate (stub).** The recipient's ESS profile carries three
  channel flags (``notification_email/sms/push``). When a profile exists
  and every flag is off, the recipient has opted out of event-driven
  notifications and :func:`emit` writes nothing. There is no email or push
  provider behind this yet (LP-NOT-002 owns delivery); the gate only
  decides whether the in-app row is written, and ``email_sent`` stays
  ``False`` until a provider sets it.

The function never commits: the calling endpoint owns the transaction, so a
notification is only ever persisted together with the change it announces.
A caller that cannot resolve a recipient (an employee with no linked user
account) gets ``None`` and carries on — a missing login must never break
an HR decision.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ess_hr import EmployeeSelfService, Notification
from app.models.job_queue import JobQueue, JobState, JobType
from app.models.user import User


def user_id_for_employee(db: Session, employee_id: int | None) -> int | None:
    """The login account linked to an employee, or ``None``.

    Not every employee has a login (service accounts, historical rows), and
    ``User.employee_id`` is the only link between the two tables. Callers
    treat ``None`` as "nobody to notify" and skip the emission.
    """
    if employee_id is None:
        return None
    user = (
        db.query(User)
        .filter(User.employee_id == employee_id)
        .first()
    )
    return user.id if user is not None else None


def recipient_preferences(db: Session, user_id: int) -> dict[str, bool]:
    """The recipient's channel flags, with the product defaults.

    A recipient with no ESS profile has never opted out, so every channel
    reads ``True``. A recipient with a profile reads whatever they chose.
    """
    defaults = {"email": True, "sms": False, "push": True}
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.employee_id is None:
        return defaults
    profile = (
        db.query(EmployeeSelfService)
        .filter(EmployeeSelfService.employee_id == user.employee_id)
        .first()
    )
    if profile is None:
        return defaults
    return {
        "email": bool(profile.notification_email),
        "sms": bool(profile.notification_sms),
        "push": bool(profile.notification_push),
    }


def preferences_allow(db: Session, user_id: int) -> bool:
    """Whether the recipient still wants event-driven notifications.

    The stub rule: everything off means opted out. Any single channel left
    on keeps the in-app row — the in-app centre is the fallback channel
    until LP-NOT-002 wires up real delivery.
    """
    prefs = recipient_preferences(db, user_id)
    return bool(prefs.get("email") or prefs.get("sms") or prefs.get("push"))


def emit(
    db: Session,
    *,
    recipient_user_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
    category: str = "system",
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Notification | None:
    """Write one in-app notification, unless the guard says otherwise.

    Returns the existing row when the duplicate guard fires, ``None`` when
    the preference gate skips the emission, and the new row otherwise. The
    row is added to the session but never committed here.
    """
    if not preferences_allow(db, recipient_user_id):
        return None
    q = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == recipient_user_id,
            Notification.category == category,
            Notification.notification_type == notification_type,
            Notification.title == title,
        )
    )
    if entity_type is not None and entity_id is not None:
        q = q.filter(
            Notification.entity_type == entity_type,
            Notification.entity_id == entity_id,
        )
    else:
        # Entity-less emissions dedupe against other entity-less rows only:
        # a NULL entity never collides with a keyed entity row.
        q = q.filter(
            Notification.entity_type.is_(None),
            Notification.entity_id.is_(None),
        )
    existing = q.first()
    if existing is not None:
        return existing
    obj = Notification(
        recipient_id=recipient_user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        delivery_status="queued",
        delivery_attempts=0,
    )
    db.add(obj)
    db.flush()
    return obj


def enqueue_delivery(
    db: Session,
    notification_id: int,
    *,
    priority: int = 10,
    max_attempts: int = 5,
) -> JobQueue:
    """Queue background delivery of one notification (LP-NOT-003).

    The payload is just the notification id, so the input hash is stable
    for the row: re-enqueueing while a job for it is still in flight
    (queued, running, or waiting for retry after a transient failure)
    returns the existing job instead of a duplicate. A job that already
    succeeded for the id is likewise returned as-is by the queue itself,
    so a retried emission that finds an already-sent row never
    double-delivers — the handler re-checks the row before doing
    anything.

    Unlike :func:`emit`, this commits: the queue owns its transaction,
    and the notification must already be visible (committed, with an id)
    before its delivery is queued.
    """
    from app.jobs.queue import JobQueueService, compute_input_hash

    payload = {"notification_id": notification_id}
    service = JobQueueService(db)
    pending = (
        db.query(JobQueue)
        .filter(
            JobQueue.job_type == JobType.NOTIFICATION_DELIVER,
            JobQueue.input_hash == compute_input_hash(payload),
            JobQueue.state.in_(
                [JobState.QUEUED, JobState.RUNNING, JobState.FAILED]
            ),
        )
        .first()
    )
    if pending is not None:
        return pending
    return service.enqueue(
        JobType.NOTIFICATION_DELIVER,
        payload,
        priority=priority,
        max_attempts=max_attempts,
    )


__all__ = [
    "emit",
    "enqueue_delivery",
    "preferences_allow",
    "recipient_preferences",
    "user_id_for_employee",
]
