from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from simplefin_archiver import Account, QueryLog


class SimpleFIN_DB:
    connection_str: str = "sqlite:///simplefin.db"

    def __init__(self, connection_str: str | None = None) -> None:
        self.connection_str = connection_str or SimpleFIN_DB.connection_str

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
        for account in accounts:
            self.session.merge(account)

        if query_log:
            self.session.add(query_log)

        self.session.commit()
