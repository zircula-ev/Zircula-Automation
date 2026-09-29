import unittest
from html import escape
from unittest.mock import Mock

from calendar_sync import (
    CalDAVCalendar,
    build_ics,
    calendar_entries,
    event_filename,
    event_uid,
)
from parser_lastenrad import parse_lastenrad


class CalendarSyncTest(unittest.TestCase):
    def test_room_event_is_stable_and_timed(self):
        booking = {
            "source": "myturn",
            "reservation_id": "846828",
            "status": "confirmed",
            "booking_date": "19.06.2026",
            "resource_type": "room",
            "room": "Besprechungsraum",
            "start_time": "09:30",
            "end_time": "15:00",
        }

        self.assertEqual(event_uid(booking), event_uid(dict(booking)))
        self.assertEqual(event_filename(booking), event_filename(dict(booking)))

        calendar = build_ics(booking)
        self.assertIn("SUMMARY:Raum: Besprechungsraum", calendar)
        self.assertIn("DTSTART:20260619T073000Z", calendar)
        self.assertIn("DTEND:20260619T130000Z", calendar)

    def test_tool_booking_creates_pickup_and_return_only(self):
        booking = {
            "source": "myturn",
            "reservation_id": "123",
            "status": "confirmed",
            "booking_date": "19.06.2026",
            "return_date": "20.06.2026",
            "resource_type": "tool",
            "item": "Akkuschrauber",
        }

        entries = calendar_entries(booking)

        self.assertEqual([entry[0] for entry in entries], ["pickup", "return"])
        self.assertIn("SUMMARY:Ausgabe: Akkuschrauber", entries[0][2])
        self.assertIn("DTSTART;VALUE=DATE:20260619", entries[0][2])
        self.assertIn("DTEND;VALUE=DATE:20260620", entries[0][2])
        self.assertIn("SUMMARY:Rückgabe: Akkuschrauber", entries[1][2])
        self.assertIn("DTSTART;VALUE=DATE:20260620", entries[1][2])
        self.assertIn("DTEND;VALUE=DATE:20260621", entries[1][2])

    def test_commonsbooking_preserves_selected_handover_times(self):
        booking = {
            "source": "commonsbooking",
            "status": "confirmed",
            "reservation_id": "timed-lale-id",
            "resource_type": "cargo_bike",
            "item": "Carla Cargo Schwarz",
            "booking_date": "28.08.2026",
            "return_date": "29.08.2026",
            "pickup_time": "28. August 2026 11:00 - 12:00",
            "return_time": "29. August 2026 15:00 - 16:00",
        }

        entries = calendar_entries(booking)

        self.assertEqual(len(entries), 2)
        self.assertIn("DTSTART:20260828T090000Z", entries[0][2])
        self.assertIn("DTEND:20260828T100000Z", entries[0][2])
        self.assertIn("DTSTART:20260829T130000Z", entries[1][2])
        self.assertIn("DTEND:20260829T140000Z", entries[1][2])
        self.assertNotIn("VALUE=DATE", "".join(entry[2] for entry in entries))

    def test_commonsbooking_id_survives_cancellation_subject(self):
        text = """
        Abholung: 19. Juni 2026 0:00 - 23:59
        Rückgabe: 20. Juni 2026 0:00 - 0:00
        Standort
        WERK.
        """
        confirmed = parse_lastenrad(
            text,
            "Deine Buchung von Siebträger Tandem am Standort WERK.",
        )
        cancelled = parse_lastenrad(
            text,
            "Stornierung deiner Buchung von Siebträger Tandem am Standort WERK.",
        )

        self.assertEqual(confirmed["reservation_id"], cancelled["reservation_id"])
        self.assertEqual(cancelled["status"], "cancelled")

    def test_commonsbooking_creates_no_events_between_handover_dates(self):
        booking = {
            "source": "commonsbooking",
            "status": "confirmed",
            "reservation_id": "stable-lale-id",
            "resource_type": "cargo_bike",
            "item": "Carla Cargo Schwarz",
            "booking_date": "22.08.2026",
            "return_date": "23.08.2026",
            "pickup_time": "22. August 2026 0:00 - 23:59",
            "return_time": "23. August 2026 0:00 - 0:00",
        }

        entries = calendar_entries(booking)

        self.assertEqual(len(entries), 2)
        self.assertIn("SUMMARY:Ausgabe: Carla Cargo Schwarz", entries[0][2])
        self.assertIn("DTSTART;VALUE=DATE:20260822", entries[0][2])
        self.assertIn("SUMMARY:Rückgabe: Carla Cargo Schwarz", entries[1][2])
        self.assertIn("DTSTART;VALUE=DATE:20260823", entries[1][2])
        self.assertNotIn("DTSTART;VALUE=DATE:20260824", "".join(e[2] for e in entries))

    def test_same_day_loan_creates_one_combined_event(self):
        booking = {
            "source": "myturn",
            "status": "confirmed",
            "reservation_id": "same-day",
            "resource_type": "tool",
            "item": "Beamer",
            "booking_date": "22.08.2026",
            "return_date": "22.08.2026",
        }

        entries = calendar_entries(booking)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][0], "handover")
        self.assertIn("SUMMARY:Ausgabe & Rückgabe: Beamer", entries[0][2])

    def test_cancellation_finds_legacy_events_by_item_and_dates(self):
        original = {
            "source": "commonsbooking",
            "status": "confirmed",
            "reservation_id": "legacy-time-based-id",
            "resource_type": "cargo_bike",
            "item": "Laszlo",
            "booking_date": "23.09.2026",
            "return_date": "27.09.2026",
            "pickup_time": "23. September 2026 11:00 - 12:00",
            "return_time": "27. September 2026 15:00 - 16:00",
        }
        entries = calendar_entries(original)
        responses = []
        for _, filename, calendar_data in entries:
            responses.append(
                "<d:response>"
                f"<d:href>/calendars/test/{filename}</d:href>"
                "<d:propstat><d:prop>"
                f"<c:calendar-data>{escape(calendar_data)}</c:calendar-data>"
                "</d:prop></d:propstat>"
                "</d:response>"
            )
        report = Mock(
            status_code=207,
            content=(
                '<d:multistatus xmlns:d="DAV:" '
                'xmlns:c="urn:ietf:params:xml:ns:caldav">'
                + "".join(responses)
                + "</d:multistatus>"
            ).encode("utf-8"),
        )
        not_found = Mock(status_code=404)
        deleted = Mock(status_code=204)
        calendar = CalDAVCalendar(
            "https://cloud.example.test/calendars/test/",
            "user",
            "password",
        )
        calendar.session.request = Mock(return_value=report)
        calendar.session.delete = Mock(
            side_effect=[not_found, not_found, not_found, not_found, deleted, deleted]
        )
        cancellation = parse_lastenrad(
            "Deine Buchung wurde storniert.",
            "Buchung storniert: Laszlo am Standort WERK. "
            "von 23. September 2026 bis 27. September 2026",
        )

        result = calendar.sync(cancellation)

        self.assertEqual(result, "deleted:2")
        calendar.session.request.assert_called_once()
        self.assertEqual(calendar.session.delete.call_count, 6)


if __name__ == "__main__":
    unittest.main()
