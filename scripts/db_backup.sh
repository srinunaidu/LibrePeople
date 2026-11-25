#!/usr/bin/env sh
# PostgreSQL backup for LibrePeople (Stage 3 DB foundations).
#
# Writes a timestamped pg_dump custom-format archive to BACKUP_DIR
# (default: ./backups). Connection is taken from DATABASE_URL when it is
# a postgresql:// URL, otherwise from PGHOST/PGPORT/PGUSER/PGDATABASE.
# No credentials are stored in this script; pg_dump uses the standard
# libpq environment (PGPASSWORD, PGSSLMODE, ...) supplied by the operator.
#
# Usage:
#   scripts/db_backup.sh
#   BACKUP_DIR=/var/backups/karmathy scripts/db_backup.sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${BACKUP_DIR}/karmathy-${STAMP}.dump"

command -v pg_dump >/dev/null 2>&1 || {
  echo "error: pg_dump not found. Install PostgreSQL client tools." >&2
  exit 1
}

mkdir -p "${BACKUP_DIR}"

# Prefer an explicit postgresql:// DATABASE_URL; otherwise let libpq fall
# back to PGHOST/PGPORT/PGUSER/PGDATABASE from the environment.
case "${DATABASE_URL:-}" in
  postgresql://*)
    echo "[backup] using DATABASE_URL host (password comes from PGPASSWORD, not the URL log)"
    pg_dump --format=custom --file="${OUT}" "${DATABASE_URL}"
    ;;
  *)
    echo "[backup] using PGHOST=${PGHOST:-localhost} PGDATABASE=${PGDATABASE:-${POSTGRES_DB:-karmathy}}"
    pg_dump --format=custom --file="${OUT}"
    ;;
esac

echo "[backup] wrote ${OUT}"
echo "[backup] restore with: scripts/db_restore.sh \"${OUT}\""
