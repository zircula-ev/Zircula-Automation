import argparse
import email
import imaplib
import json
import os
from email.header import decode_header, make_header
from email.policy import default

from dotenv import load_dotenv

from booking_importer import _body_text, _sender_domain
from parser import parse_myturn_text
from parser_lastenrad import parse_lastenrad


SAFE_FIELDS = (
    "source",
    "status",
    "reservation_id",
    "resource_type",
    "item",
    "room",
    "booking_date",
    "return_date",
    "start_time",
    "end_time",
    "pickup_time",
    "return_time",
    "location",
)


def main():
    argument_parser = argparse.ArgumentParser(
        description="Inspect the newest booking mails without changing flags or calendars"
    )
    argument_parser.add_argument("--env-file", default=".env")
    argument_parser.add_argument("--mailbox", default="INBOX")
    arguments = argument_parser.parse_args()

    load_dotenv(arguments.env_file)

    required = ("IMAP_SERVER", "IMAP_USER", "IMAP_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Fehlende Variablen: " + ", ".join(missing))

    wanted = {
        "myturn.com": None,
        "lale-bremerhaven.de": None,
    }

    mailbox = imaplib.IMAP4_SSL(os.environ["IMAP_SERVER"])
    try:
        mailbox.login(os.environ["IMAP_USER"], os.environ["IMAP_PASSWORD"])
        status, _ = mailbox.select(arguments.mailbox, readonly=True)
        if status != "OK":
            raise RuntimeError("Postfach konnte nicht read-only geöffnet werden")

        status, result = mailbox.search(None, "ALL")
        if status != "OK":
            raise RuntimeError("Mailsuche fehlgeschlagen")

        for mail_id in reversed(result[0].split()):
            status, data = mailbox.fetch(mail_id, "(BODY.PEEK[])")
            if status != "OK":
                continue

            raw = next(
                (part[1] for part in data if isinstance(part, tuple)),
                None,
            )
            if raw is None:
                continue

            message = email.message_from_bytes(raw, policy=default)
            domain = _sender_domain(message)
            if domain not in wanted or wanted[domain] is not None:
                continue

            subject = str(
                make_header(decode_header(message.get("Subject", "")))
            )
            body = _body_text(message)
            if domain == "myturn.com":
                parsed = parse_myturn_text(body, subject)
            else:
                parsed = parse_lastenrad(body, subject)

            wanted[domain] = {
                "subject": subject,
                "parsed": {
                    key: parsed.get(key)
                    for key in SAFE_FIELDS
                },
            }

            if all(value is not None for value in wanted.values()):
                break
    finally:
        try:
            mailbox.logout()
        except Exception:
            pass

    print(json.dumps(wanted, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
