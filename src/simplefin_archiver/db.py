from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from simplefin_archiver import Account, Transaction, Balance, QueryLog


class SimpleFIN_DB:
    connection_str: str = "sqlite:///simplefin.db"

    def __init__(self, db_path: str | None = None) -> None:
        self.connection_str = f"sqlite:///{db_path}" if db_path else SimpleFIN_DB.connection_str

    def __enter__(self):
        self.engine = create_engine(self.connection_str)
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

    def commit_accounts(
        self, accounts: list[Account], query_log: QueryLog = None
    ) -> None:

        # Collect all transaction IDs from incoming accounts
        incoming_tx_ids = {tx.id for account in accounts for tx in account.transactions}

        # Only query the DB for IDs we might actually insert
        existing_tx_ids = {
            id_tuple[0]
            for id_tuple in self.session.query(Transaction.id)
            .filter(Transaction.id.in_(incoming_tx_ids))
            .all()
        }

        # Merge accounts, transactions, and balances
        for acct in accounts:
            # filter out existing transactions before adding to db
            acct.transactions = [tx for tx in acct.transactions if tx.id not in existing_tx_ids]
            self.session.merge(acct)

        # query logs to keep build history of raw json responses
        if query_log:
            self.session.add(query_log)

        self.session.commit()
