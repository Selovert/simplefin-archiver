#!/usr/bin/env python3
"""Typer CLI to query accounts via SimpleFIN and persist to a local SQLite DB.

Placed inside the `tassilo_simplefin` package so it can be installed as a console script.
"""

import logging
from copy import deepcopy
from pathlib import Path
from typing import Optional

import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import tassilo_simplefin.models as models
from tassilo_simplefin import SimpleFIN

app = typer.Typer(help="Query SimpleFIN and persist accounts to a SQLite DB")


def init_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s - %(name)s - %(message)s")


def commit_accounts(accounts, db_url: str) -> None:
    engine = create_engine(db_url)
    models.reg.metadata.create_all(engine)
    session = Session(engine)
    for account in deepcopy(accounts):
        session.merge(account)
    session.commit()
    session.close()


def resolve_simplefin_key(
    simplefin_key: Optional[str], simplefin_key_file: Optional[Path]
) -> str:
    if simplefin_key and simplefin_key_file:
        typer.secho(
            "Provide only one of --simplefin-key or --simplefin-key-file",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

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


@app.command()
def run(
    days_history: int = typer.Option(
        14, "--days-history", help="days of history to query"
    ),
    db: str = typer.Option("sqlite:///SimpleFIN.db", "--db", help="SQLAlchemy DB URL"),
    simplefin_key: Optional[str] = typer.Option(
        None,
        "--simplefin-key",
        help="SimpleFIN API key (mutually exclusive with --simplefin-key-file)",
    ),
    simplefin_key_file: Optional[Path] = typer.Option(
        None, "--simplefin-key-file", help="Path to file containing SimpleFIN API key"
    ),
    timeout: int = typer.Option(20, "--timeout", help="connection timeout in seconds"),
    debug: bool = typer.Option(False, "--debug", help="enable debug logging"),
) -> None:
    """Query SimpleFIN and save accounts to the given DB."""
    init_logging(debug)

    password = resolve_simplefin_key(simplefin_key, simplefin_key_file)

    conn = SimpleFIN(password, timeout=timeout, debug=debug)
    accounts = conn.query_accounts(days_history=days_history)

    commit_accounts(accounts, db)

    txs = [tx for acct in accounts for tx in acct.transactions]
    typer.secho(
        f"Saved {len(accounts)} accounts with {len(txs)} transactions to {db}",
        fg=typer.colors.GREEN,
    )


if __name__ == "__main__":
    app()
