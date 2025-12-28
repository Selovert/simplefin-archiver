from fastapi import FastAPI, Depends

from .db import SimpleFIN_DB

app = FastAPI()


def get_db():
    with SimpleFIN_DB() as db:
        yield db


@app.get("/health_check")
def health():
    return {"status": "ok"}


@app.get("/accounts")
def list_accounts(db: SimpleFIN_DB = Depends(get_db)):
    return db.get_accounts()


@app.get("/transactions")
def list_transactions(db: SimpleFIN_DB = Depends(get_db)):
    return db.get_transactions()


@app.get("/balances")
def list_balances(db: SimpleFIN_DB = Depends(get_db)):
    return db.get_balances()
