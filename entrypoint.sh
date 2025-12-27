#!/bin/sh
set -e

alembic upgrade head

export SIMPLEFIN_API_KEY_FILE="/app/simplefin_dev_key"

simplefin-archive