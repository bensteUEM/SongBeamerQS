"""This module contains tests for most methods defined in SngFile.py."""

import logging
import unittest

from sng_utils import contains_songbook_prefix, generate_verse_marker_from_line


class TestSNGUtils(unittest.TestCase):
    """Test class for sng_utils - methods that don't rely on a SngFile class."""

    def __init__(self, *args: any, **kwargs: any) -> None:
        """Preparation of Test object.

        Params:
            args: passthrough arguments
            kwargs: passthrough named arguments
        """
        super().__init__(*args, **kwargs)

        logging.basicConfig(
            filename="logs/TestSNG.log",
            encoding="utf-8",
            format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
            level=logging.DEBUG,
        )
        logging.info("Excecuting TestSNG RUN")

    def test_helper_contains_songbook_prefix(self) -> None:
        """Test that runs various variations of songbook parts which should be detected by improved helper method."""
        # negative samples
        self.assertFalse(contains_songbook_prefix("gesegnet"))

        # positive samples
        self.assertTrue(contains_songbook_prefix("EG"))
        self.assertTrue(contains_songbook_prefix("EG999"))
        self.assertTrue(contains_songbook_prefix("EG999Psalm"))
        self.assertTrue(contains_songbook_prefix("EG999"))
        self.assertTrue(contains_songbook_prefix("EG999Psalm"))
        self.assertTrue(contains_songbook_prefix("EG999-Psalm"))
        self.assertTrue(contains_songbook_prefix("EG-999"))
        self.assertTrue(contains_songbook_prefix("999EG"))
        self.assertTrue(contains_songbook_prefix("999-EG"))

        self.assertTrue(contains_songbook_prefix("FJ"))
        self.assertTrue(contains_songbook_prefix("FJ999"))
        self.assertTrue(contains_songbook_prefix("FJ999Text"))
        self.assertTrue(contains_songbook_prefix("FJ999"))
        self.assertTrue(contains_songbook_prefix("FJ999Text"))
        self.assertTrue(contains_songbook_prefix("FJ999-Text"))
        self.assertTrue(contains_songbook_prefix("FJ-999"))
        self.assertTrue(contains_songbook_prefix("FJ5-999"))
        self.assertTrue(contains_songbook_prefix("FJ5/999"))
        self.assertTrue(contains_songbook_prefix("999/FJ5"))
        self.assertTrue(contains_songbook_prefix("999-FJ5"))
        self.assertTrue(contains_songbook_prefix("999.FJ5"))

    def test_generate_verse_marker_from_line(self) -> None:
        """Test sample lines that could be converted to verse labels."""
        samples = {
            "10. Test mehrstellige Strophe": (
                ["Verse", "10"],
                "Test mehrstellige Strophe",
            ),
            "Liedtext": (None, "Liedtext"),
            "Refrain 1: Text": (["Chorus", "1"], "Text"),
            "Chorus: Text": (["Chorus", ""], "Text"),
            "R: Text": (["Chorus", ""], "Text"),
            "C: Text": (["Chorus", ""], "Text"),
            "R1: Text": (["Chorus", "1"], "Text"),
            "R1 Text": (["Chorus", "1"], "Text"),
            "VERse 2 Text": (["Verse", "2"], "Text"),
            "Strophe 2 Text": (["Verse", "2"], "Text"),
            "Verse 3: Text": (["Verse", "3"], "Text"),
            "Strophe 10: Text": (["Verse", "10"], "Text"),
            "4. Text": (["Verse", "4"], "Text"),
            "V3: Text": (["Verse", "3"], "Text"),
            "B: Text": (["Bridge", ""], "Text"),
            "B1: Text": (["Bridge", "1"], "Text"),
            "Bridge 2: Text": (["Bridge", "2"], "Text"),
            "Bridge 3 Text": (["Bridge", "3"], "Text"),
        }

        for sample, expected_result in samples.items():
            result = generate_verse_marker_from_line(sample)
            self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
