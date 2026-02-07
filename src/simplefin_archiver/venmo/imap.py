import datetime

from imap_tools import AND, MailBox, MailMessage


def get_emails(email_addr: str, imap_passwd: str, start_date: datetime.date) -> list[MailMessage]:
    """
    Connects to the specified IMAP server and fetches Venmo emails.
    """
    msgs = []

    try:
        with MailBox("imap.gmail.com").login(email_addr, imap_passwd) as mailbox:
            criteria = AND(
                from_="venmo@venmo.com",
                date_gte=start_date,
            )
            for msg in mailbox.fetch(criteria, mark_seen=False):
                msgs.append(msg)
    except Exception as e:
        raise Exception(f"Failed to fetch emails for {email_addr}: {e}")

    return msgs
