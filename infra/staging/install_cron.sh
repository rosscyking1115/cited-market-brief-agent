#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-/opt/cited-market-brief-agent}"
LOG_DIR="$REPO_DIR/.data/logs"
mkdir -p "$LOG_DIR"

CRON_FILE=/etc/cron.d/cited-market-brief-agent
cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Check every 15 minutes; app cron decides whether a watchlist is due.
*/15 * * * * root cd "$REPO_DIR" && docker compose --env-file .env.staging -f docker-compose.staging.yml --profile scheduler run --rm scheduler >> "$LOG_DIR/scheduler.log" 2>&1
EOF

chmod 0644 "$CRON_FILE"
echo "Installed $CRON_FILE. Watchlists fire at their stored cron, currently 23:00 UTC / 07:00 Taiwan."
