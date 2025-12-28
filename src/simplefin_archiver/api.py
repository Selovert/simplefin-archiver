from os import getenv

from fastapi import FastAPI, Depends

from .db import SimpleFIN_DB
from . import schemas

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


@app.get("/accounts_full", response_model=list[schemas.AccountDeepSchema])
def list_accounts_full(db: SimpleFIN_DB = Depends(get_db)):
    return db.get_accounts()


@app.get("/transactions", response_model=list[schemas.TransactionSchema])
def list_transactions(db: SimpleFIN_DB = Depends(get_db)):
    return db.get_transactions()


@app.get("/balances", response_model=list[schemas.BalanceSchema])
def list_balances(db: SimpleFIN_DB = Depends(get_db)):
    return db.get_balances()
