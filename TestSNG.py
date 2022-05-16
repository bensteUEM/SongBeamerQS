import logging
import os.path
import re
import unittest

from SngFile import SngFile


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

        logging.basicConfig(filename='logs/TestSNG.log', encoding='utf-8',
                            format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
                            level=logging.DEBUG)
        logging.info("Excecuting Tests RUN")

    def test_file_name(self):
        """
        Checks if song contains correct filename and path information
        :return:
        """
        path = "./testData/"
        filename = "022 Die Liebe des Retters.sng"
        song = SngFile(path + filename)
        self.assertEqual(song.filename, filename)
        self.assertEqual(song.path, os.path.dirname(path))

    def test_header_title_parse(self):
        """
        Checks if param Title is correctly parsed

        Test file that checks that no title is read with sample file which does not contain title line
        Will also fail if empty line handling does not exist
        :return:
        """

        song = SngFile("./testData/022 Die Liebe des Retters.sng")
        song.parse_param("#Title=Die Liebe des Retters")

        target = {'Title': 'Die Liebe des Retters'}
        self.assertEqual(song.header["Title"], target["Title"])

        song2 = SngFile('./testData/022 Die Liebe des Retters_missing_title.sng')
        self.assertNotIn('Title', song2.header)

    def test_header_title_fix(self):
        """
        Checks that header title is fixed for one sample file
        :return:
        """
        song = SngFile('./testData/022 Die Liebe des Retters_missing_title.sng')
        self.assertNotIn("Title", song.header)
        song.fix_title()
        self.assertEqual("Die Liebe des Retters_missing_title", song.header['Title'])

    def test_header_all(self):
        """
        Checks if all params of the test file are correctly parsed
        Because of datatype Verse Order is checked first
        Rest of headers are compared to dict
        :return:
        """
        song = SngFile("./testData/022 Die Liebe des Retters.sng")

        target_verse_order = 'Intro,Strophe 1,Strophe 2,Refrain 1,Refrain 1,Strophe 2,Refrain 1,Refrain 1,' + \
                             'Bridge,Bridge,Bridge,Bridge,Intro,Refrain 1,Refrain 1,Refrain 1,Refrain 1,STOP'
        target_verse_order = target_verse_order.split(",")

        self.assertEqual(song.header["VerseOrder"], target_verse_order)

        song.header.pop("VerseOrder")
        target = {
            'LangCount': '1',
            'Title': 'Die Liebe des Retters',
            'Author': 'Mia Friesen, Stefan Schöpfle',
            'CCLI': '6020110',
            '(c)': '2010 Outbreakband Musik (Verwaltet von Gerth Medien)',
            'Editor': 'SongBeamer 5.15',
            'Version': '3',
            'BackgroundImage': r'Menschen\himmel-und-erde.jpg',
            'Songbook': 'FJ5/022',
            'Comments': '77u/Rm9saWVucmVpaGVuZm9sZ2UgbmFjaCBvZmZpemllbGxlciBBdWZuYWhtZSwgaW4gQmFpZXJzYnJvb' +
                        'm4gZ2dmLiBrw7xyemVyIHVuZCBtaXQgTXVzaWt0ZWFtIGFienVzdGltbWVu',
            'ChurchSongID': 'FJ5/022'
        }
        self.assertDictEqual(song.header, target)

    def test_header_space(self):
        """
        Test that checks that header spaces at beginning and end are omitted
        while others still exists and might invalidate headers params
        :return:
        """
        song = SngFile('./testData/022 Die Liebe des Retters_space_header.sng')
        self.assertIn('LangCount', song.header)
        self.assertEqual('1', song.header['LangCount'])
        self.assertIn('Title', song.header)
        self.assertIn('Author', song.header)
        self.assertNotIn('CCLI', song.header)

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
        song = SngFile('./testData/022 Die Liebe des Retters_missing_title.sng')
        with self.assertLogs(level='WARNING') as cm:
            song.contains_required_headers()
        self.assertEqual(cm.output, ['WARNING:root:Missing required headers in (022 Die Liebe des '
                                     "Retters_missing_title.sng) ['Title']"])

        song = SngFile('./testData/022 Die Liebe des Retters.sng')
        check = song.contains_required_headers()
        self.assertEqual(True, check[0], song.filename + ' should contain ' + str(check[1]))

        song = SngFile('./testData/Holy Holy Holy.sng')
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
        song = SngFile('./testData/618 Wenn die Last der Welt.sng', songbook_prefix="test")
        song.fix_songbook()
        self.assertEqual("test 618", song.header['Songbook'])
        self.assertEqual("test 618", song.header['ChurchSongID'])

        song = SngFile('./testData/571.1 Ubi caritas et amor - Wo die Liebe wohnt.sng', songbook_prefix="EG")
        song.fix_songbook()
        self.assertEqual("EG 571.1", song.header['Songbook'])

        song = SngFile('./testData/Holy Holy Holy.sng')
        song.fix_songbook()
        self.assertEqual(" ", song.header['Songbook'])

        with self.assertLogs(level='WARNING') as cm:
            song = SngFile('./testData/Holy Holy Holy.sng', "test")
            song.fix_songbook()
        self.assertEqual(cm.output,
                         ['WARNING:root:Invalid number format in Filename - can\'t fix songbook of ' + song.filename])

    def test_header_church_song_id_caps(self):
        """
        Test that checks for incorrect capitalization in ChurchSongID and it's autocorrect
        Corrected Songbook 085 O Haupt voll Blut und Wunden.sng - used "ChurchSongId instead of ChurchSongID"
        :return:
        """

        song = SngFile('./testData/085 O Haupt voll Blut und Wunden.sng', "EG")
        self.assertNotIn("ChurchSongID", song.header.keys())
        song.fix_header_church_song_id_caps()
        self.assertNotIn("ChurchSongId", song.header.keys())
        self.assertEqual(song.header["ChurchSongID"], "EG 085")

    def test_content_empty_block(self):
        """
        Test case with a SNG file that contains and empty block because it ends with ---
        :return:
        """
        song = SngFile('./testData/618 Wenn die Last der Welt.sng')
        self.assertEqual(len(song.content), 4)

    def test_file_write(self):
        """
        Functions which compares the original file to the one generated after parsing
        :return:
        """
        song = SngFile("./testData/022 Die Liebe des Retters.sng")
        song.write_file("_test")

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
        song = SngFile("./testData/022 Die Liebe des Retters.sng")
        target = ['Intro', 'Strophe 1', 'Refrain 1', 'Strophe 2', 'Bridge']
        markers = song.content.keys()

        for marker in markers:
            self.assertIn(marker, target)

        # Special Exceptions
        song2 = SngFile('./testData/022 Die Liebe des Retters_missing_block.sng')
        target = ['Unknown', '$$M=Testnameblock', 'Refrain 1', 'Strophe 2', 'Bridge']
        markers = song2.content.keys()

        for marker in markers:
            self.assertIn(marker, target)

        self.assertIn("Testnameblock", song2.content['$$M=Testnameblock'][0])

    def test_content_missing_block(self):
        """
        Checks that a file which does not have any section headers can be read without error
        :return:
        """
        song = SngFile('./testData/764 Test Ohne Versmarker.sng')

        self.assertEqual(len(song.content.keys()), 1)
        self.assertEqual(len(song.content["Unknown"]), 1 + 5)
        self.assertEqual(len(song.content["Unknown"][5]), 2)
        # TODO complete test case for missing block check

    def test_file_file_encoding(self):
        """
        Checks that errors are logged for files with issues while parsing
        test file uses wrong encoding therefore doesn't have a --- dividing header and content
        :return:
        """

        with self.assertLogs(level='ERROR') as cm:
            song = SngFile('./testData/726 Psalm 047.sng')
            self.assertEqual(len(song.content), 0)

        self.assertEqual(cm.output,
                         [
                             'ERROR:root:Something is wrong with the line ï»¿#LangCount=2' +
                             ' of file ./testData/726 Psalm 047.sng'
                         ])

    def test_file_broken_encoding_repaired(self):
        """
        Checks that errrors are logged for sample file which is fixed in encoding
        :return:
        """

        song = SngFile('./testData/726 Psalm 047_fixed.sng')
        self.assertEqual(song.filename, '726 Psalm 047_fixed.sng')

    def test_file_short(self):
        """
        Checks a specific SNG file which contains a header only and no content
        :return:
        """

        song = SngFile('./testData/Lizenz_Lied.sng')
        self.assertEqual(song.filename, 'Lizenz_Lied.sng')

    def test_header_EG_Psalm_special(self):
        """
        Test for debugging special Psalms which might not follow ChurchSongID conventions
        e.g. 709 Herr, sei nicht ferne.sng
        :return:
        """
        song = SngFile('./testData/709 Herr, sei nicht ferne.sng', "EG")
        self.assertEqual(song.header["Songbook"], "EG 709 - Psalm 22 I")

        songbook_regex = r"^(Wwdlp \d{3})|(FJ([1-5])\/\d{3})|(EG \d{3}(.\d{1,2})?(( - Psalm )\d{1,3})?( .{1,3})?)$"
        self.assertTrue(re.fullmatch(songbook_regex, song.header["Songbook"]))

    def test_header_EG_Psalm_quality_checks(self):
        """
        Test that checks for auto warning on correction of Psalms in EG
        :return:
        """
        # Test Warning for Psalms
        song = SngFile('./testData/726 Psalm 047.sng', 'EG')
        self.assertNotIn("ChurchSongID", song.header.keys())

        with self.assertLogs(level='WARNING') as cm:
            song.fix_songbook()

        self.assertEqual(cm.output,
                         ['WARNING:root:EG Psalm "726 Psalm 047.sng" can not be auto corrected - please adjust manually'
                          ])
        # TODO continue HERE - #Songbook=EG 709 - Psalm 22 I -> is marked as autocorrect ...

        # TODO add test for match Regex for EG Psalm in ChurchSongId?

        # TODO Add test for language marker validation in EG psalms

        # TODO Add test background image validation for EG Psalms

        # TODO Add test check for EG Psalms that #bible header is present

    def test_content_reformat_slide_4_lines(self):
        """
        Tests specific test file to contain issues before fixing
        Fixes file with fix content slides of 4
        Tests result to contain known blocks, keep Pre Chorus with 2 lines, ans split Chorus to more slides
        Tests that no single slide has more than 4 lines
        :return:
        """
        song = SngFile('./testData/079 Höher_reformat.sng')

        self.assertFalse(all([len(block[1][1]) <= 4 for block in song.content.items()]),
                         'No slides contain more than 4 lines before fixing')

        self.assertEqual(len(song.content["Pre-Chorus"][1]), 2, "Pre Chorus before fixing")
        self.assertEqual(len(song.content["Chorus 1"][1]), 6, "Chorus before fixing")

        song.fix_content_slides_number_of_lines()

        self.assertTrue(all([len(block[1][1]) <= 4 for block in song.content.items()]),
                        'Some slides contain more than 4 lines')
        self.assertEqual(len(song.content["Pre-Chorus"][1]), 2, "Pre Chorus after fixing")
        self.assertEqual(len(song.content["Chorus 1"][1]), 4, "# Slides for Chorus after fixing")
        self.assertEqual(len(song.content["Chorus 1"]), 3, "# Slides for Chorus after fixing")

    def test_header_VerseOrder_complete(self):
        song = SngFile('./testData/022 Die Liebe des Retters_missing_block.sng')

        verse_order_text = 'Intro,Strophe 1,Strophe 2,Refrain 1,Refrain 1,Strophe 2,Refrain 1,Refrain 1,Bridge,' + \
                           'Bridge,Bridge,Bridge,Intro,Refrain 1,Refrain 1,Refrain 1,Refrain 1,STOP'
        verse_order = verse_order_text.split(",")
        verse_blocks = 'Unknown,$$M=Testnameblock,Refrain 1,Strophe 2,Bridge'.split(',')

        # 1. Check initial test file state
        self.assertEqual(song.header["VerseOrder"], verse_order)
        self.assertEqual(list(song.content.keys()), verse_blocks)

        # 2. Check that Verse Order shows as incomplete
        with self.assertLogs(level='WARNING') as cm:
            self.assertFalse(song.contains_complete_verse_order())

        self.assertEqual(cm.output, ["WARNING:root:Verse Order and Blocks don't match in " +
                                     "022 Die Liebe des Retters_missing_block.sng"
                                     ])

        # Failsafe with correct file
        song = SngFile('./testData/079 Höher_reformat.sng')
        self.assertTrue(song.contains_complete_verse_order())

    def test_content_Intro_Slide(self):
        song = SngFile('./testData/079 Höher_reformat.sng')
        raise NotImplementedError()  # TODO implement test and required methods

    def test_content_STOP_VerseOrder(self):
        song = SngFile('./testData/079 Höher_reformat.sng')
        raise NotImplementedError()  # TODO implement test and required methods


if __name__ == '__main__':
    unittest.main()
