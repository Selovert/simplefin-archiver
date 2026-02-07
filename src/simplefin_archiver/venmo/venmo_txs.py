import logging
from datetime import date, timedelta
from typing import Optional

from simplefin_archiver import Transaction

from .imap import get_emails
from .parse_email import email_to_tx


def get_venmo_txs(
    email_addr: str,
    imap_passwd: str,
    start_date: Optional[date] = None,
) -> list[Transaction]:
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    logging.info(f"Fetching Venmo emails from {start_date}...")

    messages = get_emails(email_addr, imap_passwd, start_date)
    logging.info(f"Found {len(messages)} emails. Beginning parsing...")

    valid_transactions: list[Transaction] = []
    for msg in messages:
        try:
            tx = email_to_tx(msg)
            if tx:
                valid_transactions.append(tx)
        except Exception as e:
            logging.error(f"Failed to process email '{msg.subject}': {e}")
            continue

    logging.info(f"Successfully parsed {len(valid_transactions)} venmo transactions.")
    return valid_transactions
