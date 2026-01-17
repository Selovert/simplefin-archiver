import os
import logging
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .models import Account, Balance, Transaction
from .models import QueryResult

def get_db_connection_string(logger: logging.Logger = None) -> str:
    """
    Priority:
    1. Explicit function argument (handled by callers)
    2. POSTGRES_PASSWORD env var (Constructs full Postgres URL)
    3. SIMPLEFIN_DB_PATH env var (File path or custom URL)
    4. Default SQLite file
    """
    if not logger:
        logger = logging.getLogger()

    # Check for Postgres credentials (Env vars specific to your container setup)
    pg_pass = os.getenv("POSTGRES_PASSWORD")
    if pg_pass:
        user = os.getenv("POSTGRES_USER", "simplefin")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        dbname = os.getenv("POSTGRES_DB", "simplefin_db")

        # Construct the safe URL
        logger.info(f"Connecting to postgres {user}@{host}:{port}/{dbname}")
        return f"postgresql+psycopg2://{user}:{pg_pass}@{host}:{port}/{dbname}"

    # Fallback to your old logic
    db_path = os.getenv("SIMPLEFIN_DB_PATH")
    if db_path:
        logger.info(f"Connecting to sqlite at path {db_path}")
        return f"sqlite:///{db_path}"

    logger.info("Connecting to sqlite at default simplefin.db")
    return "sqlite:///simplefin.db"

class SimpleFIN_DB:
    conn_timeout: int
    logger: logging.Logger

    def __init__(
        self,
        connection_str: Optional[str] = None,
        db_path: Optional[str] = None,
        conn_timeout: int = 10,
        logger: logging.Logger = None,
    ) -> None:
        self.logger = logger or logging.getLogger()
        if connection_str:
            self.connection_str = connection_str
        elif db_path:
            self.connection_str = f"sqlite:///{db_path}"
        else:
            self.connection_str = get_db_connection_string()
        self.conn_timeout = conn_timeout

    def __enter__(self):
        conn_args = {}
        if self.connection_str.startswith("sqlite"):
            conn_args["timeout"] = self.conn_timeout

        self.engine = create_engine(self.connection_str, connect_args=conn_args)
        self.session = Session(self.engine)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.close()
        self.engine.dispose()

    def get_accounts(self) -> list[Account]:
        stmt = select(Account).order_by(Account.bank, Account.name)
        results = self.session.scalars(stmt).all()
        return results

    def add_account(self, account: Account) -> Account:
        merged_account = self.session.merge(account)
        try:
            self.session.commit()
            self.session.refresh(merged_account)
            return merged_account
        except Exception:
            self.session.rollback()
            raise

    def get_transactions(self) -> list[Transaction]:
        stmt = select(Transaction).order_by(Transaction.transacted_at.desc())
        results = self.session.scalars(stmt).all()
        return results

    def add_transaction(self, transaction: Transaction) -> Balance:
        merged_tx = self.session.merge(transaction)
        try:
            self.session.commit()
            # Refresh to load the relationship 'account' for the response schema
            self.session.refresh(merged_tx)
            return merged_tx
        except Exception:
            self.session.rollback()
            raise


    def get_balances(self) -> list[Balance]:
        stmt = select(Balance).order_by(Balance.balance_date.desc())
        results = self.session.scalars(stmt).all()
        return results

    def add_balance(self, balance: Balance) -> Balance:
        merged_balance = self.session.merge(balance)
        try:
            self.session.commit()
            # Refresh to load the relationship 'account' for the response schema
            self.session.refresh(merged_balance)
            return merged_balance
        except Exception:
            self.session.rollback()
            raise

    def commit_query_result(self, query_result: QueryResult) -> None:
        # Save query log
        self.session.merge(query_result.querylog)

        # Update accounts and overwrite existing ones
        for acct in query_result.accounts:
            self.session.merge(acct)

        # Create a quick lookup map: { id: AccountObject }
        acct_map = {acct.id: acct for acct in query_result.accounts}

        # Save new balances only (don't want to overwrite)
        incoming_bal_ids = [bal.id for bal in query_result.balances]
        if incoming_bal_ids:
            # Query the DB for which of these IDs already exist
            stmt = select(Balance.id).where(Balance.id.in_(incoming_bal_ids))
            existing_bal_ids = set(self.session.scalars(stmt).all())

            # Add only the ones not found in the DB
            for bal in query_result.balances:
                if bal.id not in existing_bal_ids:
                    bal.account = acct_map[bal.account_id]
                    self.session.merge(bal)

        # Save new transactions only (don't want to overwrite)
        incoming_tx_ids = [tx.id for tx in query_result.transactions]
        if incoming_tx_ids:
            # Query the DB for which of these IDs already exist
            stmt = select(Transaction.id).where(Transaction.id.in_(incoming_tx_ids))
            existing_tx_ids = set(self.session.scalars(stmt).all())

            # Add only the ones not found in the DB
            for tx in query_result.transactions:
                if tx.id not in existing_tx_ids:
                    tx.account = acct_map[tx.account_id]
                    self.session.merge(tx)

        # Commit all changes
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
