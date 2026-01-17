import os

from prefect import flow, task
from prefect.artifacts import create_table_artifact
from prefect.blocks.system import Secret
from prefect.logging import get_run_logger

from simplefin_archiver import QueryResult, SimpleFIN
from simplefin_archiver.db import SimpleFIN_DB
from simplefin_archiver.schemas import AccountSchema as A_Schema
from simplefin_archiver.schemas import BalanceBasicSchema as B_Schema
from simplefin_archiver.schemas import TransactionBasicSchema as Tx_Schema


@task(
    retries=2,
    retry_delay_seconds=[60],
)
def request_simplefin() -> QueryResult:
    _logger = get_run_logger()
    secret_block = Secret.load("simplefin-api-key")
    conn: SimpleFIN = SimpleFIN(
        secret_block.get(),
        debug=True,
        timeout=30,
        logger=_logger,
    )

    _logger.info("Querying to SimpleFin...")
    qr: QueryResult = conn.query_accounts()

    create_table_artifact(
        table=[A_Schema.model_validate(a).model_dump(mode='json') for a in qr.accounts],
        key="query-result-accounts-table",
        description="# Accounts in SimpleFIN query result"
    )
    create_table_artifact(
        table=[B_Schema.model_validate(b).model_dump(mode='json') for b in qr.balances],
        key="query-result-balances-table",
        description="# Balances in SimpleFIN query result"
    )
    create_table_artifact(
        table=[Tx_Schema.model_validate(tx).model_dump(mode='json') for tx in qr.transactions],
        key="query-result-transactions-table",
        description="# Transactions in SimpleFIN query result"
    )

    return qr

@task
def write_to_db(q_result: QueryResult):
    _logger = get_run_logger()
    _logger.info("Opening connection to SimpleFIN_DB...")
    secret_block = Secret.load("simplefin-db-pass")
    # os.environ["POSTGRES_HOST"] = "192.168.0.11"
    # os.environ["POSTGRES_PORT"] = "8010"
    os.environ["POSTGRES_PASSWORD"] = secret_block.get()
    with SimpleFIN_DB(conn_timeout=60, logger=_logger) as db:
        db.commit_query_result(q_result)

@flow(name="update_accounts")
def update_accounts():
    q_result: QueryResult = request_simplefin()
    write_to_db(q_result)
