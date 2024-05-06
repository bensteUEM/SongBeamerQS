"""This module contains tests for most methods defined in SngFile.py."""

import logging
import re
import unittest
from pathlib import Path
from shutil import copyfile

from SngFile import SngFile


class TestSNGHeaderValidation(unittest.TestCase):
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

        logging.basicConfig(
            filename="logs/TestSNG.log",
            encoding="utf-8",
            format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
            level=logging.DEBUG,
        )
        logging.info("Excecuting TestSNG RUN")

    def test_header_title_fix(self) -> None:
        """Checks that header title is fixed for one sample file."""
        test_data_dir = Path("testData/Test")
        sample_filename = "sample_missing_headers.sng"
        copyfile(
            test_data_dir / sample_filename,
            test_data_dir / (sample_filename + "_bak"),
        )

        song = SngFile(test_data_dir / sample_filename, "Test")
        self.assertNotIn("Title", song.header)
        song.validate_header_title(fix=False)
        self.assertNotIn("Title", song.header)
        song.validate_header_title(fix=True)
        self.assertEqual(sample_filename[:-4], song.header["Title"])

        # cleanup
        Path(test_data_dir / (sample_filename + "_bak")).rename(
            test_data_dir / sample_filename
        )

    def test_header_title_valid_no_change(self) -> None:
        """Checks that header title is not fixed for sample file which is psalm with valid title."""
        test_data_dir = Path("testData/EG Psalmen & Sonstiges")
        sample_filename = "709 Herr, sei nicht ferne.sng"

        song = SngFile(test_data_dir / sample_filename)
        self.assertIn("Title", song.header)
        self.assertEqual(sample_filename[4:-4], song.header["Title"])
        song.validate_header_title(fix=True)
        self.assertEqual(sample_filename[4:-4], song.header["Title"])

    def test_header_title_special2(self) -> None:
        """Checks that header title is not fixed.

        for sample file which had issues in log which had issues on log.
        """
        # 2022-06-03 10:56:20,370 root       DEBUG    Fixed title to (Psalm NGÜ) in Psalm 23 NGÜ.sng
        # -> Number should not be ignored if no SongPrefix
        song = SngFile(
            "./testData//Wwdlp (Wo wir dich loben, wachsen neue Lieder plus)/909.1 Psalm 85 I.sng"
        )
        self.assertIn("Title", song.header)
        self.assertEqual("Psalm 85 I", song.header["Title"])
        song.validate_header_title(fix=True)
        self.assertEqual("Psalm 85 I", song.header["Title"])

        # 2022-06-03 10:56:20,370 root       DEBUG    Song without a Title in Header:Gesegneten Sonntag.sng
        # 2022-06-03 10:56:20,370 root       DEBUG    Fixed title to (Sonntag) in Gesegneten Sonntag.sng
        # Fixed by correcting contains_songbook_prefix() method
        song = SngFile("./testData/Herzlich Willkommen.sng")
        self.assertNotIn("Title", song.header)
        song.validate_header_title(fix=True)
        self.assertEqual("Herzlich Willkommen", song.header["Title"])

    def test_header_title_special3(self) -> None:
        """Test a special cases of title which contains a number and or of songbook prefix."""
        titles = ["EG 241 Test", "EG Lied", "245 Test"]
        for title in titles:
            test_song = SngFile(
                "./testData/EG Lieder/001 Macht Hoch die Tuer.sng", songbook_prefix="EG"
            )
            test_song.header["Title"] = title
            self.assertFalse(test_song.validate_header_title(fix=False))

    def test_header_title_special4(self) -> None:
        """Test validate_header_title with WWDLP Psalm.

        as indicated in https://github.com/bensteUEM/SongBeamerQS/issues/23
        """
        test_song = SngFile(
            "./testData/Wwdlp (Wo wir dich loben, wachsen neue Lieder plus)/909.1 Psalm 85 I.sng",
            songbook_prefix="WWDLP",
        )
        self.assertEqual(test_song.header["Title"], "Psalm 85 I")

        result = test_song.validate_header_title(fix=False)
        self.assertTrue(result, "title should be valid")

    def test_is_psalm(self) -> None:
        """Checks for some files if they are psalms."""
        test_song = SngFile(
            "./testData/Wwdlp (Wo wir dich loben, wachsen neue Lieder plus)/909.1 Psalm 85 I.sng",
            songbook_prefix="WWDLP",
        )
        self.assertTrue(test_song.is_psalm())

        test_song = SngFile(
            "./testData/EG Psalmen & Sonstiges/709 Herr, sei nicht ferne.sng",
            songbook_prefix="EG",
        )
        self.assertTrue(test_song.is_psalm())

        test_song = SngFile(
            "./testData/EG Lieder/001 Macht Hoch die Tuer.sng",
            songbook_prefix="EG",
        )
        self.assertFalse(test_song.is_psalm())

        test_song = SngFile(
            "./testData/Test/sample_no_ct.sng",
            songbook_prefix="",
        )
        self.assertFalse(test_song.is_psalm())

    def test_header_all(self) -> None:
        """Checks if all params of the test file are correctly parsed.

        Because of datatype Verse Order is checked first
        Rest of headers are compared to dict
        """
        test_dir = Path("./testData/EG Lieder")
        test_file_name = "001 Macht Hoch die Tuer.sng"
        song = SngFile(test_dir / test_file_name)

        expected_verse_order = (
            "Intro,Strophe 1,Strophe 2,Strophe 3,Strophe 4,Strophe 5,STOP"
        ).split(",")
        self.assertEqual(song.header["VerseOrder"], expected_verse_order)

        song.header.pop("VerseOrder")
        expected_header = {
            "LangCount": "1",
            "Title": "Macht Hoch die Tür",
            "Author": "Georg Weissel (1623) 1642",
            "Melody": "Halle 1704",
            "Editor": "SongBeamer 5.17a",
            "CCLI": "5588206",
            "(c)": "Public Domain",
            "Version": "3",
            "BackgroundImage": r"Menschen\himmel-und-erde.jpg",
            "Songbook": "EG 2",
            # "ChurchSongID": "", # not part of sample file
            "id": "762",
            "Comments": "77u/Rm9saWVucmVpaGVuZm9sZ2UgbmFjaCBvZmZpemllbGxlciBBdWZuYWhtZSwgaW4gQmFpZXJzYnJvb"
            "m4gZ2dmLiBrw7xyemVyIHVuZCBtaXQgTXVzaWt0ZWFtIGFienVzdGltbWVu",
            "Categories": "Advent",  # usually ignored but present in sample
        }
        self.assertDictEqual(song.header, expected_header)

    def test_header_space(self) -> None:
        """Test that checks that header spaces at beginning and end are omitted while others still exists and might invalidate headers params."""
        test_dir = Path("./testData/Test")
        test_file_name = "sample_missing_headers.sng"
        song = SngFile(test_dir / test_file_name)

        self.assertIn("LangCount", song.header)
        self.assertEqual("1", song.header["LangCount"])
        self.assertIn("VerseOrder", song.header)
        self.assertIn("Author", song.header)
        self.assertNotIn("CCLI", song.header)

    def test_header_complete(self) -> None:
        """Checks that all required headers are available for the song.

        using 3 samples
        * with missing title
        * complete set
        * file with translation
        * Psalm with missing headers logged

        Info should be logged in case of missing headers
        """
        test_dir = Path("./testData/Test")
        test_file_name = "sample_missing_headers.sng"
        song = SngFile(test_dir / test_file_name)
        with self.assertLogs(level="WARNING") as cm:
            song.validate_headers()
        self.assertEqual(
            cm.output,
            [
                f"WARNING:root:Missing required headers in ({test_file_name}) ['Title', 'CCLI']"
            ],
        )

        test_dir = Path("./testData/Test")
        test_file_name = "sample.sng"
        song = SngFile(test_dir / test_file_name)
        check = song.validate_headers()
        self.assertTrue(
            check, song.filename + " should contain other headers - check log"
        )

        test_dir = Path("./testData/Test")
        test_file_name = "sample_languages.sng"
        song = SngFile(test_dir / test_file_name)
        song.fix_songbook_from_filename()
        check = song.validate_headers()
        self.assertTrue(
            check, song.filename + " should contain other headers - check log"
        )

        test_dir = Path("./testData/EG Psalmen & Sonstiges")
        test_file_name = "709 Herr, sei nicht ferne.sng"
        song = SngFile(test_dir / test_file_name, "EG")
        with self.assertLogs(level="WARNING") as cm:
            song.validate_headers()
        self.assertEqual(
            cm.output,
            [
                f"WARNING:root:Missing required headers in ({test_file_name}) "
                "['Author', 'Melody', 'CCLI', 'Translation']"
            ],
        )

    def test_header_illegal_removed(self) -> None:
        """Tests that all illegal headers are removed."""
        song = SngFile(
            "./testData/EG Psalmen & Sonstiges/709 Herr, sei nicht ferne.sng", "EG"
        )
        self.assertIn("FontSize", song.header.keys())
        song.validate_headers_illegal_removed(fix=False)
        self.assertIn("FontSize", song.header.keys())
        song.validate_headers_illegal_removed(fix=True)
        self.assertNotIn("FontSize", song.header.keys())

    def test_header_songbook(self) -> None:
        """Checks that sng prefix is correctly used when reparing songbook prefix.

        1. test prefix
        2. EG prefix with special number xxx.x
        3. no prefix
        4. testprefix without number should trigger warning
        5. not correcting ' '  songbook
        """
        # 1. test prefix
        test_dir = Path("./testData/EG Lieder")
        test_filename = "001 Macht Hoch die Tuer.sng"
        song = SngFile(test_dir / test_filename, songbook_prefix="test")
        song.fix_songbook_from_filename()
        self.assertEqual("test 001", song.header.get("Songbook", None))
        self.assertEqual("test 001", song.header.get("ChurchSongID", None))

        # 2. EG prefix
        test_dir = Path("./testData/EG Psalmen & Sonstiges")
        test_filename = "571.1 Ubi caritas et amor - Wo die Liebe wohnt.sng"
        song = SngFile(
            test_dir / test_filename,
            songbook_prefix="EG",
        )
        song.fix_songbook_from_filename()
        self.assertEqual("EG 571.1", song.header.get("Songbook", None))

        # no prefix
        test_dir = Path("./testData/Test/")
        test_filename = "sample_missing_headers.sng"
        song = SngFile(test_dir / test_filename)
        song.fix_songbook_from_filename()
        self.assertEqual(" ", song.header["Songbook"])

        # 4. test prefix
        with self.assertLogs(level="WARNING") as cm:
            song = SngFile(f"./testData/Test/{test_filename}", "test")
            song.fix_songbook_from_filename()
        self.assertEqual(
            cm.output,
            [
                f"WARNING:root:Missing required digits as first block in filename {test_filename} - can't fix songbook"
            ],
        )

        # 5. ' ' songbook not corrected
        with self.assertLogs(level=logging.DEBUG) as cm:
            test_dir = Path("./testData/Test")
            test_filename = "sample.sng"
            song = SngFile(test_dir / test_filename)
            self.assertEqual(" ", song.header["Songbook"])
            song.fix_songbook_from_filename()
            self.assertEqual(" ", song.header["Songbook"])
        self.assertEqual(
            cm.output,
            [
                f"DEBUG:root:testData/Test/{test_filename} is detected as utf-8 because of BOM",
                "DEBUG:root:Parsing content for: sample.sng",
            ],
        )

    def test_header_songbook_special(self) -> None:
        """Test checking special cases discovered in logging while programming."""
        # The file should already have correct ChurchSongID but did raise an error on logging
        song = SngFile(
            "./testData/EG Psalmen & Sonstiges/709 Herr, sei nicht ferne.sng", "EG"
        )
        self.assertEqual("EG 709 - Psalm 22 I", song.header["ChurchSongID"])
        self.assertEqual("EG 709 - Psalm 22 I", song.header["Songbook"])

        with self.assertNoLogs(level="WARNING"):
            song.validate_header_songbook(fix=False)
            song.validate_header_songbook(fix=True)

        self.assertEqual("EG 709 - Psalm 22 I", song.header["ChurchSongID"])
        self.assertEqual("EG 709 - Psalm 22 I", song.header["Songbook"])

    def test_header_church_song_id_caps(self) -> None:
        """Test that checks for incorrect capitalization in ChurchSongID and it's autocorrect.

        Corrected Songbook 085 O Haupt voll Blut und Wunden.sng - used "ChurchSongId instead of ChurchSongID"
        """
        test_dir = Path("./testData/Test")
        test_filename = "sample_churchsongid_caps.sng"
        song = SngFile(test_dir / test_filename, "EG")

        self.assertNotIn("ChurchSongID", song.header.keys())
        song.fix_header_church_song_id_caps()
        self.assertNotIn("ChurchSongId", song.header.keys())
        self.assertEqual(song.header["ChurchSongID"], "EG 000")

    def test_validate_header_background(self) -> None:
        """Test case for background images both with and without fix.

        1. regular with picture
        2. regular without picture
        3. Psalm with no picture
        4. Psalm with wrong picture
        5. Psalm with correct picture
        """
        # Case 1. regular with picture
        test_dir = Path("./testData/Test")
        test_filename = "sample.sng"
        song = SngFile(test_dir / test_filename, "test")

        self.assertTrue(song.validate_header_background(fix=False))

        song = SngFile(test_dir / test_filename, "test")
        self.assertTrue(song.validate_header_background(fix=True))

        # Case 2. regular without picture
        test_dir = Path("./testData/Test")
        test_filename = "sample_languages.sng"
        song = SngFile(test_dir / test_filename, "test")

        with self.assertLogs(level="DEBUG") as cm:
            self.assertFalse(song.validate_header_background(fix=False))
        self.assertEqual(cm.output, [f"DEBUG:root:No Background in ({test_filename})"])

        song = SngFile(test_dir / test_filename, "test")
        with self.assertLogs(level="WARN") as cm:
            self.assertFalse(song.validate_header_background(fix=True))
        self.assertEqual(
            cm.output,
            [f"WARNING:root:Can't fix background for ({test_filename})"],
        )

        # Case 3. Psalm with no picture
        test_dir = Path("./testData/EG Psalmen & Sonstiges")
        test_filename = "752 psalm_background_no.sng"
        song = SngFile(test_dir / test_filename, "EG")

        with self.assertLogs(level="DEBUG") as cm:
            self.assertFalse(song.validate_header_background(fix=False))
        self.assertEqual(cm.output, [f"DEBUG:root:No Background in ({test_filename})"])

        song = SngFile(test_dir / test_filename, "EG")
        with self.assertLogs(level="DEBUG") as cm:
            self.assertTrue(song.validate_header_background(fix=True))
        self.assertEqual(
            cm.output, [f"DEBUG:root:Fixing background for Psalm in ({test_filename})"]
        )

        # Case 4. Psalm with wrong picture
        test_dir = Path("./testData/EG Psalmen & Sonstiges")
        test_filename = "709 Herr, sei nicht ferne.sng"
        song = SngFile(test_dir / test_filename, "EG")

        with self.assertLogs(level="DEBUG") as cm:
            self.assertFalse(song.validate_header_background(fix=False))
        self.assertEqual(
            cm.output,
            [
                f"DEBUG:root:Incorrect background for Psalm in ({test_filename}) not fixed"
            ],
        )

        song = SngFile(test_dir / test_filename, "EG")
        with self.assertLogs(level="DEBUG") as cm:
            self.assertTrue(song.validate_header_background(fix=True))
        self.assertEqual(
            cm.output, [f"DEBUG:root:Fixing background for Psalm in ({test_filename})"]
        )

        # Case 5. Psalm with correct picture
        test_dir = Path("./testData/EG Psalmen & Sonstiges")
        test_filename = "753 psalm_background_correct.sng"
        song = SngFile(test_dir / test_filename, "EG")

        with self.assertNoLogs(level="DEBUG"):
            self.assertTrue(song.validate_header_background(fix=False))

        song = SngFile(test_dir / test_filename, "EG")
        with self.assertNoLogs(level="DEBUG"):
            self.assertTrue(song.validate_header_background(fix=True))

    def test_header_songbook_eg_psalm_special(self) -> None:
        """Test for debugging special Psalms which might not follow ChurchSongID conventions.

        e.g. 709 Herr, sei nicht ferne.sng
        """
        song = SngFile(
            "./testData/EG Psalmen & Sonstiges/709 Herr, sei nicht ferne.sng", "EG"
        )
        self.assertEqual(song.header["Songbook"], "EG 709 - Psalm 22 I")

        songbook_regex = r"^(Wwdlp \d{3})|(FJ([1-5])\/\d{3})|(EG \d{3}(.\d{1,2})?(( - Psalm )\d{1,3})?( .{1,3})?)$"
        self.assertTrue(re.fullmatch(songbook_regex, song.header["Songbook"]))

    def test_header_eg_psalm_quality_checks(self) -> None:
        """Test that checks for auto warning on correction of Psalms in EG."""
        # Test Warning for Psalms
        test_dir = Path("testData/EG Psalmen & Sonstiges")
        test_filename = "726 Psalm 047_utf8.sng"
        song = SngFile(test_dir / test_filename, "EG")
        self.assertNotIn("ChurchSongID", song.header.keys())
        with self.assertLogs(level=logging.INFO) as cm:
            song.fix_songbook_from_filename()

        self.assertEqual(
            cm.output,
            [
                f'INFO:root:Psalm "{test_filename}"'
                " can not be auto corrected - please adjust manually ( , )"
            ],
        )

        # TODO (bensteUEM): Add test for language marker validation in EG psalms
        # https://github.com/bensteUEM/SongBeamerQS/issues/36

        # Test background image validation for EG Psalms
        self.assertFalse(song.validate_header_background(fix=False))
        self.assertTrue(song.validate_header_background(fix=True))
        self.assertNotEqual(
            song.header["BackgroundImage"], "Israel\\Jerusalem Skyline Photo.bmp"
        )

    def test_header_verse_order_complete(self) -> None:
        """Method that checks various cases in regards to VerseOrder existance and fixing."""
        test_dir = Path("testData/Test")
        test_filename = "sample_verseorder_blocks_missing.sng"
        song = SngFile(test_dir / test_filename)

        sample_verse_order = (
            "Intro,Strophe 1,Strophe 2,Refrain 1,Refrain 1,Strophe 2,Refrain 1,Refrain 1,Bridge,"
            "Bridge,Intro,Refrain 1,Refrain 1,STOP"
        ).split(",")
        sample_blocks = "Unknown,$$M=Testnameblock,Refrain 1,Strophe 2,Bridge".split(
            ","
        )
        expected_verse_order = (
            "Strophe 2,Refrain 1,Refrain 1,Strophe 2,Refrain 1,Refrain 1,"
            "Bridge,Bridge,Refrain 1,Refrain 1,"
            "STOP,Unknown,Testnameblock"
        ).split(",")

        # 1. Check initial test file state
        self.assertEqual(song.header["VerseOrder"], sample_verse_order)
        self.assertEqual(list(song.content.keys()), sample_blocks)

        # 2. Check that Verse Order shows as incomplete
        with self.assertLogs(level="WARNING") as cm:
            self.assertFalse(song.validate_verse_order_coverage())

        self.assertEqual(
            cm.output,
            [
                f"WARNING:root:Verse Order and Blocks don't match in {test_filename}",
            ],
        )

        # 3. Check that Verse Order is completed
        song = SngFile(test_dir / test_filename)
        self.assertEqual(song.header["VerseOrder"], sample_verse_order)
        with self.assertNoLogs(level="WARNING"):
            song.validate_verse_order_coverage(fix=True)

        self.assertEqual(song.header["VerseOrder"], expected_verse_order)

    def test_header_verse_order_special3(self) -> None:
        """Special Case welcome slide with custom verse headers."""
        song = SngFile("./testData/Herzlich Willkommen.sng", "EG")
        self.assertEqual(
            ["Intro", "Variante 1", "Variante 2", "Intro", "STOP"],
            song.header["VerseOrder"],
        )
        song.validate_verse_order_coverage(fix=True)
        self.assertEqual(
            ["Intro", "Variante 1", "Variante 2", "Intro", "STOP"],
            song.header["VerseOrder"],
        )

    def test_header_validate_verse_numbers_merge(self) -> None:
        """Special case check 1b is 2nd part of verse 1."""
        test_dir = Path("./testData/Test")
        test_filename = "sample_versemarkers_letter.sng"
        song = SngFile(test_dir / test_filename)
        self.assertEqual(song.content["Strophe 1b"][1][0], "text 1b")
        song.validate_verse_numbers(fix=True)
        self.assertEqual(song.content["Strophe 1"][2][0], "text 1b")

    def test_content_stop_verse_order(self) -> None:
        """Checks and corrects existance of STOP in Verse Order.

        1. File does not have STOP
        2. File does already have STOP
        3. File does have STOP but not at end and should stay this way
        4. File does have STOP but not at end and should not stay this way
        """
        # 1. File does not have STOP
        test_dir = Path("./testData/Test")
        test_filename = "sample_header_only.sng"
        song = SngFile(test_dir / test_filename)
        self.assertNotIn("STOP", song.header["VerseOrder"])
        self.assertTrue(song.validate_header_stop_verseorder(fix=True))
        self.assertIn("STOP", song.header["VerseOrder"])

        # 2. File does already have STOP
        test_dir = Path("./testData/Test")
        test_filename = "sample.sng"
        song = SngFile(test_dir / test_filename)
        self.assertIn("STOP", song.header["VerseOrder"])
        self.assertTrue(song.validate_header_stop_verseorder())
        self.assertIn("STOP", song.header["VerseOrder"])

        # 3. File does have STOP but not at end and should stay this way
        test_dir = Path("./testData/Test")
        test_filename = "sample_stop_not_at_end.sng"
        song = SngFile(test_dir / test_filename)
        self.assertEqual("STOP", song.header["VerseOrder"][1])
        self.assertNotEqual("STOP", song.header["VerseOrder"][2])
        self.assertNotEqual("STOP", song.header["VerseOrder"][-1])
        self.assertTrue(song.validate_header_stop_verseorder(should_be_at_end=False))
        self.assertEqual("STOP", song.header["VerseOrder"][1])
        self.assertNotEqual("STOP", song.header["VerseOrder"][2])
        self.assertNotEqual("STOP", song.header["VerseOrder"][-1])

        # 4. File does have STOP but not at end and should not stay this way
        song = SngFile(test_dir / test_filename)
        self.assertEqual("STOP", song.header["VerseOrder"][1])
        self.assertNotEqual("STOP", song.header["VerseOrder"][-1])
        self.assertTrue(
            song.validate_header_stop_verseorder(fix=True, should_be_at_end=True)
        )
        self.assertNotEqual("STOP", song.header["VerseOrder"][1])
        self.assertEqual("STOP", song.header["VerseOrder"][-1])


if __name__ == "__main__":
    unittest.main()
