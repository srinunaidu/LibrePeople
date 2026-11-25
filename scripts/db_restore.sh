#!/usr/bin/env sh
# PostgreSQL restore for LibrePeople (Stage 3 DB foundations).
#
# Restores a pg_dump custom-format archive written by scripts/db_backup.sh.
# Target is taken from DATABASE_URL when it is a postgresql:// URL,
# otherwise from PGHOST/PGPORT/PGUSER/PGDATABASE. This is destructive
# (pg_restore --clean drops objects before recreating them), so it asks
# for confirmation unless --yes is given.
#
# Usage:
#   scripts/db_restore.sh <archive.dump>
#   scripts/db_restore.sh --yes <archive.dump>
set -eu

YES=0
if [ "${1:-}" = "--yes" ]; then
  YES=1
  shift
fi

ARCHIVE="${1:-}"
if [ -z "${ARCHIVE}" ]; then
  echo "usage: scripts/db_restore.sh [--yes] <archive.dump>" >&2
  exit 2
fi
if [ ! -f "${ARCHIVE}" ]; then
  echo "error: archive not found: ${ARCHIVE}" >&2
  exit 1
fi

command -v pg_restore >/dev/null 2>&1 || {
  echo "error: pg_restore not found. Install PostgreSQL client tools." >&2
  exit 1
}

if [ "${YES}" -ne 1 ]; then
  echo "About to restore ${ARCHIVE} onto:"
  case "${DATABASE_URL:-}" in
    postgresql://*) echo "  DATABASE_URL (postgresql://…)" ;;
    *) echo "  PGHOST=${PGHOST:-localhost} PGDATABASE=${PGDATABASE:-${POSTGRES_DB:-karmathy}}" ;;
  esac
  echo "This drops and recreates database objects (--clean)."
  printf "Type YES to continue: "
  read -r ANSWER
  if [ "${ANSWER}" != "YES" ]; then
    echo "aborted."
    exit 1
  fi
fi

case "${DATABASE_URL:-}" in
  postgresql://*)
    pg_restore --clean --if-exists --dbname="${DATABASE_URL}" "${ARCHIVE}"
    ;;
  *)
    pg_restore --clean --if-exists "${ARCHIVE}"
    ;;
esac

echo "[restore] restored ${ARCHIVE}"
echo "[restore] run migrations to head: (cd backend && python -m scripts.migrate upgrade)"
