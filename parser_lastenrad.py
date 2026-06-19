import re
import hashlib

def parse_lastenrad(text, subject):

    result = {
        "source": "commonsbooking",
        "resource_type": "cargo_bike",
        "status": "confirmed",
        "raw_subject": subject
    }

    # Fahrradname aus dem Betreff

    m = re.search(
        r"Buchung von (.+?) am Standort",
        subject
    )

    if m:
        result["item"] = m.group(1).strip()

    # Abholung

    m = re.search(
        r"Abholung:\s*(.+)",
        text
    )

    if m:
        result["pickup_time"] = m.group(1).strip()

    # Datum für Slack-Filter extrahieren

    m = re.search(
        r"(\d{1,2})\.\s+([A-Za-zäöüÄÖÜ]+)\s+(\d{4})",
        result["pickup_time"]
    )

    if m:

        monate = {
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
            "Dezember": "12"
        }

        tag = m.group(1).zfill(2)
        monat = monate.get(m.group(2))
        jahr = m.group(3)

        if monat:
            result["booking_date"] = f"{tag}.{monat}.{jahr}"

    # Rückgabe

    m = re.search(
        r"Rückgabe:\s*(.+)",
        text
    )

    if m:
        result["return_time"] = m.group(1).strip()

        m2 = re.search(
            r"(\d{1,2})\.\s+([A-Za-zäöüÄÖÜ]+)\s+(\d{4})",
            result["return_time"]
        )

        if m2:

            monate = {
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
                "Dezember": "12"
            }

            tag = m2.group(1).zfill(2)
            monat = monate.get(m2.group(2))
            jahr = m2.group(3)

            if monat:
                result["return_date"] = f"{tag}.{monat}.{jahr}"

    # Standort

    m = re.search(
        r"Standort\s*(.+?)\n",
        text,
        re.DOTALL
    )

    if m:
        result["location"] = m.group(1).strip()

    result["reservation_id"] = hashlib.md5(
        subject.encode()
    ).hexdigest()

    return result
