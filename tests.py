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

    def test_params_title(self):
        """
        Checks if param Title is correctly parsed
        :return:
        """
        self.song.parse_param("#Title=Die Liebe des Retters")
        target = {'Title': 'Die Liebe des Retters'}
        self.assertEqual(self.song.header["Title"], target["Title"])

    def test_params_all(self):
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

    def test_file_write(self):
        """
        Functions which compares the original file to the one generated after parsing
        :return:
        """
        self.song.write_file("_test")

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

    def test_missing_title(self):
        """
        Test file that checks that no title is read with sample file which does not contain title line
        Will also fail if empty line handling does not exist
        :return:
        """
        song = SNG_File('./testData/022 Die Liebe des Retters_missing_title.sng')
        self.assertNotIn('Title', song.header)

    def test_space_header(self):
        """
        Test that checks that header spaces at beginning and end are omitted
        while others still exists and might invalidate headers params
        :return:
        """
        song = SNG_File('./testData/022 Die Liebe des Retters_space_header.sng')
        self.assertIn('LangCount', song.header)
        self.assertEquals('1', song.header['LangCount'])
        self.assertIn('Title', song.header)
        self.assertIn('Author', song.header)
        self.assertNotIn('CCLI', song.header)


if __name__ == '__main__':
    unittest.main()
