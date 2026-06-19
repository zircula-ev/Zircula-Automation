import imaplib
import email
from dotenv import load_dotenv
import os

load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(IMAP_USER, IMAP_PASSWORD)

mail.select("INBOX")

status, messages = mail.search(None, "ALL")
mail_ids = messages[0].split()

print(f"Gefundene Mails: {len(mail_ids)}")

for mail_id in mail_ids[-5:]:
    status, msg_data = mail.fetch(mail_id, "(RFC822.HEADER)")

    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])

            print("\n----------------")
            print("Betreff:", msg.get("Subject"))
            print("Von:", msg.get("From"))
            print("Datum:", msg.get("Date"))

mail.logout()
