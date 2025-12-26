import logging
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

reg = registry()


@reg.mapped_as_dataclass
class Account:
    __tablename__ = "account"
    id: Mapped[str] = mapped_column(primary_key=True)
    bank: Mapped[str]
    name: Mapped[str]
    currency: Mapped[str]
    raw_json: Mapped[str] = mapped_column(repr=False)
    transactions: Mapped[list["Transaction"]] = relationship(
        foreign_keys="Transaction.account_id",
        back_populates="account",
        default_factory=list,
    )
    balances: Mapped[list["Balance"]] = relationship(
        foreign_keys="Balance.account_id",
        back_populates="account",
        default_factory=list,
    )


@reg.mapped_as_dataclass
class Balance:
    __tablename__ = "balance"
    id: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    balance: Mapped[float]
    balance_date: Mapped[datetime]
    available_balance: Mapped[float] = mapped_column(default=None)
    account: Mapped[Account | None] = relationship(
        foreign_keys="Balance.account_id",
        back_populates="balances",
        default=None,
    )

    def __post_init__(self):
        if not self.available_balance:
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
    raw_json: Mapped[str]
    payee: Mapped[str | None] = mapped_column(default=None)
    memo: Mapped[str | None] = mapped_column(default=None)
    category: Mapped[str | None] = mapped_column(default=None)
    tags: Mapped[str | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(default=None)
    account: Mapped[Account | None] = relationship(
        foreign_keys="Transaction.account_id",
        back_populates="transactions",
        default=None,
    )
    transacted_at: Mapped[datetime] = mapped_column(default=None)
    extra_attrs: Mapped[str] = mapped_column(default=None)

    def __post_init__(self):
        if not self.transacted_at:
            logging.debug(f"Auto-filling transacted_at for transaction {self.id}")
            self.transacted_at = self.posted

    # def to_dict(self)
