from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

# Base configuration to share across all models
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# --- ACCOUNT ---

# A "Shallow" Account schema for use inside children
class AccountSchema(BaseSchema):
    id: str
    bank: str
    name: str
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
    account: AccountSchema

# --- BALANCE ---

# Base balance fields
class BalanceBasicSchema(BaseSchema):
    id: str
    balance: float
    balance_date: datetime


# Balance including the Account info
class BalanceSchema(BalanceBasicSchema):
    account: AccountSchema


class BalanceCreateSchema(BaseSchema):
    id: str
    account_id: str
    balance: float
    balance_date: datetime
    raw_json: str
    available_balance: Optional[float] = None

# --- QUERY LOG ---
class QueryLogSchema(BaseSchema):
    id: str
    query_time: datetime
    days_history: int