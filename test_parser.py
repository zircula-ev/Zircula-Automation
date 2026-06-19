from parser import parse_myturn_text

with open("mail.txt") as f:
    text = f.read()

subject = "Reservation request canceled - Timo Hecken"

print(
    parse_myturn_text(
        text,
        subject
    )
)
