from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

# Base configuration to share across all models
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# --- ACCOUNT ---

# A "Shallow" Account schema for use inside children
class AccountBasicSchema(BaseSchema):
    id: str
    bank: str
    name: str

# The main Account schema (without lists)
class AccountSchema(AccountBasicSchema):
    currency: str

# --- TRANSACTION ---

# Base transaction fields
class TransactionBasicSchema(BaseSchema):
    id: str
    posted: datetime
    amount: float
    description: str
    transacted_at: Optional[datetime]

# Transaction including the Account info
class TransactionSchema(TransactionBasicSchema):
    account: AccountBasicSchema

# --- BALANCE ---

# Base balance fields
class BalanceBasicSchema(BaseSchema):
    id: str
    balance: float
    balance_date: datetime

# Balance including the Account info
class BalanceSchema(BaseSchema):
    account: AccountBasicSchema

# --- DEEP MODELS ---

# The main Account schema including transactions and balances
class AccountDeepSchema(AccountSchema):
    transactions: list[TransactionBasicSchema]
    balances: list[BalanceBasicSchema]