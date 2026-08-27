import re
from datetime import datetime


def _normalize_date(value):
    for date_format in ("%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, date_format).strftime("%d.%m.%Y")
        except ValueError:
            pass
    raise ValueError(f"Nicht unterstütztes Datumsformat: {value}")


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

    match = re.search(r"(?:Reservierung|Reservation)\s+#(\d+)", text, re.IGNORECASE)
    if match:
        result["reservation_id"] = match.group(1)

    match = re.search(
        r"(?:Datum|Date)\s+(\d{2}[./]\d{2}[./]\d{4})",
        text,
        re.IGNORECASE,
    )
    if match:
        result["booking_date"] = _normalize_date(match.group(1))

    match = re.search(
        r"(?:Fällig|Due\s+Back)\s+(\d{2}[./]\d{2}[./]\d{4})",
        text,
        re.IGNORECASE,
    )
    if match:
        result["return_date"] = _normalize_date(match.group(1))

    match = re.search(
        r"(?:Hinweise|Notes)\s+(.*?)\s+(?:Artikel|Items?)\b",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        result["notes"] = " ".join(match.group(1).split())

    match = re.search(r"Abholzeit\s+(\d{2}:\d{2}[–-]\d{2}:\d{2})", text)
    if match:
        result["pickup_time"] = match.group(1).replace("–", "-")

    match = re.search(
        r"(?:Artikel\s+Anzahl|Item\s+Quantity)\s+"
        r"(.*?)\s+1\s+(?:Gesamtzahl|Total\s+Items)",
        text,
        re.DOTALL | re.IGNORECASE,
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
