from os import getenv

from fastapi import FastAPI, Depends, HTTPException, Security, BackgroundTasks
from fastapi.security import APIKeyHeader

from simplefin_archiver.models import Balance
from simplefin_archiver.db import SimpleFIN_DB
from simplefin_archiver.cli import run_archiver_backend
from simplefin_archiver import schemas

import logging


# suppress specific endpoint logging
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/health_check") == -1


# Add the filter to the uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_db():
    db_path = getenv("SIMPLEFIN_DB_PATH")
    connection_str = f"sqlite:///{db_path}"
    with SimpleFIN_DB(connection_str=connection_str) as db:
        yield db


def get_api_token():
    """Load API token from file (Docker secret) or environment variable."""
    token_file = getenv("ARCHIVER_API_KEY_FILE", "/run/secrets/ARCHIVER_API_KEY_FILE")

    try:
        with open(token_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to environment variable
        token = getenv("ARCHIVER_API_KEY")
        if not token:
            raise HTTPException(
                status_code=500,
                detail="API token not configured (no file or env var)"
            )
        return token


def verify_token(api_key: str = Security(api_key_header)):
    """Verify the API key matches the configured token."""
    expected_token = get_api_token()

    if not api_key or api_key != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )

    return api_key


@app.get("/health_check")
def health():
    """Public endpoint - no auth required."""
    return {"status": "ok"}


@app.get("/accounts", response_model=list[schemas.AccountSchema])
def list_accounts(db: SimpleFIN_DB = Depends(get_db),
                  token: str = Depends(verify_token)):
    return db.get_accounts()


@app.get("/transactions", response_model=list[schemas.TransactionSchema])
def list_transactions(db: SimpleFIN_DB = Depends(get_db),
                      token: str = Depends(verify_token)):
    return db.get_transactions()


@app.get("/balances", response_model=list[schemas.BalanceSchema])
def list_balances(db: SimpleFIN_DB = Depends(get_db),
                  token: str = Depends(verify_token)):
    return db.get_balances()


@app.post("/balances", response_model=schemas.BalanceSchema)
def create_balance(balance_data: schemas.BalanceCreateSchema,
                   db: SimpleFIN_DB = Depends(get_db),
                   token: str = Depends(verify_token)):
    # Convert Pydantic schema to SQLAlchemy model
    new_balance = Balance(**balance_data.model_dump())
    return db.add_balance(new_balance)

@app.post("/trigger_update")
def trigger_update(background_tasks: BackgroundTasks,
                   token: str = Depends(verify_token)):
    background_tasks.add_task(run_archiver_backend)
    return {"message": "Archive update triggered"}
