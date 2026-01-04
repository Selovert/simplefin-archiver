from os import getenv

from fastapi import FastAPI, Depends

from simplefin_archiver.models import Balance
from simplefin_archiver.db import SimpleFIN_DB
from simplefin_archiver import schemas

app = FastAPI()


def get_db():
    db_path = getenv("SIMPLEFIN_DB_PATH")
    connection_str = f"sqlite:///{db_path}"
    with SimpleFIN_DB(connection_str=connection_str) as db:
        yield db


@app.get("/health_check")
def health():
    return {"status": "ok"}


@app.get("/accounts", response_model=list[schemas.AccountSchema])
def list_accounts(db: SimpleFIN_DB = Depends(get_db)):
    return db.get_accounts()


@app.get("/transactions", response_model=list[schemas.TransactionSchema])
def list_transactions(db: SimpleFIN_DB = Depends(get_db)):
    return db.get_transactions()


@app.get("/balances", response_model=list[schemas.BalanceSchema])
def list_balances(db: SimpleFIN_DB = Depends(get_db)):
    return db.get_balances()


@app.post("/balances", response_model=schemas.BalanceSchema)
def create_balance(balance_data: schemas.BalanceCreateSchema, db: SimpleFIN_DB = Depends(get_db)):
    # Convert Pydantic schema to SQLAlchemy model
    new_balance = Balance(**balance_data.model_dump())
    return db.add_balance(new_balance)
