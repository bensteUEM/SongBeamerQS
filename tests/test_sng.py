"""This module contains tests for most methods defined in SngFile.py."""

import json
import logging
import logging.config
import unittest
from pathlib import Path

from SngFile import SngFile

config_file = Path("logging_config.json")
with config_file.open(encoding="utf-8") as f_in:
    logging_config = json.load(f_in)
    log_directory = Path(logging_config["handlers"]["file"]["filename"]).parent
    if not log_directory.exists():
        log_directory.mkdir(parents=True)
    logging.config.dictConfig(config=logging_config)
logger = logging.getLogger(__name__)


class TestSNG(unittest.TestCase):
    """Test Class for SNG related class and methods.

    Anything but Parser
    """

    def __init__(self, *args: any, **kwargs: any) -> None:
        """Preparation of Test object.

        Params:
            args: passthrough arguments
            kwargs: passthrough named arguments
        """
        super().__init__(*args, **kwargs)

    def test_content_empty_block(self) -> None:
        """Test case with a SNG file that contains and empty block because it ends with ---."""
        test_dir = Path("./testData/Test")
        test_filename = "sample_churchsongid_caps.sng"
        song = SngFile(test_dir / test_filename, "EG")

        self.assertEqual(len(song.content), 1)
        self.assertEqual(len(song.content["Unknown"]), 3)

    def test_content(self) -> None:
        """Checks if all Markers from the Demo Set are detected.

        Test to check if a content without proper label is replaced as unknown and custom content header is read
        """
        # regular file with intro and named blocks
        test_dir = Path("./testData/Test")
        test_filename = "sample_languages.sng"
        song = SngFile(test_dir / test_filename)
        expected_versemarkers_set = {
            "Intro",
            "Verse 1",
            "Verse 2",
            "Verse 3",
            "Verse 4",
            "Verse 5",
        }
        test_versemarkers_set = set(song.content.keys())

        self.assertEqual(expected_versemarkers_set, test_versemarkers_set)

        # something with an auto detected "Unknown block" and custom block
        test_dir = Path("./testData/Test")
        test_filename = "sample_verseorder_blocks_missing.sng"
        song = SngFile(test_dir / test_filename)
        expected_versemarkers_set = {
            "Unknown",
            "$$M=Testnameblock",
            "Refrain 1",
            "Strophe 2",
            "Bridge",
        }
        test_versemarkers_set = set(song.content.keys())

        self.assertEqual(expected_versemarkers_set, test_versemarkers_set)

    def test_content_implicit_blocks(self) -> None:
        """Checks if all Markers from the Demo Set are detected.

        Test to check if a content without proper label is replaced as unknown and custom content header is read
        Checks that a file which does not have any section headers can be read without error.
        """
        test_dir = Path("./testData/EG Psalmen & Sonstiges")
        test_filename = "726 Psalm 047_utf8.sng"
        song = SngFile(test_dir / test_filename)

        self.assertEqual(list(song.content.keys()), ["Unknown"])
        self.assertEqual(len(song.content.keys()), 1)
        self.assertEqual(len(song.content["Unknown"]), 1 + 4)
        self.assertEqual(len(song.content["Unknown"][4]), 2)

    def test_content_reformat_slide_4_lines(self) -> None:
        """Tests specific test file to contain issues before fixing.

        * Fixes file with fix content slides of 4
        * Tests result to contain known blocks, keep Pre Chorus with 2 lines, ans split Chorus to more slides
        * Tests that no single slide has more than 4 lines
        """
        test_dir = Path("testData/EG Lieder")
        test_filename = "001 Macht Hoch die Tuer.sng"
        song = SngFile(test_dir / test_filename)

        sample_number_of_lines = 4

        self.assertFalse(
            all(
                len(block[1][1]) <= sample_number_of_lines
                for block in song.content.items()
            ),
            "No slides contain more than 4 lines before fixing",
        )

        self.assertEqual(
            len(song.content["Strophe 1"][1]), 4, "Strophe 1 first slide before fixing"
        )
        self.assertEqual(
            len(song.content["Strophe 2"][1]), 16, "Strophe 2 first slide before fixing"
        )
        self.assertEqual(
            len(song.content["Strophe 3"][1]), 1, "Strophe 3 first slide before fixing"
        )

        self.assertFalse(
            song.validate_content_slides_number_of_lines(
                fix=False, number_of_lines=sample_number_of_lines
            )
        )
        self.assertTrue(
            song.validate_content_slides_number_of_lines(
                fix=True, number_of_lines=sample_number_of_lines
            )
        )

        self.assertTrue(
            all(
                len(block[1][1]) <= sample_number_of_lines
                for block in song.content.items()
            ),
            f"Some slides contain more than {sample_number_of_lines} lines",
        )
        self.assertEqual(
            len(song.content["Strophe 1"][1]), 4, "Strophe 1 first slide after fixing"
        )
        self.assertEqual(
            len(song.content["Strophe 2"][1]), 4, "Strophe 2 first slide after fixing"
        )
        self.assertEqual(
            len(song.content["Strophe 3"][1]), 1, "Strophe 3 first slide after fixing"
        )

    def test_generate_verses_from_unknown(self) -> None:
        """Checks that the song is changed from Intro,Unknown,STOP to Intro,Verse .

        based on auto detecting 1.2.3. or other numerics or R: at beginning of block
        Also changes respective verse order
        """
        test_dir = Path("./testData/Test")
        test_filepath = "sample_no_versemarkers.sng"
        song = SngFile(test_dir / test_filepath, "test")
        self.assertEqual(
            ["Intro", "Unknown", "Verse 99", "STOP"], song.header["VerseOrder"]
        )
        song.generate_verses_from_unknown()

        expected_verse_markers = [
            "Intro",
            "Verse 1",
            "Verse 2",
            "Chorus",
            "Bridge 1",
            "Chorus 2",
            "Verse 10",
            "Verse 99",
            "STOP",
        ]
        self.assertEqual(
            expected_verse_markers,
            song.header["VerseOrder"],
        )

        existing_verse_markers = [
            " ".join(block[0]).strip() for block in song.content.values()
        ]
        self.assertEqual(
            set(expected_verse_markers) - {"STOP"}, set(existing_verse_markers)
        )

        # TODO (bensteUEM): optionally add test case for logged warning when new verse already exists in VerseOrder
        # https://github.com/bensteUEM/SongBeamerQS/issues/35

    def test_content_intro_slide(self) -> None:
        """Checks that sample file has no Intro in Verse Order or Blocks and repaired file contains both."""
        test_dir = Path("./testData/Test")
        test_filename = "sample.sng"
        song = SngFile(test_dir / test_filename)
        self.assertNotIn("Intro", song.header["VerseOrder"])
        self.assertNotIn("Intro", song.content.keys())
        song.fix_intro_slide()
        self.assertIn("Intro", song.header["VerseOrder"])
        self.assertIn("Intro", song.content.keys())

    def test_validate_verse_numbers(self) -> None:
        """Checks whether verse numbers are merged correctly.

        a, b parts are supposed to be merged into regular verse number
        """
        test_dir = Path("./testData/Test")
        test_filename = "sample_versemarkers_letter.sng"
        song = SngFile(test_dir / test_filename)
        self.assertIn("Refrain 1a", song.header["VerseOrder"])
        self.assertIn("Refrain 1b", song.header["VerseOrder"])

        self.assertFalse(song.validate_verse_numbers())
        self.assertIn("Refrain 1a", song.header["VerseOrder"])
        self.assertIn("Refrain 1b", song.header["VerseOrder"])

        self.assertTrue(song.validate_verse_numbers(fix=True))
        self.assertNotIn("Refrain 1a", song.header["VerseOrder"])
        self.assertNotIn("Refrain 1b", song.header["VerseOrder"])
        self.assertIn("Refrain 1", song.header["VerseOrder"])
        expected = [
            "Intro",
            "Strophe 1",
            "Strophe 2",
            "Refrain 1",
            "Bridge",
            "Strophe 3",
            "Strophe 4",
        ]
        self.assertEqual(expected, list(song.content.keys()))

    def test_validate_suspicious_encoding(self) -> None:
        """Test function which reads a file which was broken by opening a utf8 as iso8995-1 and saving it with wrong.

        Logs issues and tries to replace them
        """
        song = SngFile("./testData/ISO-UTF8/TestSongISOcharsUTF8.sng")
        result = song.validate_suspicious_encoding()
        self.assertFalse(result, "Should detect issues within the file")

        with self.assertLogs(level="DEBUG") as cm:
            result = song.validate_suspicious_encoding(fix=True)
            self.assertTrue(result, "Should have fixed issues within the file")
        info_template_prefix = "INFO:sng_utils:Found problematic encoding in str '"

        messages = [
            f"{info_template_prefix}Ã¤aaaÃ¤a'",
            "DEBUG:sng_utils:replaced Ã¤aaaÃ¤a by äaaaäa",
            f"{info_template_prefix}Ã¤'",
            "DEBUG:sng_utils:replaced Ã¤ by ä",
            f"{info_template_prefix}Ã¶'",
            "DEBUG:sng_utils:replaced Ã¶ by ö",
            f"{info_template_prefix}Ã¼'",
            "DEBUG:sng_utils:replaced Ã¼ by ü",
            f"{info_template_prefix}Ã\x84'",
            "DEBUG:sng_utils:replaced Ã\x84 by Ä",
            f"{info_template_prefix}Ã\x96'",
            "DEBUG:sng_utils:replaced Ã\x96 by Ö",
            f"{info_template_prefix}Ã\x9c'",
            "DEBUG:sng_utils:replaced Ã\x9c by Ü",
            f"{info_template_prefix}Ã\x9f'",
            "DEBUG:sng_utils:replaced Ã\x9f by ß",
        ]
        self.assertEqual(messages, cm.output)

    def test_validate_suspicious_encoding_2(self) -> None:
        """Test function which reads a file which is iso8995-1 but automatically parses correctly.

        This usually happens when automatic ChurchTools CCLI imports are read by Songbeamer without any modifications
        Logs issues and tries to replace them
        """
        song = SngFile("./testData/ISO-UTF8/TestSongISOchars.sng")
        result = song.validate_suspicious_encoding()
        self.assertTrue(
            result,
            "Should not detect issues within the file because of auto detected encoding",
        )

    def test_getset_id(self) -> None:
        """Test that runs various variations of songbook parts which should be detected by improved helper method."""
        path = "./testData/EG Lieder/"
        sample_filename = "001 Macht Hoch die Tuer.sng"
        sample_id = 762
        song = SngFile(path + sample_filename)

        self.assertEqual(song.get_id(), sample_id)
        song.set_id(-2)
        self.assertEqual(song.get_id(), -2)


if __name__ == "__main__":
    unittest.main()
