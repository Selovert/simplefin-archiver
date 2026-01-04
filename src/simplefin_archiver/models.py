import logging
from datetime import datetime
from typing import Optional, NamedTuple

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

reg = registry()

@reg.mapped_as_dataclass
class QueryLog:
    __tablename__ = "query_log"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    query_date: Mapped[datetime]
    days_history: Mapped[int]
    raw_response: Mapped[str] = mapped_column(repr=False)


@reg.mapped_as_dataclass
class Account:
    __tablename__ = "account"
    id: Mapped[str] = mapped_column(primary_key=True)
    bank: Mapped[str]
    name: Mapped[str]
    currency: Mapped[str]
    raw_json: Mapped[str] = mapped_column(repr=False)

@reg.mapped_as_dataclass
class Balance:
    __tablename__ = "balance"
    id: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    balance: Mapped[float]
    balance_date: Mapped[datetime]
    raw_json: Mapped[str] = mapped_column(repr=False)
    available_balance: Mapped[Optional[float]] = mapped_column(default=None)
    account: Mapped["Account"] = relationship(
        default=None,
        init=False,
        lazy="selectin"  # This ensures data is loaded before the session closes
    )

    def __post_init__(self):
        if self.available_balance is None:
            logging.debug(f"Auto-filling balance for account {self.id}")
            self.available_balance = self.balance


@reg.mapped_as_dataclass
class Transaction:
    __tablename__ = "transaction"
    id: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    posted: Mapped[datetime]
    amount: Mapped[float]
    description: Mapped[str]
    raw_json: Mapped[str] = mapped_column(repr=False)
    payee: Mapped[Optional[str]] = mapped_column(default=None)
    memo: Mapped[Optional[str]] = mapped_column(default=None)
    category: Mapped[Optional[str]] = mapped_column(default=None)
    tags: Mapped[Optional[str]] = mapped_column(default=None)
    notes: Mapped[Optional[str]] = mapped_column(default=None)
    transacted_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    extra_attrs: Mapped[Optional[str]] = mapped_column(default=None)
    account: Mapped["Account"] = relationship(
        default=None,
        init=False,
        lazy="selectin"  # This ensures data is loaded before the session closes
    )

    def __post_init__(self):
        if self.transacted_at is None:
            logging.debug(f"Auto-filling transacted_at for transaction {self.id}")
            self.transacted_at = self.posted

class QueryResult(NamedTuple):
    accounts: list[Account]
    balances: list[Balance]
    transactions: list[Transaction]
    querylog: QueryLog
