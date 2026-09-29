import hashlib
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import quote, urljoin

import requests
from dotenv import load_dotenv


BERLIN = ZoneInfo("Europe/Berlin")
EVENT_ROLES = ("booking", "pickup", "return", "handover")
GERMAN_MONTHS = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "maerz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}


def _escape(value):
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _date(value):
    return datetime.strptime(value, "%d.%m.%Y").date()


def _time_range(value):
    match = re.search(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", value or "")
    if not match:
        return None
    return (
        datetime.strptime(match.group(1), "%H:%M").time(),
        datetime.strptime(match.group(2), "%H:%M").time(),
    )


def _german_datetime(value):
    match = re.search(
        r"(\d{1,2})\.\s+([A-Za-zÄÖÜäöüß]+)\s+(\d{4})"
        r"(?:\s+(\d{1,2}:\d{2}))?",
        value or "",
    )
    if not match:
        return None

    month = GERMAN_MONTHS.get(match.group(2).lower())
    if not month:
        return None

    clock = datetime.strptime(match.group(4) or "00:00", "%H:%M").time()
    return datetime.combine(
        date(int(match.group(3)), month, int(match.group(1))),
        clock,
        BERLIN,
    )


def event_uid(data, role="booking"):
    source = data.get("source", "myturn")
    reservation_id = data.get("reservation_id")
    if not reservation_id:
        raise ValueError("Reservierungs-ID fehlt")

    seed = f"{source}:{reservation_id}:{role}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()
    return f"zircula-booking-{digest}@zircula.org"


def event_filename(data, role="booking"):
    return hashlib.sha256(event_uid(data, role).encode("utf-8")).hexdigest() + ".ics"


def _schedule(data):
    booking_date = _date(data["booking_date"])
    resource_type = data.get("resource_type")

    if resource_type == "room":
        start = datetime.combine(
            booking_date,
            datetime.strptime(data["start_time"], "%H:%M").time(),
            BERLIN,
        )
        end = datetime.combine(
            booking_date,
            datetime.strptime(data["end_time"], "%H:%M").time(),
            BERLIN,
        )
        return "timed", start, end

    pickup = _time_range(data.get("pickup_time"))
    return_date = _date(data.get("return_date") or data["booking_date"])

    if pickup and return_date == booking_date:
        start = datetime.combine(booking_date, pickup[0], BERLIN)
        end = datetime.combine(booking_date, pickup[1], BERLIN)
        return "timed", start, end

    return "all_day", booking_date, return_date + timedelta(days=1)


def _event_schedule(event_date, time_value=None):
    time_range = _time_range(time_value)
    if not time_range:
        return "all_day", event_date, event_date + timedelta(days=1)

    start_time, end_time = time_range
    if (
        start_time == end_time
        or (
            start_time == datetime.strptime("00:00", "%H:%M").time()
            and end_time == datetime.strptime("23:59", "%H:%M").time()
        )
    ):
        return "all_day", event_date, event_date + timedelta(days=1)

    start = datetime.combine(event_date, start_time, BERLIN)
    end = datetime.combine(event_date, end_time, BERLIN)
    return "timed", start, end


def _summary(data, action=None):
    icons = {
        "room": "Raum",
        "tool": "Ausleihe",
        "cargo_bike": "Lastenrad",
    }
    label = icons.get(data.get("resource_type"), "Buchung")
    item = data.get("room") or data.get("item") or "Unbekannt"
    if action:
        return f"{action}: {item}"
    return f"{label}: {item}"


def _event_roles(data):
    if data.get("resource_type") == "room":
        return (("booking", None, None, None),)

    booking_date = _date(data["booking_date"])
    return_date = _date(data.get("return_date") or data["booking_date"])
    if booking_date == return_date:
        return (("handover", "Ausgabe & Rückgabe", booking_date, None),)

    return (
        ("pickup", "Ausgabe", booking_date, data.get("pickup_time")),
        ("return", "Rückgabe", return_date, data.get("return_time")),
    )


def build_ics(
    data,
    role="booking",
    action=None,
    event_date=None,
    event_time=None,
):
    if event_date is None:
        mode, start, end = _schedule(data)
    else:
        mode, start, end = _event_schedule(event_date, event_time)

    uid = event_uid(data, role)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    description = [
        f"Quelle: {data.get('source', 'myturn')}",
        f"Reservierung: {data.get('reservation_id')}",
    ]
    if data.get("notes"):
        description.append(f"Hinweise: {data['notes']}")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Zircula e.V.//Booking Importer//DE",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"SUMMARY:{_escape(_summary(data, action))}",
        f"DESCRIPTION:{_escape(chr(10).join(description))}",
        f"X-ZIRCULA-SOURCE:{_escape(data.get('source', 'myturn'))}",
        f"X-ZIRCULA-RESERVATION-ID:{_escape(data.get('reservation_id'))}",
    ]

    if mode == "all_day":
        lines.extend(
            [
                f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
            ]
        )
    else:
        lines.extend(
            [
                f"DTSTART:{start.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{end.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            ]
        )

    if data.get("location"):
        lines.append(f"LOCATION:{_escape(data['location'])}")

    lines.extend(["STATUS:CONFIRMED", "END:VEVENT", "END:VCALENDAR", ""])
    return "\r\n".join(lines)


def calendar_entries(data):
    return [
        (
            role,
            event_filename(data, role),
            build_ics(data, role, action, event_date, event_time),
        )
        for role, action, event_date, event_time in _event_roles(data)
    ]


def _calendar_start_date(calendar_data):
    match = re.search(
        r"(?:^|\r?\n)DTSTART(?:;[^:]*)?:(\d{8})(?:T(\d{6})Z)?(?:\r?\n|$)",
        calendar_data,
    )
    if not match:
        return None
    if not match.group(2):
        return datetime.strptime(match.group(1), "%Y%m%d").date()
    value = datetime.strptime(
        match.group(1) + match.group(2),
        "%Y%m%d%H%M%S",
    ).replace(tzinfo=timezone.utc)
    return value.astimezone(BERLIN).date()


def _calendar_property(calendar_data, name):
    match = re.search(
        rf"(?:^|\r?\n){re.escape(name)}(?:;[^:]*)?:(.*?)(?:\r?\n|$)",
        calendar_data,
    )
    return match.group(1) if match else None


class CalDAVCalendar:
    def __init__(self, calendar_url, username, password, timeout=30):
        self.calendar_url = calendar_url.rstrip("/") + "/"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (username, password)

    @classmethod
    def from_environment(cls):
        load_dotenv()
        required = {
            "CALDAV_CALENDAR_URL": os.getenv("CALDAV_CALENDAR_URL"),
            "CALDAV_USERNAME": os.getenv("CALDAV_USERNAME"),
            "CALDAV_APP_PASSWORD": os.getenv("CALDAV_APP_PASSWORD"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError("Fehlende Konfiguration: " + ", ".join(missing))
        return cls(
            required["CALDAV_CALENDAR_URL"],
            required["CALDAV_USERNAME"],
            required["CALDAV_APP_PASSWORD"],
        )

    def check(self):
        response = self.session.request(
            "PROPFIND",
            self.calendar_url,
            headers={"Depth": "0"},
            timeout=self.timeout,
        )
        if response.status_code != 207:
            raise RuntimeError(
                f"CalDAV-Kalender nicht erreichbar: HTTP {response.status_code}"
            )

    def _commonsbooking_cancellation_urls(self, data):
        item = data.get("item")
        booking_date = _date(data["booking_date"])
        return_date = _date(data.get("return_date") or data["booking_date"])
        if booking_date == return_date:
            expected = {
                (_escape(f"Ausgabe & Rückgabe: {item}"), booking_date),
            }
        else:
            expected = {
                (_escape(f"Ausgabe: {item}"), booking_date),
                (_escape(f"Rückgabe: {item}"), return_date),
            }

        start = datetime.combine(
            booking_date - timedelta(days=1),
            datetime.min.time(),
            timezone.utc,
        ).strftime("%Y%m%dT%H%M%SZ")
        end = datetime.combine(
            return_date + timedelta(days=2),
            datetime.min.time(),
            timezone.utc,
        ).strftime("%Y%m%dT%H%M%SZ")
        query = f"""<?xml version="1.0" encoding="UTF-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop><d:getetag/><c:calendar-data/></d:prop>
  <c:filter>
    <c:comp-filter name="VCALENDAR">
      <c:comp-filter name="VEVENT">
        <c:time-range start="{start}" end="{end}"/>
      </c:comp-filter>
    </c:comp-filter>
  </c:filter>
</c:calendar-query>"""
        response = self.session.request(
            "REPORT",
            self.calendar_url,
            data=query.encode("utf-8"),
            headers={"Content-Type": "application/xml; charset=utf-8", "Depth": "1"},
            timeout=self.timeout,
        )
        if response.status_code != 207:
            raise RuntimeError(
                "Kalender konnte nicht nach der stornierten Buchung durchsucht "
                f"werden: HTTP {response.status_code}"
            )

        matches = {entry: [] for entry in expected}
        root = ET.fromstring(response.content)
        for item_response in root.findall("{DAV:}response"):
            href_node = item_response.find("{DAV:}href")
            calendar_node = item_response.find(
                ".//{urn:ietf:params:xml:ns:caldav}calendar-data"
            )
            if href_node is None or calendar_node is None or not calendar_node.text:
                continue
            calendar_data = calendar_node.text
            if _calendar_property(calendar_data, "X-ZIRCULA-SOURCE") != "commonsbooking":
                continue
            key = (
                _calendar_property(calendar_data, "SUMMARY"),
                _calendar_start_date(calendar_data),
            )
            if key in matches:
                matches[key].append(
                    (
                        urljoin(self.calendar_url, href_node.text),
                        _calendar_property(
                            calendar_data,
                            "X-ZIRCULA-RESERVATION-ID",
                        ),
                    )
                )

        id_sets = [
            {reservation_id for _, reservation_id in candidates if reservation_id}
            for candidates in matches.values()
            if candidates
        ]
        common_ids = set.intersection(*id_sets) if id_sets else set()
        if len(common_ids) == 1:
            reservation_id = next(iter(common_ids))
            matches = {
                key: [
                    candidate
                    for candidate in candidates
                    if candidate[1] == reservation_id
                ]
                for key, candidates in matches.items()
            }

        ambiguous = [
            key
            for key, candidates in matches.items()
            if len(candidates) > 1
        ]
        if ambiguous:
            raise RuntimeError(
                "Stornierung ist nicht eindeutig; mehrere passende "
                "Kalendertermine gefunden"
            )
        return [
            candidates[0][0]
            for candidates in matches.values()
            if candidates
        ]

    def sync(self, data):
        if data.get("status") == "cancelled":
            deleted = 0
            for role in EVENT_ROLES:
                filename = event_filename(data, role)
                response = self.session.delete(
                    self.calendar_url + quote(filename),
                    timeout=self.timeout,
                )
                if response.status_code not in (200, 204, 404):
                    raise RuntimeError(
                        "Kalendertermin konnte nicht gelöscht werden: "
                        f"HTTP {response.status_code}"
                    )
                if response.status_code != 404:
                    deleted += 1
            if deleted == 0 and data.get("source") == "commonsbooking":
                for url in self._commonsbooking_cancellation_urls(data):
                    response = self.session.delete(url, timeout=self.timeout)
                    if response.status_code not in (200, 204, 404):
                        raise RuntimeError(
                            "Gefundener Kalendertermin konnte nicht gelöscht "
                            f"werden: HTTP {response.status_code}"
                        )
                    if response.status_code != 404:
                        deleted += 1
            return f"deleted:{deleted}"

        entries = calendar_entries(data)

        created = 0
        updated = 0
        active_roles = {role for role, _, _ in entries}
        for _, filename, payload in entries:
            response = self.session.put(
                self.calendar_url + quote(filename),
                data=payload.encode("utf-8"),
                headers={"Content-Type": "text/calendar; charset=utf-8"},
                timeout=self.timeout,
            )
            if response.status_code not in (200, 201, 204):
                raise RuntimeError(
                    "Kalendertermin konnte nicht gespeichert werden: "
                    f"HTTP {response.status_code}"
                )
            if response.status_code == 201:
                created += 1
            else:
                updated += 1

        for role in EVENT_ROLES:
            if role in active_roles:
                continue
            response = self.session.delete(
                self.calendar_url + quote(event_filename(data, role)),
                timeout=self.timeout,
            )
            if response.status_code not in (200, 204, 404):
                raise RuntimeError(
                    "Veralteter Kalendertermin konnte nicht gelöscht werden: "
                    f"HTTP {response.status_code}"
                )
        return f"created:{created},updated:{updated}"
