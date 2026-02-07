import logging
from datetime import datetime
from typing import Optional

import regex
from bs4 import BeautifulSoup, Tag
from imap_tools.message import MailMessage

from simplefin_archiver import Transaction


def get_value_after_label(soup, label_text, tag_name="h2") -> str:
    label: Tag = soup.find(tag_name, string=regex.compile(rf"\s*{label_text}\s*"))
    if not label:
        raise ValueError(f"Label '{label_text}' not found in email.")

    value_tag = label.find_next_sibling()
    if not value_tag:
        raise ValueError(f"No element found after label '{label_text}'.")

    return value_tag.text.strip()


def parse_payment_tx(email: MailMessage) -> Optional[Transaction]:
    # init soup cursor
    soup = BeautifulSoup(email.html, "html.parser")

    # -- PARSE PAYEE --
    if " paid you" in email.subject:
        logging.info("Email identified as an incoming transaction.")
        payee_regex: str = r"^(.*?) paid you"
        tx_amount: float = 1.0
    elif email.subject.startswith("You paid "):
        logging.info("Email identified as an outgoing transaction.")
        payee_regex: str = r"^You paid (.+?) \p{Sc}"
        tx_amount: float = -1.0
    else:
        logging.info(f"Email is not a payment: {email.subject}")
        return None
    # regex pattern to match the payee
    search_result: regex.Match = regex.search(payee_regex, email.subject)
    # if no matches, can't proceed
    if not search_result or len(search_result.groups()) != 1:
        raise Exception(f"Can't parse payee from subject: {email.subject} (no regex match)")
    tx_payee: str = search_result.groups()[0]

    # -- PARSE AMOUNT --
    # take out commas from numbers like '1,000.00'
    clean_subj: str = email.subject.replace(",", "")
    # regex pattern to match the amount
    search_result: regex.Match = regex.search(r"\$(\d{1,5}\.\d\d)", clean_subj)
    # if no matches, can't proceed
    if not search_result or len(search_result.groups()) != 1:
        raise Exception(f"Can't parse tx amount from subject: {email.subject} (no regex match)")
    # extract the amount from the regex string match
    try:
        tx_amount = tx_amount * float(search_result.groups()[0])
        tx_amount = round(tx_amount, 2)
    except ValueError as ex:
        raise Exception(f"Could not parse transation amount from subject: {email.subject} ({ex})")

    # -- PARSE DESCRIPTION --
    p_texts: list[str] = [t.text for t in soup.find_all("p")]
    i_after: int = p_texts.index("See transaction")
    if not i_after:
        raise Exception("Could not parse tx description: <p>See transaction</p> not found.")
    tx_desc: str = p_texts[i_after - 1]

    # -- PARSE TRANSACTION ID --
    tx_id_text: str = get_value_after_label(soup, "Transaction ID", "h3")
    try:
        tx_id = int(tx_id_text)
    except ValueError:
        raise Exception(f"Could not parse transation ID from {tx_id_text}")

    tx = Transaction(
        id=f"{tx_id}",
        account_id=None,
        posted=datetime.combine(email.date, datetime.min.time()),
        amount=tx_amount,
        description=tx_desc,
        raw_json="Processed thru prefect",
        payee=tx_payee,
    )
    logging.info(f"Payment transaction parsed: {tx}")
    return tx


def parse_transfer_tx(email: MailMessage) -> Optional[Transaction]:
    # init soup cursor
    soup = BeautifulSoup(email.html, "html.parser")
    # unhappy path
    if "transfer has been initiated" not in email.subject:
        logging.info(f"Email is not a transfer: {email.subject}")
        return None

    # -- PARSE TRANSFER AMOUNT --
    tx_amt_text: str = get_value_after_label(soup, "Transfer Amount", "h2")
    try:
        tx_amount = float(tx_amt_text.replace("$", "").replace(",", "")) * -1
    except ValueError:
        raise Exception(f"Could not parse transfer amount from {tx_amt_text}")

    # -- PARSE TRANSFER ID --
    tx_id_text: str = get_value_after_label(soup, "Transfer transaction ID", "h2")
    try:
        tx_id = int(tx_id_text)
    except ValueError:
        raise Exception(f"Could not parse transfer ID from {tx_id_text}")

    # -- PARSE TRANSFER DESTINATION --
    tx_dest: str = get_value_after_label(soup, "Destination", "h2")

    tx = Transaction(
        id=f"{tx_id}",
        account_id=None,
        posted=datetime.combine(email.date, datetime.min.time()),
        amount=tx_amount,
        description=f"Transfer to {tx_dest}",
        raw_json="Processed thru prefect",
        payee=tx_amount,
    )
    logging.info(f"Transfer transaction parsed: {tx}")
    return tx


def email_to_tx(email: MailMessage) -> Transaction:
    logging.info(f"-- Processing venmo email: {email.subject}. --")
    payment_tx = parse_payment_tx(email)
    if payment_tx:
        return payment_tx
    transfer_tx = parse_transfer_tx(email)
    if transfer_tx:
        return transfer_tx

    logging.info("Email not processed.")
    return None
