import unittest

from calendar_sync import build_ics, event_filename, event_uid
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

    def test_tool_booking_spans_inclusive_dates(self):
        booking = {
            "source": "myturn",
            "reservation_id": "123",
            "status": "confirmed",
            "booking_date": "19.06.2026",
            "return_date": "20.06.2026",
            "resource_type": "tool",
            "item": "Akkuschrauber",
        }

        calendar = build_ics(booking)
        self.assertIn("DTSTART;VALUE=DATE:20260619", calendar)
        self.assertIn("DTEND;VALUE=DATE:20260621", calendar)

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


if __name__ == "__main__":
    unittest.main()
