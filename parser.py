import re


def parse_myturn_text(text, subject):
    lowered = subject.lower()
    result = {
        "source": "myturn",
        "status": (
            "cancelled"
            if any(word in lowered for word in ("cancel", "storn", "abgesagt"))
            else "confirmed"
        ),
    }

    match = re.search(r"Reservierung\s+#(\d+)", text)
    if match:
        result["reservation_id"] = match.group(1)

    match = re.search(r"Datum\s+(\d{2}\.\d{2}\.\d{4})", text)
    if match:
        result["booking_date"] = match.group(1)

    match = re.search(r"Fällig\s+(\d{2}\.\d{2}\.\d{4})", text)
    if match:
        result["return_date"] = match.group(1)

    match = re.search(r"Hinweise\s+(.*?)\s+Artikel", text, re.DOTALL)
    if match:
        result["notes"] = " ".join(match.group(1).split())

    match = re.search(r"Abholzeit\s+(\d{2}:\d{2}[–-]\d{2}:\d{2})", text)
    if match:
        result["pickup_time"] = match.group(1).replace("–", "-")

    match = re.search(
        r"Artikel\s+Anzahl\s+(.*?)\s+1\s+Gesamtzahl",
        text,
        re.DOTALL,
    )
    if match:
        result["item"] = " ".join(match.group(1).split())
        room_match = re.match(
            r"(.+?)\s*\((\d{2}:\d{2})-(\d{2}:\d{2})\)",
            result["item"],
        )

        if room_match:
            result["resource_type"] = "room"
            result["room"] = room_match.group(1).strip()
            result["start_time"] = room_match.group(2)
            result["end_time"] = room_match.group(3)
        else:
            result["resource_type"] = "tool"

    return result
