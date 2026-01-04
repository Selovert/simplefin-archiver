FROM ghcr.io/astral-sh/uv:alpine

# install dependencies
RUN apk add --no-cache --update \
    tzdata
    curl

# get rid of docs to save space
RUN rm -rf /usr/share/doc /usr/share/man

## USER-EDITABLE ENVIRONMENT VARIABLES ##
# set the default db path
ENV SIMPLEFIN_DB_PATH=/app/data/simplefin.db
ENV QUERY_HISTORY_DAYS=5
ENV CRON_SCHEDULE="0 0 * * *"
ENV QUERY_AT_STARTUP=false

## INTERNAL ENVIRONMENT VARIABLES ##
# uv optimisations
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
# make uv tools available globally
ENV UV_TOOL_BIN_DIR=/opt/uv-bin/
ENV PATH="/opt/uv-bin/:$PATH"


## BUILD STEPS ##
# create data dir
RUN mkdir -p "$(dirname "$SIMPLEFIN_DB_PATH")"

# copy project files
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock
COPY README.md /app/README.md
# copy app over
COPY src /app/src
# copy alembic files
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
# copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Change the working directory to the `app` directory
WORKDIR /app

# install dependencies
RUN uv sync --locked --no-editable
ENV PATH="/app/.venv/bin:$PATH"
RUN uv tool install .

## HEALTHCHECK ##
HEALTHCHECK --interval=60s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health_check || exit 1

## RUN ##
ENTRYPOINT ["/app/entrypoint.sh"]