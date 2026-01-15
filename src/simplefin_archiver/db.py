from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .models import Account, Balance, Transaction
from .models import QueryResult

class SimpleFIN_DB:
    conn_timeout: int
    connection_str: str = "sqlite:///simplefin.db"

    def __init__(
        self,
        connection_str: Optional[str] = None,
        db_path: Optional[str] = None,
        conn_timeout: int = 10,
    ) -> None:
        if connection_str:
            self.connection_str = connection_str
        elif db_path:
            self.connection_str = f"sqlite:///{db_path}"
        else:
            self.connection_str = SimpleFIN_DB.connection_str
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

    def get_transactions(self) -> list[Transaction]:
        stmt = select(Transaction).order_by(Transaction.transacted_at.desc())
        results = self.session.scalars(stmt).all()
        return results

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
