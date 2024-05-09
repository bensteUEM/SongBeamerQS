"""This module contains tests for most methods defined in SngFile.py."""

import filecmp
import json
import logging
import logging.config
import unittest
from pathlib import Path
from shutil import rmtree

from SngFile import SngFile

config_file = Path("logging_config.json")
with config_file.open(encoding="utf-8") as f_in:
    logging_config = json.load(f_in)
    log_directory = Path(logging_config["handlers"]["file"]["filename"]).parent
    if not log_directory.exists():
        log_directory.mkdir(parents=True)
    logging.config.dictConfig(config=logging_config)
logger = logging.getLogger(__name__)


class TestSNGParser(unittest.TestCase):
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

    def test_file_short(self) -> None:
        """Checks a specific SNG file which contains a header only and no content."""
        test_dir = Path("./testData/Test/")
        test_filename = "sample_header_only.sng"
        song = SngFile(test_dir / test_filename)
        self.assertEqual(song.filename, test_filename)

    def test_isoutf8(self) -> None:
        """Test method for conversion of iso-8859-1  files to UTF-8 using public domain sample from tests folder.

        1. Check that all test files exist and encoding match accordingly
        2. Parses an iso 8859-1 encoded file
        3. Parses an utf-8 file with BOM
        4. Parses an utf-8 file without BOM
        5. Parsing iso file writes utf8 and checks if output file has BOM
        """
        path = Path("testData/ISO-UTF8/")
        iso_file_path = path / "Herr du wollest uns bereiten_iso.sng"
        iso2utf_file_name = "Herr du wollest uns bereiten_iso2utf.sng"
        iso2utf_file_path = path / iso2utf_file_name
        utf_file_path = path / "Herr du wollest uns bereiten_ct_utf8.sng"
        no_bom_utf_file_path = path / "Herr du wollest uns bereiten_noBOM_utf8.sng"

        # Part 1
        with iso_file_path.open(encoding="iso-8859-1") as file_iso_as_iso:
            text = file_iso_as_iso.read()
        self.assertEqual("#", text[0], "ISO file read with correct ISO encoding")

        with iso_file_path.open(encoding="utf-8") as file_iso_as_utf, self.assertRaises(
            UnicodeDecodeError
        ) as cm:
            text = file_iso_as_utf.read()

        with utf_file_path.open(encoding="iso-8859-1") as file_utf_as_iso:
            text = file_utf_as_iso.read()
            self.assertEqual("ï»¿", text[0:3], "UTF8 file read with wrong encoding")

        with utf_file_path.open(encoding="utf-8") as file_utf_as_utf:
            text = file_utf_as_utf.read()
        self.assertEqual(
            "\ufeff", text[0], "UTF8 file read with correct encoding including BOM"
        )

        # Part 2
        with self.assertLogs(level=logging.DEBUG) as cm:
            sng = SngFile(iso_file_path)
        expected1 = "INFO:SngFileParserPart:testData/ISO-UTF8/Herr du wollest uns bereiten_iso.sng is read as iso-8859-1 - be aware that encoding is change upon write!"
        self.assertEqual(expected1, cm.output[0])
        self.assertEqual(2, len(cm.output))

        # Part 3
        with self.assertLogs(level=logging.DEBUG) as cm:
            sng = SngFile(utf_file_path)
        expected1 = "DEBUG:SngFileParserPart:testData/ISO-UTF8/Herr du wollest uns bereiten_ct_utf8.sng is detected as utf-8 because of BOM"
        self.assertEqual(expected1, cm.output[0])
        self.assertEqual(2, len(cm.output))

        # Part 4
        with self.assertLogs(level=logging.INFO) as cm:
            sng = SngFile(no_bom_utf_file_path)
        expected1 = "INFO:SngFileParserPart:testData/ISO-UTF8/Herr du wollest uns bereiten_noBOM_utf8.sng is read as utf-8 but no BOM"
        self.assertEqual(expected1, cm.output[0])
        self.assertEqual(1, len(cm.output))

        # Part 5
        sng = SngFile(iso_file_path)
        sng.filename = iso2utf_file_name
        sng.write_file()

        with iso2utf_file_path.open(encoding="utf-8") as file_iso2utf:
            text = file_iso2utf.read()
        self.assertEqual(
            "\ufeff", text[0], "UTF8 file read with correct encoding including BOM"
        )
        iso2utf_file_path.unlink()


if __name__ == "__main__":
    unittest.main()
