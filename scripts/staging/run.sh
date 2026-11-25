#!/usr/bin/env bash
# Bring up the Karmathy HCM staging environment against a scratch Oracle schema.
#
# The staging environment is the application, the built frontend, and a real
# Oracle schema that holds no customer data. It is what the journey suite
# runs against, and it is what the pilot gate means by "on staging".
#
# The free tier has no room for a second hosted service, so staging is a
# local deployment against the second schema in the same Autonomous Database
# instance. It is the same code, the same migrations and the same database
# engine as production — which is the point.
#
#   KARMA_STAGE  an empty schema, migrated to head, seeded with the
#                synthetic accounts the journeys use
#
# The password lives in ~/.karmathy/<schema>_password, mode 0600, and is
# never written here, never printed, and never committed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCHEMA="${STAGING_SCHEMA:-KARMA_STAGE}"
WALLET_DIR="${ORACLE_WALLET_DIR:-$REPO_ROOT/backend/wallet}"
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python}"
BACKEND_PORT="${BACKEND_PORT:-8011}"
FRONTEND_PORT="${FRONTEND_PORT:-4173}"
API_URL="http://127.0.0.1:${BACKEND_PORT}/api/v1"

# The guard: this script migrates a schema, so pointing it at the live one
# would try to migrate production. The password file below is the practical
# guard — the live schema's password is under a different name — but a name
# is cheap to check and the cost of being wrong is a production migration.
#
# The journey suite has its own guard, on the API base URL it is pointed at
# (`frontend/e2e/support/environment.ts`). This one is on the schema.
case "$(echo "$SCHEMA" | tr '[:upper:]' '[:lower:]')" in
  admin|prod|production|live|karmathy_admin|karmathy_prod)
    echo "refusing to run: '$SCHEMA' is a production schema, not a scratch one" >&2
    echo "staging migrates a schema that holds no customer data" >&2
    exit 2
    ;;
esac

if [ ! -f "$HOME/.karmathy/$(echo "$SCHEMA" | tr '[:upper:]' '[:lower:]')_password" ]; then
  echo "no password for $SCHEMA at ~/.karmathy/$(echo "$SCHEMA" | tr '[:upper:]' '[:lower:]')_password" >&2
  echo "ask the Release Manager to create the schema" >&2
  exit 2
fi

# And the address the environment is served on. A staging environment that
# answers on a public production hostname is production.
case "$API_URL" in
  *onrender.com*)
    echo "refusing to run: the API URL '$API_URL' is a production host" >&2
    exit 2
    ;;
esac

export ORACLE_DSN="${ORACLE_DSN:-karmkathyadb_high}"
export ORACLE_USER="$SCHEMA"
export ORACLE_PASSWORD="$(cat "$HOME/.karmathy/$(echo "$SCHEMA" | tr '[:upper:]' '[:lower:]')_password")"
export ORACLE_WALLET_DIR="$WALLET_DIR"
export ORACLE_WALLET_PASSWORD="$(cat "$HOME/.karmathy/wallet_password")"
export SECRET_KEY="${SECRET_KEY:-staging-only-key-not-for-production-0123456789}"
export BACKEND_CORS_ORIGINS="http://127.0.0.1:${FRONTEND_PORT}"
export ALLOW_SELF_REGISTRATION=false
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export MIGRATE_ON_STARTUP=false
export PUBLIC_DIAGNOSTIC_ENDPOINTS=true
export E2E_PORT="$BACKEND_PORT"

echo "== the schema, before the migrations =="
(cd "$REPO_ROOT/backend" && "$PYTHON" -m scripts.migrate status | sed 's/^/   /')

echo "== the migrations =="
(cd "$REPO_ROOT/backend" && "$PYTHON" -m scripts.migrate upgrade | tail -3 | sed 's/^/   /')

echo "== the backend, on port ${BACKEND_PORT} =="
# nohup + disown, with every stream off this shell: otherwise the script
# never returns, because the pipe stays open behind the background process.
(cd "$REPO_ROOT/backend" && nohup "$PYTHON" scripts/e2e_server.py >/tmp/karmathy-staging-backend.log 2>&1 </dev/null &) ; disown || true
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -sf "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null || { echo "the backend did not come up; see /tmp/karmathy-staging-backend.log" >&2; exit 1; }
echo "   up"

echo "== the frontend, on port ${FRONTEND_PORT} =="
(cd "$REPO_ROOT/frontend" && VITE_API_URL="$API_URL" npm run build >/tmp/karmathy-staging-frontend.log 2>&1)
(cd "$REPO_ROOT/frontend" && VITE_API_URL="$API_URL" nohup npx vite preview --port "$FRONTEND_PORT" --host 127.0.0.1 >>/tmp/karmathy-staging-frontend.log 2>&1 </dev/null &) ; disown || true
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null 2>&1; then break; fi
  sleep 1
done
echo "   up"

cat <<EOF

staging is up
  api      $API_URL
  frontend http://127.0.0.1:${FRONTEND_PORT}
  schema   $SCHEMA (Oracle, no customer data)
  logs     /tmp/karmathy-staging-backend.log, /tmp/karmathy-staging-frontend.log

run the journeys against it
  cd frontend && npx playwright test --config ../scripts/staging/playwright.staging.config.ts

stop it
  pkill -f 'e2e_server.py' ; pkill -f 'vite preview'
EOF
