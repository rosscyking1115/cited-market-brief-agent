#!/usr/bin/env bash
# Backup + restore drill (plan Phase 5 exit criterion).
# Dumps the app database, restores into a scratch DB, compares table row counts.
# Usage: DATABASE_URL=postgres://user:pass@host:5432/cited_market_brief_agent bash scripts/backup_restore_test.sh
set -euo pipefail

DB_URL="${DATABASE_URL:-postgresql://cited_market_brief_agent:cited_market_brief_agent@localhost:5432/cited_market_brief_agent}"
DB_URL="${DB_URL/postgresql+psycopg/postgresql}"
SCRATCH="cited_market_brief_agent_restore_test"
DUMP="/tmp/cited_market_brief_agent_$(date +%Y%m%d_%H%M%S).dump"

echo "==> dumping ${DB_URL%%\?*}"
pg_dump --format=custom --file="$DUMP" "$DB_URL"

ADMIN_URL="${DB_URL%/*}/postgres"
echo "==> recreating scratch db ${SCRATCH}"
psql "$ADMIN_URL" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${SCRATCH};"
psql "$ADMIN_URL" -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${SCRATCH};"
psql "${DB_URL%/*}/${SCRATCH}" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "==> restoring"
pg_restore --dbname="${DB_URL%/*}/${SCRATCH}" --no-owner --no-privileges "$DUMP"

echo "==> comparing row counts"
COUNT_SQL="SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;"
ORIG=$(psql "$DB_URL" -At -c "$COUNT_SQL")
REST=$(psql "${DB_URL%/*}/${SCRATCH}" -At -c "ANALYZE; $COUNT_SQL")

if [ "$ORIG" = "$REST" ]; then
  echo "RESTORE TEST: PASS (row counts match)"
  psql "$ADMIN_URL" -c "DROP DATABASE ${SCRATCH};"
  rm -f "$DUMP"
else
  echo "RESTORE TEST: FAIL — row count mismatch (scratch db ${SCRATCH} kept for inspection)"
  diff <(echo "$ORIG") <(echo "$REST") || true
  exit 1
fi
