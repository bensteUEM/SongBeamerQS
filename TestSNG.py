import logging
import os.path
import unittest

from SNG_File import SNG_File


class TestSNG(unittest.TestCase):
    """
    Test Class for SNG related class and methods
    """
    maxDiff = None

    def __init__(self, *args, **kwargs):
        """
        Preparation of Test object
        :param args:
        :param kwargs:
        """
        super(TestSNG, self).__init__(*args, **kwargs)
        self.song = SNG_File("./testData/022 Die Liebe des Retters.sng")

    def test_filename(self):
        """
        Checks if song contains correct filename and path information
        :return:
        """
        path = "./testData/"
        filename = "022 Die Liebe des Retters.sng"
        self.assertEqual(self.song.filename, "022 Die Liebe des Retters.sng")
        self.assertEqual(self.song.path, os.path.dirname(path))

    def test_header_title(self):
        """
        Checks if param Title is correctly parsed

        Test file that checks that no title is read with sample file which does not contain title line
        Will also fail if empty line handling does not exist
        :return:
        """
        self.song.parse_param("#Title=Die Liebe des Retters")
        target = {'Title': 'Die Liebe des Retters'}
        self.assertEqual(self.song.header["Title"], target["Title"])

        song = SNG_File('./testData/022 Die Liebe des Retters_missing_title.sng')
        self.assertNotIn('Title', song.header)

    def test_header_all(self):
        """
        Checks if all params of the test file are correctly parsed
        :return:
        """
        target = {
            'LangCount': '1',
            'Title': 'Die Liebe des Retters',
            'Author': 'Mia Friesen, Stefan Schöpfle',
            'CCLI': '6020110',
            '(c)': '2010 Outbreakband Musik (Verwaltet von Gerth Medien)',
            'Editor': 'SongBeamer 5.15',
            'Version': '3',
            'VerseOrder': 'Intro,Strophe 1,Strophe 2,Refrain 1,Refrain 1,Strophe 2,Refrain 1,Refrain 1,Bridge,Bridge,Bridge,Bridge,Intro,Refrain 1,Refrain 1,Refrain 1,Refrain 1,STOP',
            'BackgroundImage': 'Menschen\himmel-und-erde.jpg',
            'Songbook': 'FJ5/022',
            'Comments': '77u/Rm9saWVucmVpaGVuZm9sZ2UgbmFjaCBvZmZpemllbGxlciBBdWZuYWhtZSwgaW4gQmFpZXJzYnJvbm4gZ2dmLiBrw7xyemVyIHVuZCBtaXQgTXVzaWt0ZWFtIGFienVzdGltbWVu',
            'ChurchSongID': 'FJ5/022'
        }
        self.assertDictEqual(self.song.header, target)

    def test_header_space(self):
        """
        Test that checks that header spaces at beginning and end are omitted
        while others still exists and might invalidate headers params
        :return:
        """
        song = SNG_File('./testData/022 Die Liebe des Retters_space_header.sng')
        self.assertIn('LangCount', song.header)
        self.assertEqual('1', song.header['LangCount'])
        self.assertIn('Title', song.header)
        self.assertIn('Author', song.header)
        self.assertNotIn('CCLI', song.header)

    def test_header_title(self):
        """
        Checks that header title is fixed for one sample file
        :return:
        """
        song = SNG_File('./testData/022 Die Liebe des Retters_missing_title.sng')
        self.assertNotIn("Title", song.header)
        song.fix_title()
        self.assertEqual("Die Liebe des Retters_missing_title", song.header['Title'])

    def test_header_complete(self):
        """
        Checks that all required headers are available for the song
        using 3 samples
        * with missing title
        * complete set
        * file with translation
        Info should be logged in case of missing headers
        :return:
        """
        song = SNG_File('./testData/022 Die Liebe des Retters_missing_title.sng')
        with self.assertLogs(level='INFO') as cm:
            song.contains_required_headers()
        self.assertEqual(cm.output, ['INFO:root:Missing required headers in (022 Die Liebe des '
                                     "Retters_missing_title.sng) ['Title']"])

        song = SNG_File('./testData/022 Die Liebe des Retters.sng')
        check = song.contains_required_headers()
        self.assertEqual(True, check[0], song.filename + ' should contain ' + str(check[1]))

        song = SNG_File('./testData/Holy Holy Holy.sng')
        song.fix_songbook()
        check = song.contains_required_headers()  # TODO check that ChurchSong can be NULL in SNG without removal
        self.assertEqual(True, check[0], song.filename + ' should contain ' + str(check[1]))

    def test_header_songbook(self):
        """
        Checks that sng prefix is correctly used when reparing songbook prefix
        1. test prefix
        2. EG prefix with special number xxx.x
        3. no prefix
        4. testprefix without number should trigger warning
        :return:
        """
        song = SNG_File('./testData/618 Wenn die Last der Welt.sng', songbook_prefix="test")
        song.fix_songbook()
        self.assertEqual("test 618", song.header['Songbook'])
        self.assertEqual("test 618", song.header['ChurchSongID'])

        song = SNG_File('./testData/571.1 Ubi caritas et amor - Wo die Liebe wohnt.sng', songbook_prefix="EG")
        song.fix_songbook()
        self.assertEqual("EG 571.1", song.header['Songbook'])

        song = SNG_File('./testData/Holy Holy Holy.sng')
        song.fix_songbook()
        self.assertEqual(" ", song.header['Songbook'])

        with self.assertLogs(level='WARNING') as cm:
            song = SNG_File('./testData/Holy Holy Holy.sng', "testprefix")
            song.fix_songbook()
        self.assertEqual(cm.output,
                         ['WARNING:root:Invalid number format in Filename - can\'t fix songbook of ' + song.filename])

    def test_content_empty_block(self):
        """
        Test case with a SNG file that contains and empty block because it ends with ---
        :return:
        """
        song = SNG_File('./testData/618 Wenn die Last der Welt.sng')
        self.assertEqual(len(song.content), 4)

    def test_file_write(self):
        """
        Functions which compares the original file to the one generated after parsing
        :return:
        """
        self.song.write_file("_test", False)

        original_file = open('./testData/022 Die Liebe des Retters.sng', 'r', encoding='iso-8859-1')
        new_file = open('./testData/022 Die Liebe des Retters_test.sng', 'r', encoding='iso-8859-1')

        self.assertListEqual(
            list(original_file),
            list(new_file)
        )

        original_file.close()
        new_file.close()

    def test_content(self):
        """
        Checks if all Markers from the Demo Set are detected
        Test to check if a content without proper label is replaced as unknown and custom content header is read
        :return:
        """
        target = ['Intro', 'Strophe 1', 'Refrain 1', 'Strophe 2', 'Bridge']
        markers = self.song.content.keys()

        for marker in markers:
            self.assertIn(marker, target)

        # Special Exceptions
        song = SNG_File('./testData/022 Die Liebe des Retters_missing_block.sng')
        target = ['Unknown', '$$M=Testnameblock', 'Refrain 1', 'Strophe 2', 'Bridge']
        markers = song.content.keys()

        for marker in markers:
            self.assertIn(marker, target)

        self.assertIn("Testnameblock", song.content['$$M=Testnameblock'][0])


if __name__ == '__main__':
    unittest.main()
