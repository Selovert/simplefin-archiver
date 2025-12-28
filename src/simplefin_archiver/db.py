from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from simplefin_archiver import Account, QueryLog


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
