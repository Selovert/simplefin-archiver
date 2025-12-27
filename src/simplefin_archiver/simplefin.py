import json
import logging
from datetime import datetime, timedelta

import requests

from simplefin_archiver import Account, Balance, Transaction, QueryLog

from typing import NamedTuple

ACCT_DUMP_EXLUDES = { # keys to exclude from raw_json dump
    "balance",
    "available-balance",
    "balance-date",
    "transactions",
    "holdings",
}

BALANCE_DUMP_EXLUDES = { # keys to exclude from raw_json dump
    "org",
    "name",
    "currency",
    "transactions",
    "holdings",
}


class QueryResult(NamedTuple):
    accounts: list[Account]
    querylog: QueryLog


class SimpleFIN:
    __API_URL: str
    __api_user: str
    __api_passwd: str
    __timeout: int
    debug: bool

    def __init__(self, api_token: str, debug: bool = False, timeout: int = 10):
        self.__API_URL = "https://beta-bridge.simplefin.org/simplefin"
        self.__api_user = api_token.split(":")[0]
        self.__api_passwd = api_token.split(":")[1]
        self.debug = debug
        self.__timeout = 10

    def query_accounts(self, days_history: int = 7) -> QueryResult:
        start_date = datetime.now() - timedelta(days=days_history)
        logging.info(f"start_date is {start_date.isoformat(timespec='hours')}")

        logging.info(f"Initiating request to {self.__API_URL}/accounts...")
        resp = requests.get(
            url=f"{self.__API_URL}/accounts",
            auth=(self.__api_user, self.__api_passwd),
            params={"start-date": f"{int(start_date.timestamp())}"},
            timeout=self.__timeout,
        )
        if resp.status_code != 200:
            if self.debug:
                raise Exception(f"Request error: {resp.text}")
            else:
                raise Exception(f"Request error: {resp.status_code}")

        if self.debug:
            logging.debug(f"Request successful\n{resp.text}\nParsing account data...")
        else:
            logging.info("Request successful; parsing account data...")
        accts_raw: list[dict] = resp.json()["accounts"]
        if not len(accts_raw):
            if self.debug:
                raise Exception(f"No accounts found.\n{resp.text}")
            else:
                raise Exception("No accounts found.")
        elif self.debug:
            logging.debug(f"{len(accts_raw)} raw accounts found:")
            for a in accts_raw:
                logging.debug(a)

        accounts: list[Account] = []
        for acct_raw in accts_raw:
            # get account name
            acct_name: str = acct_raw["name"]
            # get the org name
            bank: str = acct_raw["org"].get("name")
            if not bank:  # if org name is missing, org domain is required by simpleFIN
                bank = acct_raw["org"].get("domain")
                logging.info(f"Defaulted '{acct_name}' org name to domain '{bank}'")
            # generate raw json without temporal data
            acct_raw_json = json.dumps(
                {
                    k: v
                    for k, v in acct_raw.items()
                    if k not in ACCT_DUMP_EXLUDES
                }
            )

            acct = Account(
                id=acct_raw["id"],
                bank=bank,
                name=acct_name,
                currency=acct_raw["currency"],
                raw_json=acct_raw_json,
                transactions=[],
            )
            if self.debug:
                logging.debug(f"Loaded account: {acct}")

            # balance
            if self.debug:
                logging.debug(f"Loading balance for account {acct.id}...")
            balance = SimpleFIN._get_balance(acct_raw, self.debug)
            acct.balances.append(balance)

            # transactions
            if self.debug:
                logging.debug(f"Loading transactions for account {acct.id}...")
            txs = SimpleFIN._get_transactions(acct_raw, self.debug)
            logging.info(f"Loaded {len(txs):>3} transactions for account {acct.name}")
            acct.transactions = txs

            accounts.append(acct)

        # create query log
        q_log = QueryLog(
            query_date=datetime.now(),
            days_history=days_history,
            raw_response=resp.text,
        )
        if self.debug:
            logging.debug(f"Created query log: {q_log}")

        return QueryResult(accounts=accounts, querylog=q_log)

    @staticmethod
    def _get_balance(acct_raw:dict, debug:bool=False) -> list[Transaction]:
        # get account name
        acct_name: str = acct_raw["name"]
        # get balance date
        try:
            balance_date = datetime.fromtimestamp(int(acct_raw["balance-date"]))
        except Exception as ex:
            logging.warning(
                f"Couldn't get balance date for {acct_name}: {ex}.\nDefaulting to today."
            )
            balance_date = datetime.now()
        # scrub time portion
        balance_date = balance_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # get the balance
        try:
            balance: float = float(acct_raw["balance"])
        except Exception as ex:
            logging.warning(
                f"Couldn't get balance for {acct_name}: {ex}.\nDefaulting to 0"
            )

            balance: float = 0.0

        # available balance
        try:
            available_balance_raw: str | None = acct_raw.get("available-balance")
            if available_balance_raw is not None:
                available_balance: float | None = float(available_balance_raw)
        except Exception as ex:
            logging.info(f"Could not get available balance for {acct_name}: {ex}.")
            available_balance: float | None = None

        # generate a balance id
        balance_id: str = f"{acct_raw['id']}_{balance_date.strftime('%Y-%m-%d')}"

        # generate raw json
        balance_raw_json = json.dumps(
            {
                k: v
                for k, v in acct_raw.items()
                if k not in BALANCE_DUMP_EXLUDES
            }
        )

        balance: Balance = Balance(
            id=balance_id,
            account_id=acct_raw["id"],
            balance=balance,
            balance_date=balance_date,
            available_balance=available_balance,
            raw_json=balance_raw_json,
        )
        if debug:
            logging.debug(f"Loaded balance: {balance}")

        return balance



    @staticmethod
    def _get_transactions(acct_raw:dict, debug:bool=False) -> list[Transaction]:
        txs: list[Transaction] = []
        txs_raw: list[dict] = acct_raw.get("transactions")
        for tx_raw in txs_raw:
            tx_id: str = tx_raw["id"]
            # extra dict of data we're not explicitly pulling
            known_keys = [
                "id",
                "amount",
                "description",
                "posted",
                "transacted_at",
                "payee",
                "memo"
            ]
            extra: dict = {k: v for k, v in tx_raw.items() if k not in known_keys}

            # posted date
            try:
                posted_date = datetime.fromtimestamp(int(tx_raw["posted"]))
            except Exception as ex:
                raise Exception(f"Could not get posted data for {tx_id}: {ex}")

            # amount
            try:
                amount: float = float(tx_raw["amount"])
            except Exception as ex:
                raise Exception(f"Could not get amount for {tx_id}: {ex}")

            # date transacted
            try:
                tx_at: datetime = tx_raw.get("transacted_at")
                if tx_at is not None:
                    tx_at: float | None = datetime.fromtimestamp(int(tx_at))
            except Exception as ex:
                logging.info(f"Couldn't get transacted date for {tx_id}: {ex}")
                tx_at: float | None = None

            tx: Transaction = Transaction(
                id=tx_id,
                account_id=acct_raw["id"],
                posted=posted_date,
                amount=amount,
                description=tx_raw["description"],
                raw_json=json.dumps(tx_raw),
                payee=tx_raw.get("payee"),
                memo=tx_raw.get("memo"),
                transacted_at=tx_at,
                extra_attrs=json.dumps(extra),
            )
            if debug:
                logging.debug(f"Loaded transaction: {tx}")

            txs.append(tx)

        return txs
