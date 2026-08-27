import email
import imaplib
import os
from email.header import decode_header, make_header
from email.policy import default
from email.utils import parseaddr

from bs4 import BeautifulSoup
from dotenv import load_dotenv

from calendar_sync import CalDAVCalendar
from parser import parse_myturn_text
from parser_lastenrad import parse_lastenrad


def _domains(name):
    return {
        value.strip().lower()
        for value in os.getenv(name, "").split(",")
        if value.strip()
    }


def _sender_domain(message):
    address = parseaddr(message.get("From", ""))[1]
    return address.rsplit("@", 1)[-1].lower() if "@" in address else ""


def _matches(domain, allowed):
    return any(domain == item or domain.endswith("." + item) for item in allowed)


def _body_text(message):
    html = None
    plain = None

    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue

        payload = part.get_payload(decode=True)
        if payload is None:
            continue

        charset = part.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")

        if part.get_content_type() == "text/html" and html is None:
            html = text
        elif part.get_content_type() == "text/plain" and plain is None:
            plain = text

    if html:
        return BeautifulSoup(html, "html.parser").get_text("\n")
    return plain or ""


def _parse(message, subject, myturn_domains, commonsbooking_domains):
    domain = _sender_domain(message)

    if _matches(domain, commonsbooking_domains):
        return parse_lastenrad(_body_text(message), subject)

    if _matches(domain, myturn_domains):
        return parse_myturn_text(_body_text(message), subject)

    raise ValueError(f"Nicht freigegebene Absenderdomain: {domain or 'unbekannt'}")


def main():
    load_dotenv()

    required = ["IMAP_SERVER", "IMAP_USER", "IMAP_PASSWORD"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Fehlende Konfiguration: " + ", ".join(missing))

    myturn_domains = _domains("MYTURN_SENDER_DOMAINS")
    commonsbooking_domains = _domains("COMMONSBOOKING_SENDER_DOMAINS")
    if not myturn_domains or not commonsbooking_domains:
        raise RuntimeError(
            "MYTURN_SENDER_DOMAINS und COMMONSBOOKING_SENDER_DOMAINS müssen gesetzt sein"
        )

    calendar = CalDAVCalendar.from_environment()
    calendar.check()

    mailbox = imaplib.IMAP4_SSL(os.environ["IMAP_SERVER"])
    try:
        mailbox.login(os.environ["IMAP_USER"], os.environ["IMAP_PASSWORD"])
        mailbox.select(os.getenv("IMAP_FOLDER", "INBOX"))

        status, messages = mailbox.search(None, "UNSEEN")
        if status != "OK":
            raise RuntimeError("IMAP-Suche fehlgeschlagen")

        mail_ids = messages[0].split()
        print(f"{len(mail_ids)} ungelesene Mails gefunden")

        for mail_id in mail_ids:
            try:
                status, message_data = mailbox.fetch(mail_id, "(RFC822)")
                if status != "OK":
                    raise RuntimeError("IMAP-Abruf fehlgeschlagen")

                raw = next(
                    part[1]
                    for part in message_data
                    if isinstance(part, tuple)
                )
                message = email.message_from_bytes(raw, policy=default)
                subject = str(make_header(decode_header(message.get("Subject", ""))))

                if (
                    "reservation" not in subject.lower()
                    and "buchung" not in subject.lower()
                    and "storn" not in subject.lower()
                ):
                    print(f"Übersprungen: {subject}")
                    continue

                data = _parse(
                    message,
                    subject,
                    myturn_domains,
                    commonsbooking_domains,
                )
                data["raw_subject"] = subject

                result = calendar.sync(data)
                mailbox.store(mail_id, "+FLAGS", "\\Seen")
                print(
                    f"{result}: {data.get('source', 'myturn')}/"
                    f"{data.get('reservation_id')}"
                )
            except Exception as exc:
                print(f"Fehler bei Mail {mail_id.decode()}: {exc}")
                # Ungelesen lassen, damit der nächste Lauf erneut versucht.
    finally:
        try:
            mailbox.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
