#!/bin/sh
set -e

## RUN DATABASE MIGRATIONS ##
echo "Running database migrations..."
alembic upgrade head

## CHECK FOR API KEY ##
# Direct key is set
if [ -n "$SIMPLEFIN_API_KEY" ]; then
    echo "Using API key from environment."
# Key file is set AND the file exists
elif [ -n "$SIMPLEFIN_API_KEY_FILE" ] && [ -f "$SIMPLEFIN_API_KEY_FILE" ]; then
    echo "Using API key from file: $SIMPLEFIN_API_KEY_FILE"
# Failure case
else
    echo "Error: SimpleFIN API key is missing."
    echo "You must provide SIMPLEFIN_API_KEY or a valid path in SIMPLEFIN_API_KEY_FILE."
    exit 1
fi
# Strict check: Fail if the variable is not set
: "${SIMPLEFIN_QUERY_FQCY_DAYS:?Environment variable SIMPLEFIN_QUERY_FQCY_DAYS is required}"

## CALCULATE PARAMETERS ##
# Convert Days to DAYS_HISTORY (Days * 2, then Ceil)
export DAYS_HISTORY=$(echo "$SIMPLEFIN_QUERY_FQCY_DAYS" | awk '{ n=$1*2; print (n > int(n) ? int(n) + 1 : int(n)) }')
# Calculate sleep seconds (Days * 86400)
SLEEP_SECONDS=$(echo "$SIMPLEFIN_QUERY_FQCY_DAYS" | awk '{print $1 * 86400}')

## MAIN LOOP ##
while true; do
    echo "Running archive with history: $DAYS_HISTORY days..."
    simplefin-archive --days-history "$DAYS_HISTORY"

    echo "Sleeping for $SLEEP_SECONDS seconds..."
    sleep "$SLEEP_SECONDS"
done