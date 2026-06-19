import re


def parse_myturn_text(text, subject):

    result = {
        "status": "unknown"
    }

    # Status

    if "canceled" in subject.lower():
        result["status"] = "cancelled"
    else:
        result["status"] = "confirmed"

    # Reservierungsnummer

    m = re.search(
        r"Reservierung\s+#(\d+)",
        text
    )

    if m:
        result["reservation_id"] = m.group(1)

    # Datum

    m = re.search(
        r"Datum\s+(\d{2}\.\d{2}\.\d{4})",
        text
    )

    if m:
        result["booking_date"] = m.group(1)

    #Rueckgabe

    m = re.search(
        r"Fällig\s+(\d{2}\.\d{2}\.\d{4})",
        text
    )

    if m:
        result["return_date"] = m.group(1)

    # Hinweise

    m = re.search(
        r"Hinweise\s+(.*?)\s+Artikel",
        text,
        re.DOTALL
    )

    if m:
        result["notes"] = " ".join(
            m.group(1).split()
        )

        # Abholzeit

    m = re.search(
        r"Abholzeit\s+(\d{2}:\d{2}[–-]\d{2}:\d{2})",
        text
    )

    if m:
        result["pickup_time"] = (
            m.group(1)
            .replace("–", "-")
        )

    # Artikel

    m = re.search(
        r"Artikel\s+Anzahl\s+(.*?)\s+1\s+Gesamtzahl",
        text,
        re.DOTALL
    )

    if m:

        result["item"] = " ".join(
            m.group(1).split()
        )

        item = result["item"]

        room_match = re.match(
            r"(.+?)\s*\((\d{2}:\d{2})-(\d{2}:\d{2})\)",
            item
        )

        if room_match:

            result["resource_type"] = "room"

            result["room"] = room_match.group(1).strip()

            result["start_time"] = room_match.group(2)

            result["end_time"] = room_match.group(3)

        else:

            result["resource_type"] = "tool"

    return result
  
