import unittest

from parser import parse_myturn_text
from parser_lastenrad import parse_lastenrad


class MyTurnParserTests(unittest.TestCase):
    def test_parses_current_english_confirmation(self):
        text = """
        Reservation #903478
        Date 28/08/2026
        Duration 1 day
        Due Back 29/08/2026
        Total Items 1
        Notes Test
        Items
        Item Quantity
        HSS Bohrerkassette 1-9mm 19 Tlg. 1
        Total Items 1
        """

        result = parse_myturn_text(
            text,
            "Your reservation has been confirmed",
        )

        self.assertEqual(result["reservation_id"], "903478")
        self.assertEqual(result["booking_date"], "28.08.2026")
        self.assertEqual(result["return_date"], "29.08.2026")
        self.assertEqual(result["notes"], "Test")
        self.assertEqual(
            result["item"],
            "HSS Bohrerkassette 1-9mm 19 Tlg.",
        )
        self.assertEqual(result["resource_type"], "tool")
        self.assertEqual(result["status"], "confirmed")


class CommonsBookingParserTests(unittest.TestCase):
    def test_parses_single_day_cancellation_from_subject(self):
        result = parse_lastenrad(
            "Deine Buchung wurde storniert.",
            "Buchung storniert: Laszlo am Standort WERK. am 18. September 2026",
        )

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["item"], "Laszlo")
        self.assertEqual(result["booking_date"], "18.09.2026")
        self.assertEqual(result["return_date"], "18.09.2026")
        self.assertTrue(result["reservation_id"])

    def test_parses_multi_day_cancellation_from_subject(self):
        result = parse_lastenrad(
            "Deine Buchung wurde storniert.",
            "Buchung storniert: Laszlo am Standort WERK. "
            "von 23. September 2026 bis 27. September 2026",
        )

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["item"], "Laszlo")
        self.assertEqual(result["booking_date"], "23.09.2026")
        self.assertEqual(result["return_date"], "27.09.2026")

    def test_rejects_ambiguous_cancellation(self):
        with self.assertRaisesRegex(ValueError, "eindeutigen Buchungsdaten"):
            parse_lastenrad(
                "Deine Buchung wurde storniert.",
                "Buchung storniert",
            )

    def test_keeps_support_for_legacy_german_confirmation(self):
        text = """
        Reservierung #895803
        Datum 18.08.2026
        Fällig 25.08.2026
        Hinweise Test
        Artikel Anzahl
        Numatic NMD 1000 Tellerschleifmaschine 1
        Gesamtzahl 1
        """

        result = parse_myturn_text(text, "Reservierung bestätigt")

        self.assertEqual(result["reservation_id"], "895803")
        self.assertEqual(result["booking_date"], "18.08.2026")
        self.assertEqual(result["return_date"], "25.08.2026")
        self.assertEqual(
            result["item"],
            "Numatic NMD 1000 Tellerschleifmaschine",
        )
        self.assertEqual(result["resource_type"], "tool")


if __name__ == "__main__":
    unittest.main()
