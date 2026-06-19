import imaplib
import email
import os

from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

mail = imaplib.IMAP4_SSL(os.getenv("IMAP_SERVER"))
mail.login(
    os.getenv("IMAP_USER"),
    os.getenv("IMAP_PASSWORD")
)

mail.select("INBOX")

status, messages = mail.search(None, "ALL")
mail_ids = messages[0].split()

for mail_id in reversed(mail_ids):

    status, msg_data = mail.fetch(mail_id, "(RFC822)")

    for response_part in msg_data:

        if not isinstance(response_part, tuple):
            continue

        msg = email.message_from_bytes(response_part[1])

        subject = msg.get("Subject", "")

        if "reservation" not in subject.lower():
            continue

        print(f"\nSUBJECT: {subject}\n")

        for part in msg.walk():

            if part.get_content_type() != "text/html":
                continue

            html = part.get_payload(decode=True).decode(
                errors="ignore"
            )

            soup = BeautifulSoup(html, "html.parser")

            text = soup.get_text("\n")

            print(text[:5000])

            mail.logout()
            raise SystemExit
