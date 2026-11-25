"""Failures a job handler raises deliberately.

The queue distinguishes a failure that a retry may cure from one that it
cannot. A handler that has no work to do — because the work is not built yet,
or because the payload it was given can never be executed — raises
:class:`JobNotImplemented` or :class:`JobInputInvalid`. The worker moves such
a job straight to ``dead`` and records the reason, instead of retrying it five
times to reach the same conclusion.

Anything else a handler raises is treated as a transient failure: the job is
retried with backoff, and only becomes dead when its attempts are spent. A
database that was briefly unreachable is not the same as a feature that does
not exist, and the queue must not confuse the two.
"""
from __future__ import annotations


class JobError(Exception):
    """Base class for a failure a handler raises deliberately."""


class JobNotImplemented(JobError):
    """The job type is registered but the work behind it is not built.

    Permanent: no number of retries will make the feature exist. The job is
    dead-lettered with this message so the gap is visible to an operator
    instead of being reported as a success.
    """


class JobInputInvalid(JobError):
    """The stored payload cannot be executed.

    Covers a job queued before its payload was stored, a payload that is not
    valid JSON, and one that is not an object. Permanent: the parameters
    cannot be recovered, so retrying reads the same unusable row again.
    """


class JobCancelled(JobError):
    """The work was cancelled before it finished.

    Permanent. An operator who cancels an import means it, and the import
    refuses every later attempt at the same confirmation token — so a retry
    cannot succeed, and the job would sit in ``failed`` waiting for someone
    to retry it into the same refusal. It is dead-lettered instead, with the
    reason, which is where an operator looks for work that did not happen.
    """
