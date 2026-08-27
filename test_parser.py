import unittest

from parser import parse_myturn_text


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
