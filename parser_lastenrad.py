import hashlib
import re


def _cancelled(subject):
    lowered = subject.lower()
    return any(word in lowered for word in ("cancel", "storn", "abgesagt"))


def _german_date(value):
    match = re.search(
        r"(\d{1,2})\.\s+([A-Za-zäöüÄÖÜ]+)\s+(\d{4})",
        value or "",
    )
    if not match:
        return None

    months = {
        "Januar": "01",
        "Februar": "02",
        "März": "03",
        "April": "04",
        "Mai": "05",
        "Juni": "06",
        "Juli": "07",
        "August": "08",
        "September": "09",
        "Oktober": "10",
        "November": "11",
        "Dezember": "12",
    }
    month = months.get(match.group(2))
    if not month:
        return None
    return f"{match.group(1).zfill(2)}.{month}.{match.group(3)}"


def parse_lastenrad(text, subject):
    result = {
        "source": "commonsbooking",
        "resource_type": "cargo_bike",
        "status": "cancelled" if _cancelled(subject) else "confirmed",
        "raw_subject": subject,
    }

    match = re.search(r"Buchung von (.+?) am Standort", subject)
    if match:
        result["item"] = match.group(1).strip()

    match = re.search(r"Abholung:\s*(.+)", text)
    if match:
        result["pickup_time"] = match.group(1).strip()
        booking_date = _german_date(result["pickup_time"])
        if booking_date:
            result["booking_date"] = booking_date

    match = re.search(r"Rückgabe:\s*(.+)", text)
    if match:
        result["return_time"] = match.group(1).strip()
        return_date = _german_date(result["return_time"])
        if return_date:
            result["return_date"] = return_date

    match = re.search(r"Standort\s*(.+?)(?:\n\s*\n|$)", text, re.DOTALL)
    if match:
        result["location"] = " ".join(match.group(1).split())

    identity = "|".join(
        [
            result.get("item", ""),
            result.get("pickup_time", ""),
            result.get("return_time", ""),
        ]
    )
    result["reservation_id"] = hashlib.sha256(identity.encode("utf-8")).hexdigest()

    return result
