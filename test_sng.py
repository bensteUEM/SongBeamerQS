"""This module contains tests for most methods defined in SngFile.py."""

import filecmp
import logging
import re
import unittest
from pathlib import Path
from shutil import copyfile, rmtree

from SngFile import SngFile, contains_songbook_prefix, generate_verse_marker_from_line


class TestSNG(unittest.TestCase):
    """Test Class for SNG related class and methods."""

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

    def test_file_name(self) -> None:
        """Checks if song contains correct filename and path information."""
        path = Path("testData/EG Lieder/")
        filename = "001 Macht Hoch die Tuer.sng"
        song = SngFile(path / filename)
        self.assertEqual(song.filename, filename)
        self.assertEqual(song.path, Path(path))

    def test_write_path_change(self) -> None:
        """Check that path was successfully changed on sample file."""
        path = Path("testData/EG Lieder/")
        filename = "001 Macht Hoch die Tuer.sng"
        song = SngFile(path / filename)
        self.assertEqual(song.filename, filename)
        self.assertEqual(song.path, Path(path))

        new_path = Path("test_output/EG Lieder/")
        rmtree(new_path.parent, ignore_errors=True)
        # path.walk with rmdir and unlink would require python 3.12
        """for root, dirs, files in new_path.walk(top_down=False):
            for name in files:
                (root / name).unlink()
            for name in dirs:
                (root / name).rmdir()
        new_path.rmdir()
        """
        song.write_path_change(new_path.parent)
        self.assertEqual(song.path, new_path)

    def test_header_title_parse(self) -> None:
        """Checks if param Title is correctly parsed.

        Test file that checks that no title is read with sample file which does not contain title line
        Will also fail if empty line handling does not exist
        """
        song = SngFile("./testData/EG Lieder/001 Macht Hoch die Tuer.sng")
        song.parse_param("#Title=Macht Hoch die Tür")

        expected_output = {"Title": "Macht Hoch die Tür"}
        self.assertEqual(song.header["Title"], expected_output["Title"])

        song2 = SngFile("./testData/Test/sample_missing_headers.sng")
        self.assertNotIn("Title", song2.header)

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

    def test_content_empty_block(self) -> None:
        """Test case with a SNG file that contains and empty block because it ends with ---."""
        test_dir = Path("./testData/Test")
        test_filename = "sample_churchsongid_caps.sng"
        song = SngFile(test_dir / test_filename, "EG")

        self.assertEqual(len(song.content), 1)
        self.assertEqual(len(song.content["Unknown"]), 3)

    def test_file_write(self) -> None:
        """Functions which compares the original file to the one generated after parsing."""
        test_dir = Path("./testData/Test")
        test_filename = "sample.sng"

        song = SngFile(test_dir / test_filename, "EG")
        song.write_file(suffix="_test_file_write")

        self.assertTrue(
            filecmp.cmp(
                test_dir / test_filename,
                test_dir / (test_filename[:-4] + "_test_file_write.sng"),
            )
        )

        (test_dir / (test_filename[:-4] + "_test_file_write.sng")).unlink()

    def test_content(self) -> None:
        """Checks if all Markers from the Demo Set are detected.

        Test to check if a content without proper label is replaced as unknown and custom content header is read
        """
        song = SngFile("./testData/022 Die Liebe des Retters.sng")
        target = ["Intro", "Strophe 1", "Refrain 1", "Strophe 2", "Bridge"]
        markers = song.content.keys()

        for marker in markers:
            self.assertIn(marker, target)

        # Special Exceptions
        song2 = SngFile("./testData/022 Die Liebe des Retters_missing_block.sng")
        target = ["Unknown", "$$M=Testnameblock", "Refrain 1", "Strophe 2", "Bridge"]
        markers = song2.content.keys()

        for marker in markers:
            self.assertIn(marker, target)

        self.assertIn("Testnameblock", song2.content["$$M=Testnameblock"][0])

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

    def test_file_short(self) -> None:
        """Checks a specific SNG file which contains a header only and no content."""
        test_dir = Path("./testData/Test/")
        test_filename = "sample_header_only.sng"
        song = SngFile(test_dir / test_filename)
        self.assertEqual(song.filename, test_filename)

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

    def test_content_intro_slide(self) -> None:
        """Checks that sample file has no Intro in Verse Order or Blocks and repaired file contains both."""
        song = SngFile("./testData/079 Höher_reformat.sng")
        self.assertNotIn("Intro", song.header["VerseOrder"])
        self.assertNotIn("Intro", song.content.keys())
        song.fix_intro_slide()
        self.assertIn("Intro", song.header["VerseOrder"])
        self.assertIn("Intro", song.content.keys())

    def test_validate_verse_numbers(self) -> None:
        """Checks whether verse numbers are regular."""
        song = SngFile("./testData/123 Du bist der Schöpfer des Universums.sng")
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
        ]
        self.assertEqual(expected, list(song.content.keys()))

    def test_validate_verse_numbers2(self) -> None:
        """More complicated file with more issues and problems with None in VerseOrder."""
        song = SngFile("./testData/375 Dass Jesus siegt bleibt ewig ausgemacht.sng")
        text = (
            "Strophe 1a,Strophe 1b,Strophe 1c,Strophe 4a,Strophe 4b,Strophe 4c,STOP,"
            "Strophe 2a,Strophe 2b,Strophe 2c,Strophe 3a,Strophe 3b,Strophe 3c"
        )

        expected_order = text.split(",")
        self.assertEqual(song.header["VerseOrder"], expected_order)

        song.validate_verse_numbers(fix=True)
        expected_order = ["Strophe 1", "Strophe 4", "STOP", "Strophe 2", "Strophe 3"]
        self.assertEqual(expected_order, song.header["VerseOrder"])
        expected_order = ["Strophe 1", "Strophe 2", "Strophe 3", "Strophe 4"]
        self.assertEqual(expected_order, list(song.content.keys()))

    def test_validate_verse_numbers3(self) -> None:
        """Test with a file that has other verses than verse order.

        fixes verse order based on content
        and verse number validation should not have any impact
        """
        song = SngFile("./testData/289 Nun lob mein Seel den Herren.sng")
        song.validate_verse_order_coverage(True)
        song.validate_verse_numbers(True)

        self.assertIn("Verse 1", song.header["VerseOrder"])
        self.assertIn("STOP", song.header["VerseOrder"])
        self.assertIn("Verse 1", song.content.keys())

    def test_header_validate_verse_numbers4(self) -> None:
        """Special Case 375 Dass Jesus siegt bleibt ewig ausgemacht.sng with merging verse blocks.

        did show up as list instead of lines for slide 2 and 3 for verse 1
        """
        song = SngFile(
            "./testData/375 Dass Jesus siegt bleibt ewig ausgemacht.sng", "EG"
        )
        self.assertEqual(song.content["Strophe 1b"][1][0], "denn alles ist")
        song.validate_verse_numbers(fix=True)
        self.assertEqual(song.content["Strophe 1"][2][0], "denn alles ist")

    def test_content_stop_verse_order(self) -> None:
        """Checks and corrects existance of STOP in Verse Order.

        1. File does not have STOP
        2. File does already have STOP
        3. File does have STOP but not at end and should stay this way
        4. File does have STOP but not at end and should not stay this way
        """
        # 1. File does not have STOP
        song = SngFile("./testData/079 Höher_reformat.sng")
        self.assertNotIn("STOP", song.header["VerseOrder"])
        self.assertTrue(song.validate_stop_verseorder(fix=True))
        self.assertIn("STOP", song.header["VerseOrder"])

        # 2. File does already have STOP
        song = SngFile("./testData/022 Die Liebe des Retters.sng")
        self.assertIn("STOP", song.header["VerseOrder"])
        self.assertTrue(song.validate_stop_verseorder())
        self.assertIn("STOP", song.header["VerseOrder"])

        # 3. File does have STOP but not at end and should stay this way
        song = SngFile("./testData/085 O Haupt voll Blut und Wunden.sng")
        self.assertEqual("STOP", song.header["VerseOrder"][5])
        self.assertNotEqual("STOP", song.header["VerseOrder"][11])
        self.assertNotEqual("STOP", song.header["VerseOrder"][-1])
        self.assertTrue(song.validate_stop_verseorder(should_be_at_end=False))
        self.assertEqual("STOP", song.header["VerseOrder"][5])
        self.assertNotEqual("STOP", song.header["VerseOrder"][-1])
        self.assertNotEqual("STOP", song.header["VerseOrder"][11])

        # 4. File does have STOP but not at end and should not stay this way
        song = SngFile("./testData/085 O Haupt voll Blut und Wunden.sng")
        self.assertEqual("STOP", song.header["VerseOrder"][5])
        self.assertNotEqual("STOP", song.header["VerseOrder"][-1])
        self.assertTrue(song.validate_stop_verseorder(fix=True, should_be_at_end=True))
        self.assertNotEqual("STOP", song.header["VerseOrder"][5])
        self.assertEqual("STOP", song.header["VerseOrder"][-1])

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
        info_template_prefix = "INFO:root:Found problematic encoding in str '"

        messages = [
            f"{info_template_prefix}Ã¤aaaÃ¤a'",
            "DEBUG:root:replaced Ã¤aaaÃ¤a by äaaaäa",
            f"{info_template_prefix}Ã¤'",
            "DEBUG:root:replaced Ã¤ by ä",
            f"{info_template_prefix}Ã¶'",
            "DEBUG:root:replaced Ã¶ by ö",
            f"{info_template_prefix}Ã¼'",
            "DEBUG:root:replaced Ã¼ by ü",
            f"{info_template_prefix}Ã\x84'",
            "DEBUG:root:replaced Ã\x84 by Ä",
            f"{info_template_prefix}Ã\x96'",
            "DEBUG:root:replaced Ã\x96 by Ö",
            f"{info_template_prefix}Ã\x9c'",
            "DEBUG:root:replaced Ã\x9c by Ü",
            f"{info_template_prefix}Ã\x9f'",
            "DEBUG:root:replaced Ã\x9f by ß",
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

    def test_getset_id(self) -> None:
        """Test that runs various variations of songbook parts which should be detected by improved helper method."""
        path = "./testData/EG Lieder/"
        sample_filename = "001 Macht Hoch die Tuer.sng"
        sample_id = 762
        song = SngFile(path + sample_filename)

        self.assertEqual(song.get_id(), sample_id)
        song.set_id(-2)
        self.assertEqual(song.get_id(), -2)

    def test_isoutf8(self) -> None:
        """Test method for conversion of iso-8859-1  files to UTF-8 using public domain sample from tests folder.

        1. Check that all test files exist and encoding match accordingly
        2. Parses an iso 8859-1 encoded file
        3. Parses an utf-8 file with BOM
        4. Parses an utf-8 file without BOM
        5. Parsing iso file writes utf8 and checks if output file has BOM
        """
        path = "testData/ISO-UTF8/"
        iso_file_path = path + "Herr du wollest uns bereiten_iso.sng"
        iso2utf_file_name = "Herr du wollest uns bereiten_iso2utf.sng"
        iso2utf_file_path = path + iso2utf_file_name
        utf_file_path = path + "Herr du wollest uns bereiten_ct_utf8.sng"
        no_bom_utf_file_path = path + "Herr du wollest uns bereiten_noBOM_utf8.sng"

        # Part 1
        with Path(iso_file_path).open(encoding="iso-8859-1") as file_iso_as_iso:
            text = file_iso_as_iso.read()
        self.assertEqual("#", text[0], "ISO file read with correct ISO encoding")

        with Path(iso_file_path).open(
            encoding="utf-8"
        ) as file_iso_as_utf, self.assertRaises(UnicodeDecodeError) as cm:
            text = file_iso_as_utf.read()

        with Path(utf_file_path).open(encoding="iso-8859-1") as file_utf_as_iso:
            text = file_utf_as_iso.read()
            self.assertEqual("ï»¿", text[0:3], "UTF8 file read with wrong encoding")

        with Path(utf_file_path).open(encoding="utf-8") as file_utf_as_utf:
            text = file_utf_as_utf.read()
        self.assertEqual(
            "\ufeff", text[0], "UTF8 file read with correct encoding including BOM"
        )

        # Part 2
        with self.assertLogs(level=logging.DEBUG) as cm:
            sng = SngFile(iso_file_path)
        expected1 = "INFO:root:testData/ISO-UTF8/Herr du wollest uns bereiten_iso.sng is read as iso-8859-1 - be aware that encoding is change upon write!"
        self.assertEqual(expected1, cm.output[0])
        self.assertEqual(2, len(cm.output))

        # Part 3
        with self.assertLogs(level=logging.DEBUG) as cm:
            sng = SngFile(utf_file_path)
        expected1 = "DEBUG:root:testData/ISO-UTF8/Herr du wollest uns bereiten_ct_utf8.sng is detected as utf-8 because of BOM"
        self.assertEqual(expected1, cm.output[0])
        self.assertEqual(2, len(cm.output))

        # Part 4
        with self.assertLogs(level=logging.INFO) as cm:
            sng = SngFile(no_bom_utf_file_path)
        expected1 = "INFO:root:testData/ISO-UTF8/Herr du wollest uns bereiten_noBOM_utf8.sng is read as utf-8 but no BOM"
        self.assertEqual(expected1, cm.output[0])
        self.assertEqual(1, len(cm.output))

        # Part 5
        sng = SngFile(iso_file_path)
        sng.filename = iso2utf_file_name
        sng.write_file()

        with Path(iso2utf_file_path).open(encoding="utf-8") as file_iso2utf:
            text = file_iso2utf.read()
        self.assertEqual(
            "\ufeff", text[0], "UTF8 file read with correct encoding including BOM"
        )
        Path.unlink(iso2utf_file_path)


if __name__ == "__main__":
    unittest.main()
