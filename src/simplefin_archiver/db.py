from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .models import Account, Balance, QueryLog, Transaction


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
        for new_acct in accounts:
            # Fetch the existing account
            db_acct = self.session.get(Account, new_acct.id)

            if db_acct:
                # Identify new transactions
                incoming_tx_ids = [tx.id for tx in new_acct.transactions]
                stmt_tx = select(Transaction.id).where(Transaction.id.in_(incoming_tx_ids))
                existing_tx_ids = set(self.session.scalars(stmt_tx).all())
                new_txs = [tx for tx in new_acct.transactions if tx.id not in existing_tx_ids]

                # Identify new balances
                incoming_bal_ids = [bal.id for bal in new_acct.balances]
                stmt_bal = select(Balance.id).where(Balance.id.in_(incoming_bal_ids))
                existing_bal_ids = set(self.session.scalars(stmt_bal).all())
                new_balances = [bal for bal in new_acct.balances if bal.id not in existing_bal_ids]

                # Add to the session-tracked object
                db_acct.transactions.extend(new_txs)
                db_acct.balances.extend(new_balances)

                db_acct.name = new_acct.name
                db_acct.raw_json = new_acct.raw_json
            else:
                # If it's truly new, add the whole tree
                self.session.add(new_acct)

        if query_log:
            self.session.add(query_log)

        self.session.commit()