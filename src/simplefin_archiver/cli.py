import logging
import os
from pathlib import Path
from typing import Optional

import typer
from simplefin_archiver import SimpleFIN, SimpleFIN_DB, QueryResult
from simplefin_archiver.simplefin import DEFAULT_DAYS_HISTORY, DEFAULT_TIMEOUT

app = typer.Typer(help="Query SimpleFIN and persist accounts to a SQLite DB")


def init_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s - %(name)s - %(message)s")


def resolve_simplefin_key(
    simplefin_key: Optional[str], simplefin_key_file: Optional[Path]
) -> str:
    # default to env vars if not provided
    if not simplefin_key:
        simplefin_key = os.getenv("SIMPLEFIN_KEY")
    if not simplefin_key_file:
        simplefin_key_file_env = os.getenv("SIMPLEFIN_KEY_FILE")
        if simplefin_key_file_env:
            simplefin_key_file = Path(simplefin_key_file_env)

    # if file provided, read it
    if simplefin_key_file:
        try:
            data = Path(simplefin_key_file).read_text(encoding="utf-8").strip()
        except Exception as e:
            typer.secho(f"Failed to read key file: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=2)
        if not data:
            typer.secho("Key file is empty", fg=typer.colors.RED)
            raise typer.Exit(code=2)
        return data

    if simplefin_key:
        return simplefin_key

    typer.secho(
        "You must provide either --simplefin-key or --simplefin-key-file",
        fg=typer.colors.RED,
    )
    raise typer.Exit(code=2)


def resolve_days_history():
    try:
        env_val = int(os.getenv("QUERY_HISTORY_DAYS"))
    except Exception as e:
        typer.secho(f"Failed to QUERY_HISTORY_DAYS: {e}", fg=typer.colors.RED)
        logging.info(f"Querying {env_val} days per DEFAULT_DAYS_HISTORY")
        return DEFAULT_DAYS_HISTORY
    if env_val:
        logging.info(f"Querying {env_val} days per QUERY_HISTORY_DAYS")
        return env_val
    else:
        logging.info(f"Querying {env_val} days per DEFAULT_DAYS_HISTORY")
        return DEFAULT_DAYS_HISTORY


def resolve_db_url(db: Optional[str]) -> str:
    """Resolve database URL from parameter or environment variable."""
    if db:
        return db

    db_path = os.getenv("SIMPLEFIN_DB_PATH")
    if db_path:
        # check if it's already a full URL (like postgresql://...)
        if "://" in db_path:
            return db_path
        else:
            return f"sqlite:///{db_path}"

    return SimpleFIN_DB.connection_str
def run_archiver_backend(
    simplefin_key: Optional[str] = None,
    simplefin_key_file: Optional[Path] = None,
    days_history: Optional[int] = None,
    db: Optional[str] = None,
    timeout: int = 20,
    debug: bool = False,
) -> str:
    """Core logic without Typer dependencies."""
    init_logging(debug)
    password = resolve_simplefin_key(simplefin_key, simplefin_key_file)
    db_url = resolve_db_url(db)

    if not days_history:
        days_history = resolve_days_history()

    conn = SimpleFIN(password, timeout=timeout, debug=debug)
    qr: QueryResult = conn.query_accounts(days_history=days_history)

    with SimpleFIN_DB(connection_str=db_url) as db_conn:
        db_conn.commit_query_result(qr)

    message = (
        f"Saved {len(qr.accounts)} accounts with "
        f"{len(qr.transactions)} transactions to {db_url}"
    )

    typer.secho(message, fg=typer.colors.GREEN)
    return message


@app.command()
def run_archiver(
    simplefin_key: Optional[str] = typer.Option(
        None,
        "--simplefin-key",
        help="SimpleFIN API key (mutually exclusive with --simplefin-key-file).\n"
        "Env var SIMPLEFIN_KEY can also be used.",
    ),
    simplefin_key_file: Optional[Path] = typer.Option(
        None,
        "--simplefin-key-file",
        help="Path to file containing SimpleFIN API key\n"
        "Env var SIMPLEFIN_KEY_FILE can also be used.",
    ),
    days_history: Optional[int] = typer.Option(
        None,
        "--days-history",
        help="Days of history to query",
    ),
    db: Optional[str] = typer.Option(
        None,
        "--db",
        help="SQLAlchemy DB URL (or use SIMPLEFIN_DB_PATH env var)",
    ),
    timeout: int = typer.Option(
        DEFAULT_TIMEOUT,
        "--timeout",
        help="Connection timeout in seconds",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug logging",
    ),
) -> None:
    """Query SimpleFIN and save accounts to the given DB."""
    return run_archiver_backend(simplefin_key, simplefin_key_file, days_history, db, timeout, debug)


if __name__ == "__main__":
    app()
