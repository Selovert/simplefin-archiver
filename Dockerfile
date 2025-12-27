from ghcr.io/astral-sh/uv:debian

# uv optimisations
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
# make uv tools available globally
ENV UV_TOOL_BIN_DIR=/opt/uv-bin/
ENV PATH="/opt/uv-bin/bin:$PATH"

# copy pyproject
COPY pyproject.toml /app/pyproject.toml
# copy app over
COPY src /app/src
# copy alembic files
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

# Change the working directory to the `app` directory
WORKDIR /app

# install dependencies
RUN uv sync --locked --no-editable
ENV PATH="/app/.venv/bin:$PATH"
RUN uv tool install .

ENTRYPOINT ["uv", "run", "simplefin_archive"]