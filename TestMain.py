import logging
import unittest

import pandas
import pandas as pd
from ChurchToolsApi import ChurchToolsApi

import SNG_DEFAULTS
from main import check_ct_song_categories_exist_as_folder, parse_sng_from_directory, read_baiersbronn_songs_to_df, \
    validate_all_songbook, generate_songbook_column


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
        songs_df = read_baiersbronn_songs_to_df()
        filter = songs_df["path"] \
                 == '/home/benste/Documents/Kirchengemeinde Baiersbronn/Beamer/Songbeamer - Songs/EG Lieder'
        eg_songs_df = songs_df[filter]
        result = validate_all_songbook(eg_songs_df, fix=True)
        generate_songbook_column(eg_songs_df)
        self.assertEqual(len(eg_songs_df['Songbook']), eg_songs_df['Songbook'].str.startswith('EG').sum())

    def test_validate_songbook_special_cases(self):
        """
        Checks the application of the validate_header_songbook method in main.py with specific problematic examples
        :return:
        """

        special_files = ['709 Herr, sei nicht ferne.sng']
        song = parse_sng_from_directory('./testData', 'EG', special_files)[0]
        self.assertEqual(special_files[0], song.filename)

        #Special Case for Regex Testing
        special_files = ['548 Kreuz auf das ich schaue.sng']
        song = parse_sng_from_directory('./testData', 'EG', special_files)[0]
        song_df = pd.DataFrame([song], columns=["SngFile"])
        self.assertEqual('Wwdlp 170 & EG 548', song_df['SngFile'].iloc[0].header['Songbook'])
        validate_all_songbook(song_df, fix=True)
        generate_songbook_column(song_df)
        self.assertEqual('EG 548', song_df['SngFile'].iloc[0].header['Songbook'])
        self.assertEqual(len(song_df['Songbook']), song_df['Songbook'].str.startswith('EG').sum())


        # TODO songbook fixing fails with (76, 'Wwdlp 170 & EG 548') from Baiersbronn dir

        # TODO Songbook=EG 709 - Psalm 22 I -> is marked as autocorrect ...

        # TODO add test for match Regex for EG Psalm in ChurchSongId?
