# Migration implications (SQLite-naive → aware)

## 1. Current state

SQLite returns naive datetimes; app code today coerces them with
`replace(tzinfo=timezone.utc)` at read time (see inventory §8).
Stored values are therefore already UTC wall-equivalent; only the
tz-awareness is missing.

## 2. Rules for the implementation slice

- **No bulk rewrite.** Existing rows are semantically UTC already —
  a bulk `UPDATE` re-stamping them would risk double-shifting.
- **Schema**: prefer keeping `TIMESTAMP` columns as-is on SQLite;
  enforce awareness at the ORM/pydantic boundary going forward.
- **Opt-in backfill**: a backfill (where needed for Postgres
  `timestamptz` parity) must be a separate, explicitly invoked script
  that only sets `tzinfo`, never shifts values, and logs row counts.
- **Gap/fold**: no stored instant can be a "gap" (UTC has none);
  wall reconstruction across a transition may need `fold`
  disambiguation at display time only.

## 3. Rollback

- Docs slice: nothing to roll back (no code touched).
- Implementation slice: rollback = revert helper + call-site commits;
  stored data is unshifted so reads remain valid under old naive code.
- Backfill rollback: no-op by design (tz-label-only change); any
  script must support `--verify` showing zero shifted rows.
