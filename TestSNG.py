import logging
import os.path
import re
import unittest

from SngFile import SngFile, contains_songbook_prefix


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
        logging.info("Excecuting TestSNG RUN")

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
        song.validate_header_title(fix=False)
        self.assertNotIn("Title", song.header)
        song.validate_header_title(fix=True)
        self.assertEqual("Die Liebe des Retters_missing_title", song.header['Title'])

    def test_header_title_special(self):
        """
        Checks that header title is not fixed for sample file
        which had issues on log
        :return:
        """

        song = SngFile('./testData/Psalm/751 Psalm 130.sng')
        self.assertIn("Title", song.header)
        self.assertEqual("Ich harre des Herrn, denn bei ihm ist die Gnade", song.header['Title'])
        song.validate_header_title(fix=True)
        self.assertEqual("Ich harre des Herrn, denn bei ihm ist die Gnade", song.header['Title'])

    def test_header_title_special2(self):
        """
        Checks that header title is not fixed for sample file which had issues in log
        which had issues on log
        :return:
        """

        # 2022-06-03 10:56:20,370 root       DEBUG    Fixed title to (Psalm NGÜ) in Psalm 23 NGÜ.sng
        # -> Number should not be ignored if no SongPrefix
        song = SngFile('./testData/Psalm 23 NGÜ.sng')
        self.assertIn("Title", song.header)
        self.assertEqual("Psalm 23 NGÜ", song.header["Title"])
        song.validate_header_title(fix=True)
        self.assertEqual("Psalm 23 NGÜ", song.header["Title"])

        # 2022-06-03 10:56:20,370 root       DEBUG    Song without a Title in Header:Gesegneten Sonntag.sng
        # 2022-06-03 10:56:20,370 root       DEBUG    Fixed title to (Sonntag) in Gesegneten Sonntag.sng
        # Fixed by correcting contains_songbook_prefix() method
        song = SngFile('./testData/Gesegneten Sonntag.sng')
        self.assertNotIn("Title", song.header)
        song.validate_header_title(fix=True)
        self.assertEqual("Gesegneten Sonntag", song.header["Title"])

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
            'Melody': 'TESTDATA',
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
        song = SngFile('./testData/022 Die Liebe des Retters_missing_title.sng', 'FJ/5')
        with self.assertLogs(level='WARNING') as cm:
            song.validate_headers()
        self.assertEqual(cm.output, ['WARNING:root:Missing required headers in (022 Die Liebe des '
                                     "Retters_missing_title.sng) ['Title']"])

        song = SngFile('./testData/022 Die Liebe des Retters.sng', 'FJ/5')
        check = song.validate_headers()
        self.assertTrue(check, song.filename + ' should contain other headers - check log')

        song = SngFile('./testData/Holy Holy Holy.sng')
        song.fix_songbook()
        check = song.validate_headers()
        self.assertTrue(check, song.filename + ' should contain other headers - check log')

        song = SngFile('./testData/Psalm/709 Herr, sei nicht ferne.sng', 'EG')
        with self.assertLogs(level='WARNING') as cm:
            song.validate_headers()
        self.assertEqual(cm.output,
                         ["WARNING:root:Missing required headers in (709 Herr, sei nicht ferne.sng) "
                          "['Author', 'Melody', 'CCLI', 'Translation']"])

        song = SngFile('./testData/Psalm/751 Psalm 130.sng', 'EG')
        with self.assertLogs(level='WARNING') as cm:
            song.validate_headers()
        self.assertEqual(cm.output,
                         ["WARNING:root:Missing required headers in (751 Psalm 130.sng) "
                          "['Author', 'Melody', '(c)', 'CCLI', 'VerseOrder', 'Bible']"])

    def test_header_illegal_removed(self):
        """
        Tests that all illegal headers are removed
        :return:
        """
        song = SngFile('./testData/Psalm/709 Herr, sei nicht ferne.sng', 'EG')
        self.assertIn('FontSize', song.header.keys())
        song.validate_headers_illegal_removed(fix=False)
        self.assertIn('FontSize', song.header.keys())
        song.validate_headers_illegal_removed(fix=True)
        self.assertNotIn('FontSize', song.header.keys())

    def test_header_songbook(self):
        """
        Checks that sng prefix is correctly used when reparing songbook prefix
        1. test prefix
        2. EG prefix with special number xxx.x
        3. no prefix
        4. testprefix without number should trigger warning
        5. not correcting ' '  songbook
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

        with self.assertLogs(level=logging.DEBUG) as cm:
            song = SngFile('./testData/Gesegneten Sonntag.sng')
            self.assertEqual(" ", song.header['Songbook'])
            song.fix_songbook()
            self.assertEqual(" ", song.header['Songbook'])
        self.assertEqual(cm.output,
                         ['DEBUG:root:Parsing content for: Gesegneten Sonntag.sng'])

    def test_header_songbook_special(self):
        """
        Test checking special cases discovered in logging while programming

        :return:
        """

        # The file should already have correct ChurchSongID but did raise an error on logging
        song = SngFile('./testData/Psalm/752 Psalm 134.sng', "EG")
        self.assertEqual('EG 752 - Psalm 134', song.header["ChurchSongID"])
        self.assertEqual('EG 752 - Psalm 134', song.header["Songbook"])

        with self.assertNoLogs(level='WARNING'):
            song.validate_header_songbook(fix=False)
            song.validate_header_songbook(fix=True)

        self.assertEqual('EG 752 - Psalm 134', song.header["ChurchSongID"])
        self.assertEqual('EG 752 - Psalm 134', song.header["Songbook"])

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

    def test_validate_header_background(self):
        """
        Test case for background images
        1. regular with picture
        2. regular without picture
        3. Psalm with no picture
        4. Psalm with wrong picture
        5. Psalm with correct picture
        :return:
        """
        # Case 1. regular with picture
        song = SngFile('./testData/085 O Haupt voll Blut und Wunden.sng', "EG")
        self.assertTrue(song.validate_header_background(fix=False))

        # Case 2. regular without picture

        song = SngFile('./testData/001 Macht Hoch die Tuer.sng', "EG")
        with self.assertLogs(level='DEBUG') as cm:
            self.assertFalse(song.validate_header_background(fix=False))
        self.assertEqual(cm.output, ['DEBUG:root:No Background in (001 Macht Hoch die Tuer.sng)'])

        song = SngFile('./testData/001 Macht Hoch die Tuer.sng', "EG")
        with self.assertLogs(level='WARN') as cm:
            self.assertFalse(song.validate_header_background(fix=True))
        self.assertEqual(cm.output, ["WARNING:root:Can't fix background for (001 Macht Hoch die Tuer.sng)"])

        # Case 3. Psalm with no picture
        song = SngFile('./testData/Psalm/752 Psalm 134.sng', "EG")
        with self.assertLogs(level='DEBUG') as cm:
            self.assertFalse(song.validate_header_background(fix=False))
        self.assertEqual(cm.output, ['DEBUG:root:No Background in (752 Psalm 134.sng)'])

        song = SngFile('./testData/Psalm/752 Psalm 134.sng', "EG")
        with self.assertLogs(level='DEBUG') as cm:
            self.assertTrue(song.validate_header_background(fix=True))
        self.assertEqual(cm.output, ["DEBUG:root:Fixing background for Psalm in (752 Psalm 134.sng)"])

        # Case 4. Psalm with wrong picture
        song = SngFile('./testData/Psalm/751 Psalm 130.sng', "EG")
        with self.assertLogs(level='DEBUG') as cm:
            self.assertFalse(song.validate_header_background(fix=False))
        self.assertEqual(cm.output, ['DEBUG:root:Incorrect background for Psalm in (751 Psalm 130.sng) not fixed'])

        song = SngFile('./testData/Psalm/751 Psalm 130.sng', "EG")
        with self.assertLogs(level='DEBUG') as cm:
            self.assertTrue(song.validate_header_background(fix=True))
        self.assertEqual(cm.output, ["DEBUG:root:Fixing background for Psalm in (751 Psalm 130.sng)"])

        # Case 5. Psalm with correct picture
        song = SngFile('./testData/Psalm/764 Test Ohne Versmarker.sng', "EG")
        with self.assertNoLogs(level='DEBUG'):
            self.assertTrue(song.validate_header_background(fix=False))

        song = SngFile('./testData/Psalm/764 Test Ohne Versmarker.sng', "EG")
        with self.assertNoLogs(level='DEBUG'):
            self.assertTrue(song.validate_header_background(fix=True))

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
        song = SngFile('./testData/Psalm/764 Test Ohne Versmarker.sng')

        self.assertEqual(len(song.content.keys()), 1)
        self.assertEqual(len(song.content["Unknown"]), 1 + 5)
        self.assertEqual(len(song.content["Unknown"][5]), 2)

    def test_file_file_encoding(self):
        """
        Checks that errors are logged for files with issues while parsing
        test file uses wrong encoding therefore doesn't have a --- dividing header and content
        :return:
        """

        with self.assertLogs(level='ERROR') as cm:
            song = SngFile('./testData/Psalm/726 Psalm 047_utf8.sng')
            self.assertEqual(len(song.content), 0)

        self.assertEqual(cm.output,
                         [
                             'ERROR:root:Something is wrong with the line ï»¿#LangCount=2' +
                             ' of file ./testData/Psalm/726 Psalm 047_utf8.sng'
                         ])

    def test_file_broken_encoding_repaired(self):
        """
        Checks that errrors are logged for sample file which is fixed in encoding
        :return:
        """

        song = SngFile('testData/Psalm/726 Psalm 047_utf8.sng')
        self.assertEqual(song.filename, '726 Psalm 047_utf8.sng')

    def test_file_short(self):
        """
        Checks a specific SNG file which contains a header only and no content
        :return:
        """

        song = SngFile('./testData/Lizenz_Lied.sng')
        self.assertEqual(song.filename, 'Lizenz_Lied.sng')

    def test_header_songbook_EG_Psalm_special(self):
        """
        Test for debugging special Psalms which might not follow ChurchSongID conventions
        e.g. 709 Herr, sei nicht ferne.sng
        :return:
        """
        song = SngFile('./testData/Psalm/709 Herr, sei nicht ferne.sng', "EG")
        self.assertEqual(song.header["Songbook"], "EG 709 - Psalm 22 I")

        songbook_regex = r"^(Wwdlp \d{3})|(FJ([1-5])\/\d{3})|(EG \d{3}(.\d{1,2})?(( - Psalm )\d{1,3})?( .{1,3})?)$"
        self.assertTrue(re.fullmatch(songbook_regex, song.header["Songbook"]))

    def test_header_EG_Psalm_quality_checks(self):
        """
        Test that checks for auto warning on correction of Psalms in EG
        :return:
        """
        # Test Warning for Psalms
        song = SngFile('testData/Psalm/726 Psalm 047_iso-8859-1.sng', 'EG')
        self.assertNotIn("ChurchSongID", song.header.keys())
        with self.assertLogs(level='WARNING') as cm:
            song.fix_songbook()

        self.assertEqual(cm.output,
                         ['WARNING:root:EG Psalm "726 Psalm 047_iso-8859-1.sng"' +
                          ' can not be auto corrected - please adjust manually'])

        song = SngFile('testData/Psalm/726 Psalm 047_iso-8859-1.sng', 'EG')
        self.assertNotIn("ChurchSongID", song.header.keys())

        # TODO Add test for language marker validation in EG psalms

        # Test background image validation for EG Psalms
        self.assertFalse(song.validate_header_background(fix=False))
        self.assertTrue(song.validate_header_background(fix=True))

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

        self.assertFalse(song.validate_content_slides_number_of_lines(fix=False))
        self.assertTrue(song.validate_content_slides_number_of_lines(fix=True))

        self.assertTrue(all([len(block[1][1]) <= 4 for block in song.content.items()]),
                        'Some slides contain more than 4 lines')
        self.assertEqual(len(song.content["Pre-Chorus"][1]), 2, "Pre Chorus after fixing")
        self.assertEqual(len(song.content["Chorus 1"][1]), 4, "# Slides for Chorus after fixing")
        self.assertEqual(len(song.content["Chorus 1"]), 3, "# Slides for Chorus after fixing")

    def test_header_VerseOrder_complete(self):
        """
        Method that checks various cases in regards to VerseOrder existance and fixing
        :return:
        """
        song = SngFile('./testData/022 Die Liebe des Retters_missing_block.sng')

        verse_order_text = 'Intro,Strophe 1,Strophe 2,Refrain 1,Refrain 1,Strophe 2,Refrain 1,Refrain 1,Bridge,' + \
                           'Bridge,Bridge,Bridge,Intro,Refrain 1,Refrain 1,Refrain 1,Refrain 1,STOP'
        verse_order = verse_order_text.split(",")
        verse_blocks = 'Unknown,$$M=Testnameblock,Refrain 1,Strophe 2,Bridge'.split(',')
        verse_order_text_fixed = 'Strophe 2,Refrain 1,Refrain 1,Strophe 2,Refrain 1,Refrain 1,Bridge,Bridge,Bridge,' + \
                                 'Bridge,Refrain 1,Refrain 1,Refrain 1,Refrain 1,STOP,Unknown,Testnameblock'
        verse_order_fixed = verse_order_text_fixed.split(",")

        # 1. Check initial test file state
        self.assertEqual(song.header["VerseOrder"], verse_order)
        self.assertEqual(list(song.content.keys()), verse_blocks)

        # 2. Check that Verse Order shows as incomplete
        with self.assertLogs(level='WARNING') as cm:
            self.assertFalse(song.validate_verse_order_coverage())

        self.assertEqual(cm.output, ["WARNING:root:Verse Order and Blocks don't match in " +
                                     "022 Die Liebe des Retters_missing_block.sng"
                                     ])

        # 3. Check that Verse Order is completed
        song = SngFile('./testData/022 Die Liebe des Retters_missing_block.sng')
        self.assertEqual(song.header["VerseOrder"], verse_order)
        with self.assertNoLogs(level='WARNING'):
            song.validate_verse_order_coverage(fix=True)

        self.assertEqual(song.header["VerseOrder"], verse_order_fixed)

        # Failsafe with correct file
        song = SngFile('./testData/079 Höher_reformat.sng')
        with self.assertNoLogs(level='WARNING'):
            self.assertTrue(song.validate_verse_order_coverage())

    def test_header_verse_order_special(self):
        """
        Test case for special cases occured while running on sample files
        e.g. 375 Dass Jesus siegt bleibt ewig ausgemacht.sng - Warning Verse Order and Blocks don't match
        :return:
        """
        song = SngFile('./testData/375 Dass Jesus siegt bleibt ewig ausgemacht.sng', 'EG')
        with self.assertNoLogs(level='WARNING'):
            self.assertTrue(song.validate_verse_order_coverage())

    def test_generate_verses_from_unknown(self):
        """
        Checks that the song is changed from Intro,Unknown,STOP to Intro,Verse ...
        based on auto detecting 1.2.3. or other numerics or R: at beginning of block
        Also changes respective verse order
        :return:
        """
        song = SngFile('./testData/644 Jesus hat die Kinder lieb.sng', 'EG')
        self.assertEqual(['Intro', 'Unknown', 'Verse 99', 'STOP'], song.header["VerseOrder"])
        song.generate_verses_from_unknown()
        self.assertEqual(['Intro', 'Verse 1', 'Verse 2', 'Refrain', 'Verse 10', 'Verse 99', 'STOP'],
                         song.header["VerseOrder"])

        # TODO optionally add test case for logged warning when new verse already exists in VerseOrder

    def test_header_verse_order_special2(self):
        """
        Test case for special cases occured while running on sample files
        e.g. 098 Korn das in die Erde in den Tod versinkt.sng
        DEBUG    Missing VerseOrder in (098 Korn das in die Erde in den Tod versinkt.sng)
        :return:
        """
        song = SngFile('./testData/098 Korn das in die Erde in den Tod versinkt.sng', 'EG')
        with self.assertLogs(level='WARNING') as cm:
            self.assertFalse(song.validate_verse_order_coverage(fix=False))
        messages = [
            "WARNING:root:Verse Order and Blocks don't match in 098 Korn das in die Erde in den Tod versinkt.sng"]
        self.assertEqual(messages, cm.output)

        with self.assertLogs(level='DEBUG') as cm:
            self.assertTrue(song.validate_verse_order_coverage(fix=True))
        messages = [
            "DEBUG:root:Fixed VerseOrder to ['Strophe 1a', 'Strophe 1b', 'Strophe 2a', 'Strophe 2b', 'Strophe 3a',"
            " 'Strophe 3b'] in (098 Korn das in die Erde in den Tod versinkt.sng)"]
        self.assertEqual(messages, cm.output)

    def test_header_verse_order_special3(self):
        """
        Special Case welcome slide with custom verse headers
        :return:
        """

        song = SngFile('./testData/Herzlich Willkommen.sng', 'EG')
        self.assertEqual(['Intro', 'Variante 1', 'Variante 2', 'Intro', 'STOP'], song.header["VerseOrder"], )
        song.validate_verse_order_coverage(fix=True)
        self.assertEqual(['Intro', 'Variante 1', 'Variante 2', 'Intro', 'STOP'], song.header["VerseOrder"], )

    def test_content_Intro_Slide(self):
        """
        Checks that sample file has no Intro in Verse Order or Blocks and repaired file contains both
        :return:
        """
        song = SngFile('./testData/079 Höher_reformat.sng')
        self.assertNotIn('Intro', song.header["VerseOrder"])
        self.assertNotIn('Intro', song.content.keys())
        song.fix_intro_slide()
        self.assertIn('Intro', song.header["VerseOrder"])
        self.assertIn('Intro', song.content.keys())

    def test_validate_verse_numbers(self):
        """
        Checks whether verse numbers are regular
        """
        song = SngFile('./testData/123 Du bist der Schöpfer des Universums.sng')
        self.assertIn('Refrain 1a', song.header["VerseOrder"])
        self.assertIn('Refrain 1b', song.header["VerseOrder"])

        self.assertFalse(song.validate_verse_numbers())
        self.assertIn('Refrain 1a', song.header["VerseOrder"])
        self.assertIn('Refrain 1b', song.header["VerseOrder"])

        self.assertTrue(song.validate_verse_numbers(fix=True))
        self.assertNotIn('Refrain 1a', song.header["VerseOrder"])
        self.assertNotIn('Refrain 1b', song.header["VerseOrder"])
        self.assertIn('Refrain 1', song.header["VerseOrder"])
        expected = ['Intro', 'Strophe 1', 'Strophe 2', 'Refrain 1', 'Bridge', 'Strophe 3']
        self.assertEqual(expected, list(song.content.keys()))

    def test_validate_verse_numbers2(self):
        """More complicated file with more issues and problems with None in VerseOrder"""
        song = SngFile('./testData/375 Dass Jesus siegt bleibt ewig ausgemacht.sng')
        text = 'Strophe 1a,Strophe 1b,Strophe 1c,Strophe 4a,Strophe 4b,Strophe 4c,STOP,' \
               'Strophe 2a,Strophe 2b,Strophe 2c,Strophe 3a,Strophe 3b,Strophe 3c'

        expected_order = text.split(',')
        self.assertEqual(song.header['VerseOrder'], expected_order)

        song.validate_verse_numbers(fix=True)
        expected_order = ['Strophe 1', 'Strophe 4', 'STOP', 'Strophe 2', 'Strophe 3']
        self.assertEqual(expected_order, song.header['VerseOrder'])
        expected_order = ['Strophe 1', 'Strophe 2', 'Strophe 3', 'Strophe 4']
        self.assertEqual(expected_order, list(song.content.keys()))

    def test_validate_verse_numbers3(self):
        """
        Test with a file that has other verses than verse order
        fixes verse order based on content
        and verse number validation should not have any impact
        :return:
        """
        song = SngFile('./testData/289 Nun lob mein Seel den Herren.sng')
        song.validate_verse_order_coverage(True)
        song.validate_verse_numbers(True)

        self.assertIn("Verse 1", song.header["VerseOrder"])
        self.assertIn("STOP", song.header["VerseOrder"])
        self.assertIn("Verse 1", song.content.keys())

    def test_header_validate_verse_numbers4(self):
        """
        Special Case 375 Dass Jesus siegt bleibt ewig ausgemacht.sng with merging verse blocks
        did show up as list instead of lines for slide 2 and 3 for verse 1
        :return:
        """
        song = SngFile('./testData/375 Dass Jesus siegt bleibt ewig ausgemacht.sng', 'EG')
        self.assertEqual(song.content['Strophe 1b'][1][0], 'denn alles ist')
        song.validate_verse_numbers(fix=True)
        self.assertEqual(song.content['Strophe 1'][2][0], 'denn alles ist')

    def test_content_STOP_VerseOrder(self):
        """
        Checks and corrects existance of STOP in Verse Order
        1. File does not have STOP
        2. File does already have STOP
        3. File does have STOP but not at end and should stay this way
        4. File does have STOP but not at end and should not stay this way
        :return:
        """
        # 1. File does not have STOP
        song = SngFile('./testData/079 Höher_reformat.sng')
        self.assertNotIn('STOP', song.header['VerseOrder'])
        self.assertTrue(song.validate_stop_verseorder(fix=True))
        self.assertIn('STOP', song.header['VerseOrder'])

        # 2. File does already have STOP
        song = SngFile('./testData/022 Die Liebe des Retters.sng')
        self.assertIn('STOP', song.header['VerseOrder'])
        self.assertTrue(song.validate_stop_verseorder())
        self.assertIn('STOP', song.header['VerseOrder'])

        # 3. File does have STOP but not at end and should stay this way
        song = SngFile('./testData/085 O Haupt voll Blut und Wunden.sng')
        self.assertEqual('STOP', song.header['VerseOrder'][5])
        self.assertNotEqual('STOP', song.header['VerseOrder'][11])
        self.assertNotEqual('STOP', song.header['VerseOrder'][-1])
        self.assertTrue(song.validate_stop_verseorder(should_be_at_end=False))
        self.assertEqual('STOP', song.header['VerseOrder'][5])
        self.assertNotEqual('STOP', song.header['VerseOrder'][-1])
        self.assertNotEqual('STOP', song.header['VerseOrder'][11])

        # 4. File does have STOP but not at end and should not stay this way
        song = SngFile('./testData/085 O Haupt voll Blut und Wunden.sng')
        self.assertEqual('STOP', song.header['VerseOrder'][5])
        self.assertNotEqual('STOP', song.header['VerseOrder'][-1])
        self.assertTrue(song.validate_stop_verseorder(fix=True, should_be_at_end=True))
        self.assertNotEqual('STOP', song.header['VerseOrder'][5])
        self.assertEqual('STOP', song.header['VerseOrder'][-1])

    def test_helper_contains_songbook_prefix(self):
        """
        Test that runs various variations of songbook parts which should be detected by improved helper method
        :return:
        """
        # negative samples
        self.assertFalse(contains_songbook_prefix("gesegnet"))

        # positive samples
        self.assertTrue(contains_songbook_prefix("EG"))
        self.assertTrue(contains_songbook_prefix("EG999"))
        self.assertTrue(contains_songbook_prefix("EG999Psalm"))
        self.assertTrue(contains_songbook_prefix("EG999"))
        self.assertTrue(contains_songbook_prefix("EG999Psalm"))
        self.assertTrue(contains_songbook_prefix("EG999-Psalm"))
        self.assertTrue(contains_songbook_prefix("EG-999"))
        self.assertTrue(contains_songbook_prefix("999EG"))
        self.assertTrue(contains_songbook_prefix("999-EG"))

        self.assertTrue(contains_songbook_prefix("FJ"))
        self.assertTrue(contains_songbook_prefix("FJ999"))
        self.assertTrue(contains_songbook_prefix("FJ999Text"))
        self.assertTrue(contains_songbook_prefix("FJ999"))
        self.assertTrue(contains_songbook_prefix("FJ999Text"))
        self.assertTrue(contains_songbook_prefix("FJ999-Text"))
        self.assertTrue(contains_songbook_prefix("FJ-999"))
        self.assertTrue(contains_songbook_prefix("FJ5-999"))
        self.assertTrue(contains_songbook_prefix("FJ5/999"))
        self.assertTrue(contains_songbook_prefix("999/FJ5"))
        self.assertTrue(contains_songbook_prefix("999-FJ5"))
        self.assertTrue(contains_songbook_prefix("999.FJ5"))

    def test_getset_id(self):
        """
        Test that runs various variations of songbook parts which should be detected by improved helper method
        :return:
        """
        path = "./testData/"
        filename = "001 Macht Hoch die Tuer.sng"
        song = SngFile(path + filename)

        self.assertEqual(song.get_id(), -1)
        song.set_id(-2)
        self.assertEqual(song.get_id(), -2)

    def test_isoutf8(self):
        """
        Test method for conversion of iso-8859-1  files to UTF-8 using public domain sample from tests folder

        1. Check that all test files exist and encoding match accordingly
        2. Parses an iso 8859-1 encoded file
        3. Parses an utf-8 file with BOM
        4. Parses an utf-8 file without BOM
        5. Parsing iso file writes utf8 and checks if output file has BOM

        :return:
        """

        path = 'testData/ISO-UTF8/'
        iso_file_path = path + 'Herr du wollest uns bereiten_iso.sng'
        iso2utf_file_name = 'Herr du wollest uns bereiten_iso2utf.sng'
        iso2utf_file_path = path + iso2utf_file_name
        utf_file_path = path + 'Herr du wollest uns bereiten_ct_utf8.sng'
        noBOM_utf_file_path = path + 'Herr du wollest uns bereiten_noBOM_utf8.sng'

        # Part 1

        iso_file_path = 'testData/ISO-UTF8/Herr du wollest uns bereiten_iso.sng'
        utf_file_path = 'testData/ISO-UTF8/Herr du wollest uns bereiten_utf8.sng'

        file_iso_as_iso = open(iso_file_path, encoding='iso-8859-1')
        text = file_iso_as_iso.read()
        self.assertEqual('#', text[0], 'ISO file read with correct ISO encoding')
        file_iso_as_iso.close()

        file_iso_as_utf = open(iso_file_path, encoding='utf-8')
        with self.assertRaises(UnicodeDecodeError) as cm:
            text = file_iso_as_utf.read()
        file_iso_as_utf.close()

        file_utf_as_iso = open(utf_file_path, encoding='iso-8859-1')
        text = file_utf_as_iso.read()
        self.assertEqual("ï»¿", text[0:3], 'UTF8 file read with wrong encoding')
        file_utf_as_iso.close()

        file_utf_as_utf = open(utf_file_path, encoding='utf-8')
        text = file_utf_as_utf.read()
        self.assertEqual("\ufeff", text[0], 'UTF8 file read with correct encoding including BOM')
        file_utf_as_utf.close()

        # Part 2
        with self.assertLogs(level=logging.DEBUG) as cm:
            sng = SngFile(iso_file_path)
        expected1 = 'INFO:root:testData/ISO-UTF8/Herr du wollest uns bereiten_iso.sng is read as iso-8859-1 - be aware that encoding is change upon write!'
        self.assertEqual(expected1, cm.output[0])
        self.assertEqual(2, len(cm.output))

        # Part 3
        with self.assertLogs(level=logging.DEBUG) as cm:
            sng = SngFile(utf_file_path)
        expected1 = 'DEBUG:root:testData/ISO-UTF8/Herr du wollest uns bereiten_ct_utf8.sng is detected as utf-8 because of BOM'
        self.assertEqual(expected1, cm.output[0])
        self.assertEqual(2, len(cm.output))

        # Part 4
        with self.assertLogs(level=logging.INFO) as cm:
            sng = SngFile(noBOM_utf_file_path)
        expected1 = 'INFO:root:testData/ISO-UTF8/Herr du wollest uns bereiten_noBOM_utf8.sng is read as utf-8 but no BOM'
        self.assertEqual(expected1, cm.output[0])
        self.assertEqual(1, len(cm.output))

        # Part 5
        sng = SngFile(iso_file_path)
        sng.filename = iso2utf_file_name
        sng.write_file()

        file_iso2utf = open(iso2utf_file_path, encoding='utf-8')
        text = file_iso2utf.read()
        self.assertEqual("\ufeff", text[0], 'UTF8 file read with correct encoding including BOM')
        file_iso2utf.close()

        os.remove(iso2utf_file_path)


if __name__ == '__main__':
    unittest.main()
