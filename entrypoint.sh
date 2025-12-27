#!/bin/sh
set -e

# --- Database Initialization ---
echo "Running database migrations..."
alembic upgrade head

# --- API Configuration Validation ---
if [ -n "$SIMPLEFIN_KEY" ]; then
    echo "Using API key from environment."
elif [ -n "$SIMPLEFIN_KEY_FILE" ] && [ -f "$SIMPLEFIN_KEY_FILE" ]; then
    echo "Using API key from file: $SIMPLEFIN_KEY_FILE"
else
    echo "Error: SimpleFIN API key is missing."
    echo "You must provide SIMPLEFIN_KEY or a valid path in SIMPLEFIN_KEY_FILE."
    exit 1
fi

: "${QUERY_HISTORY_DAYS:?Environment variable QUERY_HISTORY_DAYS is required}"
: "${CRON_SCHEDULE:?Environment variable CRON_SCHEDULE is required}"

# --- Cron Configuration ---
# Capture all ENV vars for cron
printenv | grep -v "no_proxy" > /etc/environment
chmod 400 /etc/environment

# --- Startup Run ---
if [ "${QUERY_AT_STARTUP:-false}" = "true" ]; then
    echo "Running initial data fetch at startup..."
    simplefin-archive --days-history "$QUERY_HISTORY_DAYS"
fi

# Create crontab entry
CRON_CMD="simplefin-archive --days-history $QUERY_HISTORY_DAYS > /proc/1/fd/1 2>&1"
echo "$CRON_SCHEDULE . /etc/environment; $CRON_CMD" > /etc/crontabs/root

# --- Start Daemon ---
echo "Starting cron daemon with schedule: $CRON_SCHEDULE"
exec crond -f -l 2