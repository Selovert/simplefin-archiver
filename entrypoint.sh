#!/bin/bash
set -e

alembic upgrade head

uv run simplefin_archive