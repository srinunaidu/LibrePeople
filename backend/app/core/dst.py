"""DST-canonical datetime helpers (policy: spec/features/dst-canonical-datetime).

Boundary rule: parse wall time -> convert to UTC instant at the boundary
via :func:`wall_to_utc` / :func:`as_utc_for_compare`; convert UTC instant
-> wall only for display. All stored timestamps, comparisons, ordering and
durations use UTC instants.

Policy-amendment note: the policy doc prescribes rejecting spring-forward
gaps with a 422. The kiosk auto-create path cannot reject — a roster shift
may legitimately start inside a gap — so these helpers *push gap wall times
forward* to the first valid local time (bounded, max 3h) instead of
raising. Any HTTP surface that must enforce the strict 422 behaviour should
detect gaps itself rather than relying on these helpers.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TZLike = Union[str, ZoneInfo]

#: Maximum forward shift applied to a wall time that falls inside a DST gap.
MAX_GAP_PUSH = timedelta(hours=3)
_GAP_STEP = timedelta(minutes=1)


def _resolve_tz(tz: TZLike) -> ZoneInfo:
    if isinstance(tz, ZoneInfo):
        return tz
    if isinstance(tz, str) and tz:
        try:
            return ZoneInfo(tz)
        except ZoneInfoNotFoundError:
            raise ValueError(f"Unknown IANA time zone: {tz!r}")
    raise ValueError(f"tz must be an IANA name or ZoneInfo, got {tz!r}")


def _roundtrip_ok(wall: datetime, tz: ZoneInfo, fold: int) -> bool:
    """True when ``wall`` exists in ``tz`` with the given fold."""
    instant = wall.replace(tzinfo=tz, fold=fold).astimezone(timezone.utc)
    back = instant.astimezone(tz)
    return back.replace(tzinfo=None) == wall


def _offsets(wall: datetime, tz: ZoneInfo) -> tuple:
    return (
        wall.replace(tzinfo=tz, fold=0).utcoffset(),
        wall.replace(tzinfo=tz, fold=1).utcoffset(),
    )


def wall_to_utc(wall: datetime, tz: TZLike, fold: Optional[int] = None) -> datetime:
    """Convert a naive wall time in ``tz`` to a UTC instant.

    - ``wall`` must be naive; tz-aware input raises ``ValueError`` (instants
      are already canonical — never reinterpret them as wall times).
    - ``tz`` is an IANA name or ``ZoneInfo`` (never a fixed offset or
      server-local time); unknown names raise ``ValueError``.
    - Fold (autumn-back, wall occurs twice): when the wall time is
      ambiguous the caller must pass ``fold=0|1``; omitting it raises
      ``ValueError``.
    - Gap (spring-forward, wall never existed): the wall time is pushed
      forward to the first valid local time, at most 3h; a wider gap
      raises ``ValueError``.
    """
    if not isinstance(wall, datetime):
        raise ValueError(f"wall must be a datetime, got {type(wall).__name__}")
    if wall.tzinfo is not None:
        raise ValueError("wall must be naive (tzinfo=None); refusing aware input")
    if fold not in (None, 0, 1):
        raise ValueError(f"fold must be 0, 1 or None, got {fold!r}")

    zone = _resolve_tz(tz)
    naive = wall.replace(tzinfo=None)

    if _roundtrip_ok(naive, zone, 0) and _roundtrip_ok(naive, zone, 1):
        off0, off1 = _offsets(naive, zone)
        if off0 != off1:
            if fold is None:
                raise ValueError(
                    f"Ambiguous wall time {naive.isoformat()} in {zone.key}: "
                    "pass fold=0 (first occurrence) or fold=1 (second)"
                )
            return naive.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
        return naive.replace(tzinfo=zone, fold=0).astimezone(timezone.utc)

    # Gap: push forward to the first valid local time (bounded).
    probe = naive
    elapsed = timedelta(0)
    while elapsed < MAX_GAP_PUSH:
        probe = probe + _GAP_STEP
        elapsed = elapsed + _GAP_STEP
        if _roundtrip_ok(probe, zone, 0) and _roundtrip_ok(probe, zone, 1):
            off0, off1 = _offsets(probe, zone)
            if off0 == off1:
                return probe.replace(tzinfo=zone, fold=0).astimezone(timezone.utc)
    raise ValueError(
        f"Nonexistent wall time {naive.isoformat()} in {zone.key}: "
        "no valid local time within 3h after it"
    )


def as_utc_for_compare(wall: datetime, tz: TZLike, fold: Optional[int] = None) -> datetime:
    """Canonical UTC instant for a wall time, for comparisons/ordering/durations.

    Same semantics as :func:`wall_to_utc`: naive wall in, aware UTC out;
    ambiguous folds require explicit ``fold``, gaps push forward (<=3h),
    aware input raises ``ValueError``.
    """
    return wall_to_utc(wall, tz, fold=fold)
