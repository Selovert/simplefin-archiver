from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from simplefin_archiver import Account, Balance, QueryLog, Transaction


class SimpleFIN_DB:
    conn_timeout: int
    connection_str: str = "sqlite:///simplefin.db"

    def __init__(self, db_path: Optional[str] = None, conn_timeout: int = 10) -> None:
        self.connection_str = f"sqlite:///{db_path}" if db_path else SimpleFIN_DB.connection_str
        self.conn_timeout = conn_timeout

    def __enter__(self):
        conn_args = {"timeout": self.conn_timeout}
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

    def commit_accounts(self, accounts: list[Account], query_log: QueryLog = None) -> None:
        for incoming_acct in accounts:
            # Get the existing account from DB (if it exists)
            db_acct = self.session.get(Account, incoming_acct.id)

            if db_acct:
                # Identify new transactions
                db_tx_ids = {tx.id for tx in db_acct.transactions}
                new_txs = [tx for tx in incoming_acct.transactions if tx.id not in db_tx_ids]
                db_acct.transactions.extend(new_txs)

                # Identify new balances
                db_balance_ids = {bal.id for bal in db_acct.balances}
                new_balances = [bal for bal in incoming_acct.balances if bal.id not in db_balance_ids]
                db_acct.balances.extend(new_balances)
                # (commit new state below)
            else:
                # If it's a brand new account, just add it
                self.session.add(incoming_acct)

        if query_log:
            self.session.add(query_log)
        self.session.commit()