"""This module contains tests for most methods defined in main.py."""

import datetime
import filecmp
import json
import logging
import logging.config
import os
import time
import unittest
from pathlib import Path
from shutil import copyfile

import pandas as pd
from ChurchToolsApi import ChurchToolsApi

import SNG_DEFAULTS
from main import (
    add_id_to_local_song_if_available_in_ct,
    apply_ct_song_sng_count_qs_tag,
    check_ct_song_categories_exist_as_folder,
    clean_all_songs,
    download_missing_online_songs,
    generate_songbook_column,
    get_ct_songs_as_df,
    parse_sng_from_directory,
    prepare_required_song_tags,
    read_songs_to_df,
    upload_local_songs_by_id,
    upload_new_local_songs_and_generate_ct_id,
    validate_ct_songs_exist_locally_by_name_and_category,
    write_df_to_file,
)
from SngFile import SngFile

config_file = Path("logging_config.json")
with config_file.open(encoding="utf-8") as f_in:
    logging_config = json.load(f_in)
    logging.config.dictConfig(config=logging_config)
logger = logging.getLogger(__name__)


class TestSNG(unittest.TestCase):
    """Test Class for SNG related class and methods."""

    def __init__(self, *args: any, **kwargs: any) -> None:
        """Preparation of Test object.

        Params:
            args: passthrough arguments
            kwargs: passthrough named arguments
        """
        super().__init__(*args, **kwargs)

    def setUp(self) -> None:
        """Setup of TestCase.

        Prepares anything that can be used by all tests
        """
        ct_domain = os.getenv("CT_DOMAIN")
        ct_token = os.getenv("CT_TOKEN")

        if ct_domain is None or ct_token is None:
            from secure.config import ct_domain, ct_token  # noqu PLC0415

            logger.info(
                "ct_domain or ct_token missing in env variables - using local config instead"
            )
            from secure import config

            ct_domain = config.ct_domain
            ct_token = config.ct_token

        self.api = ChurchToolsApi(domain=ct_domain, ct_token=ct_token)

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

        expected_in_testing = list(df_ct["category.name"].unique())

        missing_directories = check_ct_song_categories_exist_as_folder(
            ct_song_categories=expected_in_testing,
            directory=Path("./testData"),
            fix=False,
        )
        # ELKW1610.krz.tools specific test case for the named function
        ommited_in_tests = {
            "Hintergrundmusik",
            "Feiert Jesus 3",
            "Musical - Leuchte, leuchte Weihnachtsstern",
            "Sonstige Texte",
            "Sonstige Lieder",
            "Feiert Jesus 2",
            "Feiert Jesus 5",
            "Feiert Jesus 6",
            "Feiert Jesus 1",
            "Feiert Jesus 4",
        }

        self.assertEqual(len(missing_directories - ommited_in_tests), 0)

    def test_eg_with_songbook_prefix(self) -> None:
        """Check that all fixable songs in EG Lieder do have EG Songbook prefix."""
        songs_df = read_songs_to_df(testing=True)

        filter1 = songs_df["path"] == Path("testData/EG Lieder")
        filter2 = songs_df["path"] == Path("testData/EG Psalmen & Sonstiges")
        eg_songs_df = songs_df[filter1 | filter2].copy()
        generate_songbook_column(eg_songs_df)

        # following variables are dependant on the number of files included in respective folders
        number_of_files_in_eg = 8
        number_of_files_with_eg_songbook_pre_fix = 4
        # eg songs will be fixed, psalm range not ; EG764 is Sonstige, not Psalm
        number_of_files_with_eg_songbook_post_fix = 7

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
        special_files = ["sample.sng"]
        song = parse_sng_from_directory(
            directory="./testData/Test", songbook_prefix="", filenames=special_files
        )[0]
        expected = "77u/RW50c3ByaWNodCBuaWNodCBkZXIgVmVyc2lvbiBhdXMgZGVtIEVHIQ=="
        self.assertEqual(expected, song.header["Comments"])

    def test_emptied_song(self) -> None:
        """Test that a song which would have been emptied on parsing because of encoding issues is not empty.

        because it was emptied during execution even though backup did have content
        Issue was encoding UTF8 - needed to save song again to correct encoding - added ERROR logging for song parsing
        """
        songs_temp = parse_sng_from_directory(
            directory="testData/EG Psalmen & Sonstiges",
            songbook_prefix="TEST",
            filenames=["709 Herr, sei nicht ferne.sng"],
        )
        self.assertIn("Verse", songs_temp[0].content.keys())

    def test_validate_ct_songs_exist_locally_by_name_and_category(self) -> None:
        """Test function proving one case of validate_ct_songs_exist_locally_by_name_and_category.

        uses one song which does not have a CT id and tries to match by name and category
        """
        test_dir = Path("./testData/Test")
        test_filename = "sample_no_ct.sng"
        song = SngFile(test_dir / test_filename)
        self.assertNotIn("id", song.header)

        test_local_df = pd.DataFrame([song], columns=["SngFile"])
        test_local_df["filename"] = test_filename
        test_local_df["path"] = test_dir

        test_ct_id = 3064
        test_ct_df = pd.json_normalize(self.api.get_songs(song_id=test_ct_id))

        result = validate_ct_songs_exist_locally_by_name_and_category(
            df_sng=test_local_df, df_ct=test_ct_df
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["_merge"], "both")

    def test_add_id_to_local_song_if_available_in_ct(self) -> None:
        """This should verify that add_id_to_local_song_if_available_in_ct is working as expected."""
        test_dir = Path("./testData/Test")
        test_filename = "sample_no_ct.sng"
        copyfile(test_dir / test_filename, test_dir / (test_filename + "_bak"))
        song = SngFile(test_dir / test_filename)
        self.assertNotIn("id", song.header)

        test_local_df = pd.DataFrame([song], columns=["SngFile"])
        test_local_df["filename"] = test_filename
        test_local_df["path"] = test_dir

        test_ct_id = 3064
        test_ct_df = pd.json_normalize(self.api.get_songs(song_id=test_ct_id))

        add_id_to_local_song_if_available_in_ct(df_sng=test_local_df, df_ct=test_ct_df)
        self.assertEqual(song.header["id"], str(test_ct_id))

        # cleanup
        (test_dir / (test_filename + "_bak")).rename(test_dir / test_filename)

    def test_download_missing_online_songs(self) -> None:
        """ELKW1610.krz.tools specific test case for the named function (using 2 specific song IDs).

        1. define sample data and deletes EG 002 if exists locally
        2. Reads local sng files from known directories - should not include sample2
        3. tries to detect that EG002 from CT is missing (by comparing to CT data for sample 1 and 2 only)
        4. downloads all missing files
        5. checks that file for sample_2 now exists
        6. cleanup - deletes file
        """
        # 1. prepare
        songs_temp = []
        dirname = "testData/"
        dirprefix = "TEST"

        sample1_id = 762

        sample2_id = 1113
        sample2_name = "002 Er ist die rechte Freudensonn.sng"
        test2path = dirname + "/EG Lieder/" + sample2_name

        Path.unlink(test2path, missing_ok=True)

        # 2. read all songs from known folders in testData
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

        # 3. read specific sample ids from CT
        ct_songs = [
            self.api.get_songs(song_id=sample1_id)[0],
            self.api.get_songs(song_id=sample2_id)[0],
        ]
        df_ct_test = pd.json_normalize(ct_songs)

        # 4. start download of mising songs
        result = download_missing_online_songs(df_sng_test, df_ct_test, self.api)
        self.assertTrue(result)

        # 5. check if download successful
        self.assertTrue(Path(test2path).exists())

        # 6. Cleanup
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
            test_data_dir / "sample_no_ct.sng_bak",
        )
        song = SngFile(test_data_dir / "sample_no_ct.sng")

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

        Path(test_data_dir / "sample_no_ct.sng").rename(test_data_dir / "expected.sng")

        self.api.file_download(
            filename="sample_no_ct.sng",
            domain_type="song_arrangement",
            domain_identifier=arrangement_id,
            target_path=str(test_data_dir),
        )

        self.assertTrue(
            filecmp.cmp(
                test_data_dir / "expected.sng",
                test_data_dir / "sample_no_ct.sng",
            )
        )

        # 6. cleanup
        self.api.delete_song(song_id=song_id)

        Path(test_data_dir / "expected.sng").unlink()
        Path(test_data_dir / "sample_no_ct.sng_bak").rename(
            test_data_dir / "sample_no_ct.sng"
        )

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

        Path(test_data_dir / "sample_no_ct_attachement.sng_bak").rename(
            test_data_dir / "sample_no_ct_attachement.sng"
        )
        Path(test_data_dir / "sample.sng_bak").rename(test_data_dir / "sample.sng")

    def test_write_df_to_file(self) -> None:
        """Test method checking functionality of write_df_to_file.

        checks modification time is not older than two seconds for
        1. sample file as dataframe and writing contents without change
        2. sample file as dataframe and writing contents to custom target dir
        """
        sample_dir = Path("testData/Test/")
        sample_filename = "sample.sng"

        copyfile(
            sample_dir / sample_filename,
            sample_dir / (sample_filename + "_bak"),
        )

        sample_filepath = sample_dir / sample_filename
        sample_song = SngFile(sample_filepath)

        sample_df = pd.DataFrame({"SngFile": [sample_song]})

        # 1 same DIR
        write_df_to_file(sample_df)
        modification_time = sample_filepath.stat().st_mtime
        current_time = time.time()
        time_difference = current_time - modification_time

        self.assertGreater(2, time_difference)
        # Cleanup
        Path(sample_dir / (sample_filename + "_bak")).rename(
            sample_dir / sample_filename
        )

        # 2 other target DIR
        sample_dir2 = Path("test_output")
        write_df_to_file(sample_df, target_dir=sample_dir2)

        expected_filepath = sample_dir2 / sample_song.path.name / sample_song.filename
        modification_time = expected_filepath.stat().st_mtime
        current_time = time.time()
        time_difference = current_time - modification_time

        self.assertGreater(2, time_difference)
        # Cleanup
        expected_filepath.unlink()

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

    def test_clean_all_songs(self) -> None:
        """Method executing "clean_all_songs" on some songs.

        assuming if header does not match original first parsing something was cleaned
        each individual methods applied are tested individually
        """
        test_dir = Path("testData/Test")
        test_filenames = ["sample.sng", "sample_churchsongid_caps.sng"]

        songs = [SngFile(test_dir / test_filename) for test_filename in test_filenames]
        test_df = pd.DataFrame(songs, columns=["SngFile"])

        cleaned_df = clean_all_songs(df_sng=test_df)
        expected_songs = [
            SngFile(test_dir / test_filename) for test_filename in test_filenames
        ]

        self.assertNotEqual(expected_songs[0], cleaned_df.iloc[0]["SngFile"])
        self.assertNotEqual(expected_songs[1], cleaned_df.iloc[1]["SngFile"])


if __name__ == "__main__":
    unittest.main()
