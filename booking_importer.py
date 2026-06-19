import imaplib
import email
import os

from dotenv import load_dotenv
from bs4 import BeautifulSoup

from parser import parse_myturn_text
from parser_lastenrad import parse_lastenrad
from save_booking import save_booking
from email.header import decode_header

load_dotenv()

mail = imaplib.IMAP4_SSL(
    os.getenv("IMAP_SERVER")
)

mail.login(
    os.getenv("IMAP_USER"),
    os.getenv("IMAP_PASSWORD")
)

mail.select("INBOX")

status, messages = mail.search(
    None,
    "UNSEEN"
)

mail_ids = messages[0].split()

print(f"{len(mail_ids)} ungelesene Mails gefunden")

for mail_id in mail_ids:

    status, msg_data = mail.fetch(
        mail_id,
        "(RFC822)"
    )

    for response_part in msg_data:

        if not isinstance(response_part, tuple):
            continue

        msg = email.message_from_bytes(
            response_part[1]
        )

        subject = msg.get(
            "Subject",
            ""
        )

        decoded = decode_header(subject)[0]

        if isinstance(decoded[0], bytes):
            subject = decoded[0].decode(
                decoded[1] or "utf-8"
            )
        else:
            subject = decoded[0]

        print(f"Betreff: {subject}")

        if (
            "reservation" not in subject.lower()
            and "buchung" not in subject.lower()
        ):
            print(f"Übersprungen: {subject}")
            continue

        print(f"Verarbeite: {subject}")

        html = None

        for part in msg.walk():

            if (
                part.get_content_type()
                == "text/html"
            ):

                html = (
                    part.get_payload(
                        decode=True
                    )
                    .decode(
                        errors="ignore"
                    )
                )

                break

        if not html:
            continue

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        text = soup.get_text("\n")

        sender = msg.get("From", "")

        print(f"Absender: {sender}")

        if "lale-bremerhaven.de" in sender:

            print("-> CommonsBooking erkannt")

            data = parse_lastenrad(
                text,
                subject
            )

        else:

            print("-> MyTurn erkannt")

            data = parse_myturn_text(
                text,
                subject
            )

        print(data)

        data["raw_subject"] = subject

        save_booking(data)

        mail.store(
        mail_id,
        '+FLAGS',
        '\\Seen'
        )
        
        print(
            f"Gespeichert: "
            f"{data.get('reservation_id')}"
        )

mail.logout()

print("Fertig.")
