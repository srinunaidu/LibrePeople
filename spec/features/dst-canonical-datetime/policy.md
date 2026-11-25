# DST-canonical datetime policy

Status: policy (docs only — no behavior change in this slice).
Scope: all backend timestamps touching attendance, leave, payroll, scheduling.

## 1. Instant vs wall time

- **Instant**: a point on the UTC timeline. All stored timestamps, audit
  fields (`created_at`, `decided_at`, `clock_in/out`, `pay_date` instants),
  comparisons, ordering, and durations use instants.
- **Wall time**: what a person sees on a clock in a zone
  (e.g. `2026-10-25 02:30 Europe/Berlin`). Wall times are display/input
  only — never stored, never compared.
- Rule: **parse wall → convert to UTC instant at the boundary;
  convert UTC instant → wall only for display.**

## 2. Conversion rule (wall + ZoneInfo → UTC)

- Interpret user-supplied wall times with an explicit IANA zone
  (`ZoneInfo`, never fixed offsets, never server-local time).
- Canonical helper signatures (to be introduced in the implementation
  slice, not this docs slice):
  - `as_utc(wall: datetime, tz: ZoneInfo) -> datetime`
  - `as_wall(instant: datetime, tz: ZoneInfo) -> datetime`
  - `utcnow() -> datetime` (tz-aware, `tzinfo=timezone.utc`)
- All helpers reject naive datetimes as input (`ValueError`) except the
  single SQLite-read coercion point (see migration-implications.md).
- `date.today()` / server-local "today" must not define day boundaries
  for attendance or payroll; the tenant's zone defines the day.

## 3. Gap and fold handling

- **Gap** (spring forward, wall time never existed): reject with a 422
  naming the zone and the local time; never silently shift.
- **Fold** (autumn back, wall time occurs twice): require the caller to
  disambiguate (`fold=0|1`); default reject with 422 when ambiguous.
- Durations are computed on UTC instants, so a "25-hour day" yields
  correct hours without special-casing.

## 4. Domain notes

- **Attendance**: `clock_in/out` stored as UTC instants; late/overtime
  evaluated against shift walls converted per §2; overnight shifts span
  two wall dates but one UTC interval.
- **Leave**: leave days are wall-date ranges in the employee's zone;
  balances decrement in days, never via 24h division across a transition.
- **Payroll**: pay periods close on UTC instants derived from zone walls;
  `pay_date` display uses the tenant zone; proration uses actual elapsed
  instants, not nominal 8h × days, across DST boundaries.
