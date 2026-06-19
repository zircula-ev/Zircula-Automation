import imaplib
import email
from dotenv import load_dotenv
import os

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

        print("\n====================")
        print(subject)
        print("====================")

        if msg.is_multipart():

            for part in msg.walk():

                content_type = part.get_content_type()

                if content_type == "text/html":

                    html = part.get_payload(decode=True).decode(
                        errors="ignore"
                    )

                    print(html[:3000])
                    break

        else:

            print(
                msg.get_payload(decode=True).decode(
                    errors="ignore"
                )[:3000]
            )

        mail.logout()
        raise SystemExit
