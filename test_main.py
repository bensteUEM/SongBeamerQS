import logging
import os
import unittest

import pandas
import pandas as pd
from ChurchToolsApi import ChurchToolsApi

import SNG_DEFAULTS
from main import check_ct_song_categories_exist_as_folder, parse_sng_from_directory, read_baiersbronn_songs_to_df, \
    generate_songbook_column, get_ct_songs_as_df, validate_ct_songs_exist_locally_by_name_and_category, \
    clean_all_songs, download_missing_online_songs


class TestSNG(unittest.TestCase):
    """
    Test Class for SNG related class and methods
    """

    def __init__(self, *args, **kwargs):
        """
        Preparation of Test object
        :param args:
        :param kwargs:
        """
        super(TestSNG, self).__init__(*args, **kwargs)

        logging.basicConfig(filename='logs/TestMain.log', encoding='utf-8',
                            format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
                            level=logging.DEBUG)
        logging.info("Excecuting Test Main RUN")

    def test_ct_categories_as_local_folder(self):
        api = ChurchToolsApi('https://elkw1610.krz.tools')
        songs = api.get_songs()
        df_ct = pandas.json_normalize(songs)

        self.assertTrue(check_ct_song_categories_exist_as_folder(list(df_ct['category.name'].unique()),
                                                                 SNG_DEFAULTS.KnownDirectory))

    def test_eg_with_songbook_prefix(self):
        """
        Check that all songs in EG Lieder does have EG Songbook prefix
        :return:
        """
        songs_df = read_baiersbronn_songs_to_df()
        filter1 = songs_df["path"] \
                  == '/home/benste/Documents/Kirchengemeinde Baiersbronn/Beamer/Songbeamer - Songs/EG Lieder'
        filter2 = songs_df["path"] \
                  == '/home/benste/Documents/Kirchengemeinde Baiersbronn/Beamer/Songbeamer - Songs/EG Psalmen & Sonstiges'

        songs_df['SngFile'].apply(lambda x: x.validate_header_songbook(True))
        eg_songs_df = songs_df[filter1 | filter2]
        generate_songbook_column(songs_df)
        self.assertEqual(len(eg_songs_df['SngFile']), songs_df['Songbook'].str.startswith('EG').sum())

    def test_validate_songbook_special_cases(self):
        """
        Checks the application of the validate_header_songbook method in main.py with specific problematic examples
        :return:
        """

        special_files = ['709 Herr, sei nicht ferne.sng']
        song = parse_sng_from_directory('./testData/Psalm', 'EG', special_files)[0]
        self.assertEqual(special_files[0], song.filename)

        # Special Case for Regex Testing
        special_files = ['548 Kreuz auf das ich schaue.sng']
        song = parse_sng_from_directory('./testData', 'EG', special_files)[0]
        song_df = pd.DataFrame([song], columns=["SngFile"])
        self.assertEqual('Wwdlp 170 & EG 548', song_df['SngFile'].iloc[0].header['Songbook'])
        result = song_df['SngFile'].apply(lambda x: x.validate_header_songbook(False))
        self.assertEqual(result.sum(), 0, 'Should have no valid entries')
        result = song_df['SngFile'].apply(lambda x: x.validate_header_songbook(True))
        self.assertEqual(result.sum(), 1, 'Should have one valid entry')
        result = generate_songbook_column(song_df)
        self.assertEqual('EG 548', song_df['SngFile'].iloc[0].header['Songbook'])
        self.assertEqual(len(song_df['Songbook']), song_df['Songbook'].str.startswith('EG').sum())

        # Special Case for Regex Testing - Songbook=EG 709 - Psalm 22 I -> is marked as autocorrect ...
        special_files = ['709 Herr, sei nicht ferne.sng']
        song = parse_sng_from_directory('./testData/Psalm', 'EG', special_files)[0]
        song_df = pd.DataFrame([song], columns=["SngFile"])
        self.assertEqual('EG 709 - Psalm 22 I', song_df['SngFile'].iloc[0].header['Songbook'])
        result = song_df['SngFile'].apply(lambda x: x.validate_header_songbook(False))
        self.assertEqual(result.sum(), 1, 'Should have one valid entry')

    def test_validate_comment_special_case(self):
        """
        Test method which validates one specific file which had differences while parsing
        :return:
        """
        special_files = ['Psalm 104_Stierlen.sng']
        song = parse_sng_from_directory('./testData', '', special_files)[0]
        expected = '77u/RW50c3ByaWNodCBuaWNodCBkZXIgVmVyc2lvbiBhdXMgZGVtIEVHIQ=='
        self.assertEqual(expected, song.header['Comments'])

    def test_missing_song(self):
        """
        Checking why Hintergrundmusik fails
        :return:
        """
        songs_temp = parse_sng_from_directory(SNG_DEFAULTS.KnownDirectory + 'Hintergrundmusik', '',
                                              ['The Knowledge of Good and Evil.sng'])
        songs_temp = read_baiersbronn_songs_to_df()

        from ChurchToolsApi import ChurchToolsApi
        api = ChurchToolsApi('https://elkw1610.krz.tools')

        df_ct = get_ct_songs_as_df(api)
        df_ct = df_ct[df_ct['id'] == 204]

        df_sng = pd.DataFrame(songs_temp, columns=["SngFile"])
        for index, value in df_sng['SngFile'].items():
            df_sng.loc[(index, 'filename')] = value.filename
            df_sng.loc[(index, 'path')] = value.path

        compare = validate_ct_songs_exist_locally_by_name_and_category(df_ct, df_sng)
        self.assertEqual(compare['_merge'][0], 'both')

        clean_all_songs(df_sng)
        compare = validate_ct_songs_exist_locally_by_name_and_category(df_ct, df_sng)
        self.assertEqual(compare['_merge'][0], 'both')

    def test_emptied_song(self):
        """
        Test that checks on FJ 3 - 238 because it was emptied during execution even though backup did have content
        Issue was encoding UTF8 - needed to save song again to correct encoding - added ERROR logging for song parsing
        :return:
        """

        songs_temp = parse_sng_from_directory(SNG_DEFAULTS.KnownDirectory + 'Feiert Jesus 3',
                                              'FJ3', ['238 Der Herr segne dich.sng'])
        self.assertIn('Refrain', songs_temp[0].content.keys())
        songs_temp = read_baiersbronn_songs_to_df()

    def test_add_id_to_local_song_if_available_in_ct(self):  # TODO #13
        self.assertFalse(True, 'Not Implemented')

    def test_download_missing_online_songs(self):
        """
        ELKW1610.krz.tools specific test case for the named function (using 2 specific song IDs)
        deletes EG 002 if exists locally
        Reads one local sng file (EG 001)
        tries to detect that EG002 from CT is missing
        downloads the file
        checks if download success
        deletes file
        :return:
        """

        songs_temp = []
        dirname = 'testData/'
        dirprefix = 'TEST'

        test2name = '002 Er ist die rechte Freudensonn.sng'
        test2path = dirname + '/EG Lieder/' + test2name

        exists = os.path.exists(test2path)
        if exists:
            os.remove(test2path)

        songs = parse_sng_from_directory(dirname, dirprefix)

        for key, value in SNG_DEFAULTS.KnownFolderWithPrefix.items():
            dirname = './testData/' + key
            if not os.path.exists(dirname):
                continue
            dirprefix = value
            songs_temp.extend(parse_sng_from_directory(dirname, dirprefix))

        df_sng_test = pd.DataFrame(songs_temp, columns=["SngFile"])
        for index, value in df_sng_test['SngFile'].items():
            df_sng_test.loc[(index, 'filename')] = value.filename
            df_sng_test.loc[(index, 'path')] = value.path

        api = ChurchToolsApi('https://elkw1610.krz.tools')
        ct_songs = [api.get_songs(song_id=762), api.get_songs(song_id=1113)]
        df_ct_test = pd.json_normalize(ct_songs)

        result = download_missing_online_songs(df_sng_test, df_ct_test, api)
        self.assertTrue(result)

        exists = os.path.exists(test2path)
        self.assertTrue(exists)
        os.remove(test2path)

    def test_upload_new_local_songs_and_generate_ct_id(self):  # TODO #15
        self.assertFalse(True, 'Not Implemented')

    def test_upload_local_songs_by_id(self):
        self.assertFalse(True, 'Not Implemented')  # TODO #14
