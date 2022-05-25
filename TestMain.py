import logging
import unittest

import pandas
from ChurchToolsApi import ChurchToolsApi

import SNG_DEFAULTS
from main import check_ct_song_categories_exist_as_folder


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
