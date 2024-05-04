"""This module contains tests for most methods defined in main.py."""

import datetime
import filecmp
import logging
import os
import time
import unittest
from pathlib import Path
from shutil import copyfile

import pandas as pd
from ChurchToolsApi import ChurchToolsApi

import SNG_DEFAULTS
from main import (
    apply_ct_song_sng_count_qs_tag,
    check_ct_song_categories_exist_as_folder,
    clean_all_songs,
    download_missing_online_songs,
    generate_songbook_column,
    get_ct_songs_as_df,
    parse_sng_from_directory,
    prepare_required_song_tags,
    read_baiersbronn_songs_to_df,
    read_test_songs_to_df,
    upload_local_songs_by_id,
    upload_new_local_songs_and_generate_ct_id,
    validate_ct_songs_exist_locally_by_name_and_category,
    write_df_to_file,
)
from SngFile import SngFile


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
        """Check that all fixable songs in EG Lieder do have EG Songbook prefix."""
        songs_df = read_test_songs_to_df()

        filter1 = songs_df["path"] == Path("testData/EG Lieder")
        filter2 = songs_df["path"] == Path("testData/EG Psalmen & Sonstiges")
        eg_songs_df = songs_df[filter1 | filter2].copy()
        generate_songbook_column(eg_songs_df)

        # following variables are dependant on the number of files included in respective folders
        number_of_files_in_eg = 11
        number_of_files_with_eg_songbook_pre_fix = number_of_files_in_eg - 2 - 3
        # eg songs will be fixed, psalm range not ; EG764 is Sonstige, not Psalm
        number_of_files_with_eg_songbook_post_fix = number_of_files_in_eg - 2

        self.assertEqual(len(eg_songs_df), number_of_files_in_eg)
        self.assertEqual(
            eg_songs_df["Songbook"].str.startswith("EG").sum(),
            number_of_files_with_eg_songbook_pre_fix,
        )

        songs_df["SngFile"].apply(lambda x: x.validate_header_songbook(True))

        generate_songbook_column(eg_songs_df)

        self.assertEqual(
            eg_songs_df["Songbook"].str.startswith("EG").sum(),
            number_of_files_with_eg_songbook_post_fix,
        )

    def test_validate_songbook_special_cases(self) -> None:
        """Checks the application of the validate_header_songbook method in main.py with specific problematic examples.

        1. regular file with umlaut issues- filename is read
        2. invalid songbook entry
        3. Psalm songbook that should be detected as valid

        """
        # 1. (see docstring explanation)
        special_files = ["709 Herr, sei nicht ferne.sng"]
        song = parse_sng_from_directory(
            directory="./testData/EG Psalmen & Sonstiges",
            songbook_prefix="EG",
            filenames=special_files,
        )[0]
        self.assertEqual(special_files[0], song.filename)

        # 1. (see docstring explanation)
        # Special Case for Regex Testing - sample should have invalid songbook entry at first and valid EG entry later
        special_files = ["001 Macht Hoch die Tuer_invalid_songbook.sng"]
        song = parse_sng_from_directory(
            directory="./testData/EG Lieder",
            songbook_prefix="EG",
            filenames=special_files,
        )[0]
        song_df = pd.DataFrame([song], columns=["SngFile"])
        self.assertEqual(
            "WWDLP 999 and EG 999", song_df["SngFile"].iloc[0].header["Songbook"]
        )
        result = song_df["SngFile"].apply(lambda x: x.validate_header_songbook(False))
        self.assertEqual(result.sum(), 0, "Should have no valid entries")
        result = song_df["SngFile"].apply(lambda x: x.validate_header_songbook(True))
        self.assertEqual(result.sum(), 1, "Should have one valid entry")
        result = generate_songbook_column(song_df)
        self.assertEqual("EG 001", song_df["SngFile"].iloc[0].header["Songbook"])
        self.assertEqual(
            len(song_df["Songbook"]), song_df["Songbook"].str.startswith("EG").sum()
        )

        # 3. Special Case for Regex Testing - Songbook=EG 709 - Psalm 22 I -> is marked as autocorrect ...
        special_files = ["709 Herr, sei nicht ferne.sng"]
        song = parse_sng_from_directory(
            directory="./testData/EG Psalmen & Sonstiges",
            songbook_prefix="EG",
            filenames=special_files,
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

    def test_add_id_to_local_song_if_available_in_ct(self) -> None:
        """This should verify that add_id_to_local_song_if_available_in_ct is working as expected."""
        self.assertFalse(
            True,
            "Not Implemented see https://github.com/bensteUEM/SongBeamerQS/issues/13",
        )
        # TODO (bensteUEM): implement test_add_id_to_local_song_if_available_in_ct
        # https://github.com/bensteUEM/SongBeamerQS/issues/13

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

    def test_upload_new_local_songs_and_generate_ct_id(self) -> None:
        """This should verify that upload_new_local_songs_and_generate_ct_id is working as expected.

        1. copy sample template file and prepare it as parsed df
        2. retrieve list of current songs from CT isntance
        3. upload file
        4. check that local file now has id= param and rename remaining local file
        5. download and compare to expected
        6. cleanup
        """
        test_data_dir = Path("testData/Test")

        copyfile(
            test_data_dir / "sample_no_ct.sng",
            test_data_dir / "sample.sng",
        )
        song = SngFile(test_data_dir / "sample.sng")

        df_song = pd.DataFrame([song], columns=["SngFile"])
        for index, value in df_song["SngFile"].items():
            df_song.loc[(index, "filename")] = value.filename
            df_song.loc[(index, "path")] = value.path

        # 2. check ct
        df_ct = get_ct_songs_as_df(self.api)

        # 3. upload file
        upload_new_local_songs_and_generate_ct_id(df_sng=df_song, df_ct=df_ct)
        song_id = df_song.iloc[0]["SngFile"].get_id()

        # 4. check local ID
        self.assertNotEqual(song_id, -1, "Should have specifc ID when created")

        ct_song = self.api.get_songs(song_id=song_id)[0]
        arrangement_id = next(
            arrangement["id"]
            for arrangement in ct_song["arrangements"]
            if arrangement["isDefault"]
        )

        Path(test_data_dir / "sample.sng").rename(test_data_dir / "expected.sng")

        self.api.file_download(
            filename="sample.sng",
            domain_type="song_arrangement",
            domain_identifier=arrangement_id,
            target_path=str(test_data_dir),
        )

        self.assertTrue(
            filecmp.cmp(
                test_data_dir / "expected.sng",
                test_data_dir / "sample.sng",
            )
        )

        # 6. cleanup
        self.api.delete_song(song_id=song_id)

        Path(test_data_dir / "sample.sng").unlink()
        Path(test_data_dir / "expected.sng").unlink()

    def test_upload_local_songs_by_id(self) -> None:
        """This should verify that upload_local_songs_by_id is working as expected.

        Define two songs -
        1. should already have an attachment in Churchtools
        2. should exist but not have an attachement yet

        Cleanup ... Delete recently created attachment, remove local file copys and recover bak files

        """
        test_data_dir = Path("testData/Test")

        copyfile(
            test_data_dir / "sample.sng",
            test_data_dir / "sample.sng_bak",
        )
        song_with_attachment = SngFile(test_data_dir / "sample.sng")

        copyfile(
            test_data_dir / "sample_no_ct_attachement.sng",
            test_data_dir / "sample_no_ct_attachement.sng_bak",
        )
        song_no_attachment = SngFile(test_data_dir / "sample_no_ct_attachement.sng")

        df_songs = pd.DataFrame(
            [song_with_attachment, song_no_attachment], columns=["SngFile"]
        )
        for index, value in df_songs["SngFile"].items():
            df_songs.loc[(index, "filename")] = value.filename
            df_songs.loc[(index, "path")] = value.path

        df_ct = get_ct_songs_as_df(self.api)
        upload_local_songs_by_id(df_sng=df_songs, df_ct=df_ct)

        # Check sample 1 has attachment online and recently changed mod date
        ct_song_1 = self.api.get_songs(song_id=df_songs.iloc[0]["SngFile"].get_id())[0]
        arrangement_1 = next(
            arrangement
            for arrangement in ct_song_1["arrangements"]
            if arrangement["isDefault"]
        )
        self.assertIsNotNone(arrangement_1["id"], "Should have a song arrangement")
        ct_sng_attachment = next(
            file for file in arrangement_1["files"] if "sng" in file["name"]
        )
        ct_sng_modified_date = ct_sng_attachment["meta"]["modifiedDate"]
        ct_sng_modified_date = datetime.datetime.fromisoformat(
            ct_sng_modified_date.replace("Z", "+00:00")
        )
        # Get the local timezone of the system
        local_timezone = (
            datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        )
        datetime.datetime.now(local_timezone)

        offset = datetime.datetime.now(local_timezone) - ct_sng_modified_date
        allowed_delta = datetime.timedelta(minutes=2)
        self.assertGreater(
            allowed_delta, offset, "Last changed date of file should be recent"
        )

        # Check sample 2 has attachment
        ct_song_2 = self.api.get_songs(song_id=df_songs.iloc[1]["SngFile"].get_id())[0]
        arrangement_2 = next(
            arrangement
            for arrangement in ct_song_2["arrangements"]
            if arrangement["isDefault"]
        )
        self.assertIsNotNone(arrangement_2["id"], "Should have a song arrangement")

        # cleanup
        self.api.file_delete(
            domain_type="song_arrangement",
            domain_identifier=arrangement_2["id"],
            filename_for_selective_delete="sample_no_ct_attachement.sng",
        )

        Path(test_data_dir / "sample.sng_bak").rename(test_data_dir / "sample.sng")
        Path(test_data_dir / "sample_no_ct_attachement.sng_bak").rename(
            test_data_dir / "sample_no_ct_attachement.sng"
        )

    def test_write_df_to_file(self) -> None:
        """Test method checking functionality of write_df_to_file.

        checks modification time is not older than two seconds for
        1. sample file as dataframe and writing contents without change
        2. sample file as dataframe and writing contents to custom target dir
        """
        path = Path("testData/EG Lieder/")
        filename = "001 Macht Hoch die Tuer.sng"
        sample_path = path / filename
        song = SngFile(sample_path)

        sample_df = pd.DataFrame({"SngFile": [song]})

        # 1 same DIR
        write_df_to_file(sample_df)
        modification_time = sample_path.stat().st_mtime
        current_time = time.time()
        time_difference = current_time - modification_time

        self.assertGreater(2, time_difference)

        # 2 other target DIR
        new_output_parent_path = Path("test_output")
        write_df_to_file(sample_df, target_dir=new_output_parent_path)
        expected_output_path = new_output_parent_path / song.path.name / song.filename
        modification_time = expected_output_path.stat().st_mtime
        current_time = time.time()
        time_difference = current_time - modification_time

        self.assertGreater(2, time_difference)

    def test_apply_ct_song_sng_count_qs_tag(self) -> None:
        """Test that checks qs sng tags are correctly applied.

        IMPORTANT - This test method and the parameters used depend on the target system!

        Requires 2 sample songs
        * song_id=408 without SNG attached to any arrangement
        * song_id=2034 with SNG attached to any arrangement (also used with fake upload to check for 2 sng attachments)
        """
        sample_1_id = 408
        sample_2_id = 2034

        tags_by_name = prepare_required_song_tags(api=self.api)

        song1 = self.api.get_songs(song_id=sample_1_id)[0]
        song2 = self.api.get_songs(song_id=sample_2_id)[0]

        # Check first song
        apply_ct_song_sng_count_qs_tag(
            api=self.api, song=song1, tags_by_name=tags_by_name
        )
        tags1 = self.api.get_song_tags(song_id=sample_1_id)
        self.assertIn(str(tags_by_name["QS: missing sng"]), tags1)
        self.assertNotIn(str(tags_by_name["QS: too many sng"]), tags1)

        # Check 2nd song
        apply_ct_song_sng_count_qs_tag(
            api=self.api, song=song2, tags_by_name=tags_by_name
        )
        tags2 = self.api.get_song_tags(song_id=sample_2_id)
        self.assertNotIn(str(tags_by_name["QS: missing sng"]), tags2)
        self.assertNotIn(str(tags_by_name["QS: too many sng"]), tags2)

        # 3. modify 2nd song to include another fake sng attachement and validate
        dummy_filename = "QS_DELETE_ME_2_FILES.sng"
        arrangement_id_2 = song2["arrangements"][0]["id"]
        self.api.file_upload(
            source_filepath="testData/Test/sample_no_ct.sng",
            domain_type="song_arrangement",
            domain_identifier=arrangement_id_2,
            custom_file_name=dummy_filename,
        )
        song3 = self.api.get_songs(song_id=sample_2_id)[0]

        apply_ct_song_sng_count_qs_tag(
            api=self.api, song=song3, tags_by_name=tags_by_name
        )
        # get_song_tags uses cached version either refresh of cache or 10s cooldown required to see updated values
        time.sleep(10)

        tags3 = self.api.get_song_tags(song_id=sample_2_id)
        self.assertNotIn(str(tags_by_name["QS: missing sng"]), tags3)
        self.assertIn(str(tags_by_name["QS: too many sng"]), tags3)

        # song sng qs tags from samples
        self.api.file_delete(
            domain_type="song_arrangement",
            domain_identifier=arrangement_id_2,
            filename_for_selective_delete=dummy_filename,
        )
        for song_tag in [
            tags_by_name["QS: missing sng"],
            tags_by_name["QS: too many sng"],
        ]:
            self.api.remove_song_tag(song_id=sample_1_id, song_tag_id=song_tag)
            self.api.remove_song_tag(song_id=sample_2_id, song_tag_id=song_tag)

    def test_prepare_required_song_tags(self) -> None:
        """Checks that prepare song tags returns respective tags in list.

        Creation of non existant tags is not validated because tags are in use!
        """
        tags_by_name = prepare_required_song_tags(api=self.api)
        self.assertIn("QS: missing sng", tags_by_name)
        self.assertIn("QS: too many sng", tags_by_name)