#!/usr/bin/env bash
#
# The pilot gate's journey check, in one command.
#
#   bash scripts/staging/gate.sh
#
# It brings the staging environment up, runs the journey suite against it,
# and reports the result. The release procedure is one line.
#
# The journeys are counted on their own. DEC-012: the backend checks and the
# Playwright journeys are never summed, so this script reports the journeys
# and nothing else.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMMIT="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

echo "================================================================"
echo " the journey gate"
echo "   commit  $COMMIT"
echo "   branch  $BRANCH"
echo "   schema  ${STAGING_SCHEMA:-KARMA_STAGE} (Oracle, no customer data)"
echo "================================================================"
echo

echo "== 1/2  bringing the staging environment up =="
if ! bash "$REPO_ROOT/scripts/staging/run.sh"; then
  echo
  echo "the staging environment did not come up; the journeys were not run" >&2
  exit 1
fi
echo

echo "== 2/2  the journeys, against real Oracle =="
cd "$REPO_ROOT/frontend" || exit 2
npx playwright test --config "$REPO_ROOT/scripts/staging/playwright.staging.config.ts"
STATUS=$?

echo
echo "================================================================"
if [ "$STATUS" -eq 0 ]; then
  echo " the journeys pass on staging"
  echo "   commit $COMMIT ($BRANCH)"
  echo "   record this result in agents/PROGRESS.md with the commit"
else
  echo " the journeys do NOT pass on staging"
  echo "   commit $COMMIT ($BRANCH)"
fi
echo "================================================================"

exit "$STATUS"
