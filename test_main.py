"""This module contains tests for most methods defined in main.py."""
import logging
import os
import unittest
from pathlib import Path

import pandas as pd
from ChurchToolsApi import ChurchToolsApi

import SNG_DEFAULTS
from main import (
    check_ct_song_categories_exist_as_folder,
    clean_all_songs,
    download_missing_online_songs,
    generate_songbook_column,
    get_ct_songs_as_df,
    parse_sng_from_directory,
    read_baiersbronn_songs_to_df,
    validate_ct_songs_exist_locally_by_name_and_category,
)


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
            filename="logs/TestMain.log",
            encoding="utf-8",
            format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
            level=logging.DEBUG,
        )
        logging.info("Excecuting Test Main RUN")

    def setUp(self) -> None:
        """Setup of TestCase.

        Prepares anything that can be used by all tests
        """
        ct_domain = os.getenv("CT_DOMAIN")
        ct_token = os.getenv("CT_TOKEN")

        if ct_domain is None or ct_token is None:
            logging.info(
                "ct_domain or ct_token missing in env variables - using local config instead"
            )
            from secure import config

            ct_domain = config.ct_domain
            ct_token = config.ct_token

        self.api = ChurchToolsApi(config.ct_domain, ct_token=config.ct_token)

    def test_ct_connection_established(self) -> None:
        """Checks that an API connection to a CT instance was establied.

        If configuration does not provide necessary details there will be an error executing this test.
        This means one would need to verify everything was setup correctly
        """
        result = self.api.who_am_i()
        self.assertIsNotNone(result)

    def test_ct_categories_as_local_folder(self) -> None:
        """Check CT categories exist against the local known directory.

        * Loads ist of all songs
        * get unique values of category names
        * checks that all exist in SNG_DEFAULTS.KnownDirectory path
        """
        songs = self.api.get_songs()
        df_ct = pd.json_normalize(songs)

        self.assertTrue(
            check_ct_song_categories_exist_as_folder(
                list(df_ct["category.name"].unique()), SNG_DEFAULTS.KnownDirectory
            )
        )

    def test_eg_with_songbook_prefix(self) -> None:
        """Check that all songs in EG Lieder does have EG Songbook prefix."""
        songs_df = read_baiersbronn_songs_to_df()
        filter1 = songs_df["path"] == Path(
            "/home/benste/Documents/Kirchengemeinde Baiersbronn/Beamer/Songbeamer - Songs/EG Lieder"
        )
        filter2 = songs_df["path"] == Path(
            "/home/benste/Documents/Kirchengemeinde Baiersbronn/Beamer/Songbeamer - Songs/EG Psalmen & Sonstiges"
        )

        songs_df["SngFile"].apply(lambda x: x.validate_header_songbook(True))
        eg_songs_df = songs_df[filter1 | filter2]
        generate_songbook_column(songs_df)
        self.assertEqual(
            len(eg_songs_df["SngFile"]), songs_df["Songbook"].str.startswith("EG").sum()
        )

    def test_validate_songbook_special_cases(self) -> None:
        """Checks the application of the validate_header_songbook method in main.py with specific problematic examples."""
        special_files = ["709 Herr, sei nicht ferne.sng"]
        song = parse_sng_from_directory(
            directory="./testData/Psalm", songbook_prefix="EG", filenames=special_files
        )[0]
        self.assertEqual(special_files[0], song.filename)

        # Special Case for Regex Testing
        special_files = ["548 Kreuz auf das ich schaue.sng"]
        song = parse_sng_from_directory(
            directory="./testData", songbook_prefix="EG", filenames=special_files
        )[0]
        song_df = pd.DataFrame([song], columns=["SngFile"])
        self.assertEqual(
            "Wwdlp 170 & EG 548", song_df["SngFile"].iloc[0].header["Songbook"]
        )
        result = song_df["SngFile"].apply(lambda x: x.validate_header_songbook(False))
        self.assertEqual(result.sum(), 0, "Should have no valid entries")
        result = song_df["SngFile"].apply(lambda x: x.validate_header_songbook(True))
        self.assertEqual(result.sum(), 1, "Should have one valid entry")
        result = generate_songbook_column(song_df)
        self.assertEqual("EG 548", song_df["SngFile"].iloc[0].header["Songbook"])
        self.assertEqual(
            len(song_df["Songbook"]), song_df["Songbook"].str.startswith("EG").sum()
        )

        # Special Case for Regex Testing - Songbook=EG 709 - Psalm 22 I -> is marked as autocorrect ...
        special_files = ["709 Herr, sei nicht ferne.sng"]
        song = parse_sng_from_directory(
            directory="./testData/Psalm", songbook_prefix="EG", filenames=special_files
        )[0]
        song_df = pd.DataFrame([song], columns=["SngFile"])
        self.assertEqual(
            "EG 709 - Psalm 22 I", song_df["SngFile"].iloc[0].header["Songbook"]
        )
        result = song_df["SngFile"].apply(lambda x: x.validate_header_songbook(False))
        self.assertEqual(result.sum(), 1, "Should have one valid entry")

    def test_validate_comment_special_case(self) -> None:
        """Test method which validates one specific file which had differences while parsing."""
        special_files = ["Psalm 104_Stierlen.sng"]
        song = parse_sng_from_directory(
            directory="./testData", songbook_prefix="", filenames=special_files
        )[0]
        expected = "77u/RW50c3ByaWNodCBuaWNodCBkZXIgVmVyc2lvbiBhdXMgZGVtIEVHIQ=="
        self.assertEqual(expected, song.header["Comments"])

    def test_missing_song(self) -> None:
        """Checking why Hintergrundmusik fails.

        ELKW1610.krz.tools specific test case
        requires song id 204 to be present
        """
        sample_song_id = 204
        songs_temp = parse_sng_from_directory(
            directory=SNG_DEFAULTS.KnownDirectory + "Hintergrundmusik",
            songbook_prefix="",
            filenames=["The Knowledge of Good and Evil.sng"],
        )
        songs_temp = read_baiersbronn_songs_to_df()
        df_ct = get_ct_songs_as_df(self.api)
        df_ct = df_ct[df_ct["id"] == sample_song_id]

        df_sng = pd.DataFrame(songs_temp, columns=["SngFile"])
        for index, value in df_sng["SngFile"].items():
            df_sng.loc[(index, "filename")] = value.filename
            df_sng.loc[(index, "path")] = value.path

        compare = validate_ct_songs_exist_locally_by_name_and_category(df_ct, df_sng)
        self.assertEqual(compare["_merge"][0], "both")

        clean_all_songs(df_sng)
        compare = validate_ct_songs_exist_locally_by_name_and_category(df_ct, df_sng)
        self.assertEqual(compare["_merge"][0], "both")

    def test_emptied_song(self) -> None:
        """Test that checks on FJ 3 - 238.

        because it was emptied during execution even though backup did have content
        Issue was encoding UTF8 - needed to save song again to correct encoding - added ERROR logging for song parsing
        """
        songs_temp = parse_sng_from_directory(
            directory=SNG_DEFAULTS.KnownDirectory + "Feiert Jesus 3",
            songbook_prefix="FJ3",
            filenames=["238 Der Herr segne dich.sng"],
        )
        self.assertIn("Refrain", songs_temp[0].content.keys())
        songs_temp = read_baiersbronn_songs_to_df()

    def test_add_id_to_local_song_if_available_in_ct(self) -> None:  # TODO #13
        """This should verify that add_id_to_local_song_if_available_in_ct is working as expected."""
        self.assertFalse(True, "Not Implemented")

    def test_download_missing_online_songs(self) -> None:
        """ELKW1610.krz.tools specific test case for the named function (using 2 specific song IDs).

        * deletes EG 002 if exists locally
        * Reads one local sng file (EG 001)
        * tries to detect that EG002 from CT is missing
        * downloads the file
        * checks if download success
        * deletes file
        """
        songs_temp = []
        dirname = "testData/"
        dirprefix = "TEST"

        test2name = "002 Er ist die rechte Freudensonn.sng"
        test2path = dirname + "/EG Lieder/" + test2name

        Path.unlink(test2path, missing_ok=True)

        for key, value in SNG_DEFAULTS.KnownFolderWithPrefix.items():
            dirname = "./testData/" + key
            if not Path(dirname).exists():
                continue
            dirprefix = value
            songs_temp.extend(
                parse_sng_from_directory(directory=dirname, songbook_prefix=dirprefix)
            )

        df_sng_test = pd.DataFrame(songs_temp, columns=["SngFile"])
        for index, value in df_sng_test["SngFile"].items():
            df_sng_test.loc[(index, "filename")] = value.filename
            df_sng_test.loc[(index, "path")] = value.path

        ct_songs = [
            self.api.get_songs(song_id=762)[0],
            self.api.get_songs(song_id=1113)[0],
        ]
        df_ct_test = pd.json_normalize(ct_songs)

        result = download_missing_online_songs(df_sng_test, df_ct_test, self.api)
        self.assertTrue(result)

        exists = Path(test2path).exists()
        self.assertTrue(exists)
        Path(test2path).unlink()

    def test_upload_new_local_songs_and_generate_ct_id(self) -> None:  # TODO #15
        """This should verify that upload_new_local_songs_and_generate_ct_id is working as expected."""
        self.assertFalse(True, "Not Implemented")

    def test_upload_local_songs_by_id(self) -> None:
        """This should verify that upload_local_songs_by_id is working as expected."""
        self.assertFalse(True, "Not Implemented")  # TODO #14
