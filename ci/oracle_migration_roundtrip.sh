#!/usr/bin/env bash
#
# The Oracle migration round trip.
#
# The SQLite suites cannot see the failures that stop the migration chain
# on Oracle, so the chain has to be applied to a real Oracle database
# before a release. This script does that: it applies the chain to a
# scratch schema, downgrades it to the base and applies it again, three
# times, and reports the revision after every step.
#
# It needs the Autonomous Database wallet, so it cannot be an ordinary
# pull-request job. The Release Manager decides where it runs — a scheduled
# job, a release check, or a documented manual command in the release
# procedure. What is not acceptable is a migration that has never been
# applied to Oracle and is called verified.
#
# The schema must be a scratch one: the script empties it before it starts.
# It refuses the live ADMIN schema by name.
#
# Usage:
#   ORACLE_DSN=karmkathyadb_high \
#   ORACLE_USER=KARMA_VERIFY \
#   ORACLE_PASSWORD="$(cat ~/.karmathy/karma_verify_password)" \
#   ORACLE_WALLET_DIR="$PWD/backend/wallet" \
#   ORACLE_WALLET_PASSWORD="$(cat ~/.karmathy/wallet_password)" \
#   SECRET_KEY="$(openssl rand -base64 48)" \
#   ci/oracle_migration_roundtrip.sh --i-know-this-is-a-scratch-schema
#
# The application refuses a key shorter than 32 characters; a throwaway one
# generated for the run is enough, because the round trip never
# authenticates anything. The password is read from the environment. It is
# never printed, never written to a file and never committed.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-${REPO_ROOT}/.venv/bin/python}"

if [ ! -x "${PYTHON}" ]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

if [ -z "${PYTHON}" ]; then
  echo "oracle_migration_roundtrip: no Python interpreter found" >&2
  exit 2
fi

for required in ORACLE_DSN ORACLE_USER ORACLE_PASSWORD ORACLE_WALLET_DIR; do
  if [ -z "${!required:-}" ]; then
    echo "oracle_migration_roundtrip: ${required} is not set" >&2
    exit 2
  fi
done

if [ -z "${SECRET_KEY:-}" ]; then
  echo "oracle_migration_roundtrip: SECRET_KEY is not set" >&2
  exit 2
fi

cd "${REPO_ROOT}" || exit 2
exec "${PYTHON}" ci/oracle_migration_roundtrip.py "$@"
