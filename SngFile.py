import logging

import SNG_DEFAULTS
from SNG_DEFAULTS import SngDefaultHeader, SngIllegalHeader


class SngFile:

    def __init__(self, filename, songbook_prefix=''):
        """
        Default Construction for a SNG File and it's params
        :param filename: filename with optional directory which should be opened
        """
        import os
        self.filename = os.path.basename(filename)
        self.path = os.path.dirname(filename)
        self.header = {}
        self.content = {}
        self.songbook_prefix = songbook_prefix
        self.parse_file(filename)

    def parse_file(self, filename):
        file = open(filename, 'r', encoding='iso-8859-1')
        temp_content = []
        for line in file.read().splitlines():
            line = line.strip()  # clean spaces
            if len(line) == 0:  # Skip empty row
                continue
            if line[0] == "#" and line[1] != "#":  # Tech Param for Header
                self.parse_param(line)
                continue
            if line == "---":  # For each new Slide within a block add new list and increase index
                temp_content.append([])
            else:  # Textzeile
                if len(temp_content) == 0:
                    logging.error("Something is wrong with the line {} of file {}".format(line, filename))
                    break
                temp_content[-1].append(line)
        file.close()
        # Remove empty blocks e.g. EG 618 ends with ---
        for content in temp_content:
            if len(content) == 0:
                temp_content.remove(content)
                self.update_editor_because_content_modified()

        logging.debug("Parsing content for: {}".format(self.filename))
        self.parse_content(temp_content)

    def parse_content(self, temp_content):
        """
        Iterates through a list of slides
        in case a versemarker is detected a new dict items with the name of the block is created
        in case there is no previous current content name a new "Unknown" block is created and a new list started
        otherwise the lines are added to the previously set content block
        :param temp_content: List of Textline lists preferably each first str entry should be verse marker
        :return:
        """
        current_contentname = None  # Use Unknown if no content name is specified
        for content in temp_content:
            # TODO check if not duplicate code compared to end of parsefile with empty block removal
            if len(content) == 0:  # Skip in case there is no content
                continue
            elif is_verse_marker_line(content[0]):  # New named content
                current_contentname = content[0]
                self.content[current_contentname] = [get_verse_marker_line(content[0])]
                self.content[current_contentname].append(content[1:])
            elif current_contentname is None:  # New unnamed content
                self.update_editor_because_content_modified()
                current_contentname = "Unknown"
                self.content["Unknown"] = [["Unknown"]]
                self.content["Unknown"].append(content)

            else:  # regular line for existing content
                self.content[current_contentname].append(content)

        # TODO need to check that "Unknown" exists in Verse Order or no Verse Order

    def parse_param(self, line):
        """
        Function which is used to interpret the context of one specific line as a param
        Safes self.params dictionary with detected params and prints all unknown lines to console

        :param line: string of one line from a SNG file
        """
        if line.__contains__("="):
            line_split = line.split("=")
            key = line_split[0][1:]
            value = line_split[1]
            self.header[key] = value

    def update_editor_because_content_modified(self):
        """
        Method used to update editor to mark files that are updated compared to it's original
        :return:
        """
        self.header["Editor"] = SngDefaultHeader["Editor"]

    def write_file(self, suffix="_new"):
        """
        Function used to write a processed SngFile to disk
        :param suffix: suffix to append to file name - default ist _new, test should use _test overwrite by ""
        :return:
        """
        filename = self.path + '/' + self.filename[:-4] + suffix + ".sng"
        new_file = open(filename, 'w', encoding='iso-8859-1')
        for key, value in self.header.items():
            new_file.write("#" + key + "=" + value + "\n")

        for key, block in self.content.items():
            result = ['---', key]
            if len(block) > 1:
                for slide in block[1:]:
                    if len(result) != 2:
                        result.append("---")
                    if len(slide) != 0:
                        result.extend(slide)
            new_file.writelines("%s\n" % line for line in result)
        new_file.close()

    def contains_required_headers(self):
        """
        Checks if all required headers are present
        Logs info in case something is missing and returns respective list of keys
        :return: bool, list of missing keys
        """
        missing = []
        for key in SNG_DEFAULTS.SngRequiredHeader:
            if key not in self.header.keys():
                missing.append(key)

        if 'LangCount' in self.header:
            if int(self.header['LangCount']) > 1:
                if 'Translation' not in self.header.keys():
                    missing.append('Translation')
                    # TODO add test case

                    # TODO add TitleLang2 validation

                    # TODO add exception for Psalms?

        result = len(missing) == 0

        if not result:
            logging.warning('Missing required headers in (' + self.filename + ') ' + str(missing))

        return result, missing

    def fix_header_church_song_id_caps(self):
        """
        Function which replaces any caps of e.g. ChurchSongId to ChurchSongID in header keys
        :return: if updated
        """
        if "ChurchSongID" not in self.header.keys():
            for i in self.header.keys():
                if 'ChurchSongID'.upper() == i.upper():
                    self.header['ChurchSongID'] = self.header[i]
                    del self.header[i]
                    logging.debug("Changed Key from {} to ChurchSongID in {}".format(i, self.filename))
                    self.update_editor_because_content_modified()
                    return True
        return False

    def fix_remove_illegal_headers(self):
        """
        removes header params in the current file which should not be present
        Does not write to disk!
        :return:
        """

        for key in list(self.header.keys()):
            if key in SngIllegalHeader:
                logging.debug('Removed {} from {} as illegal header'.format(key, self.filename))
                self.header.pop(key)
                self.update_editor_because_content_modified()

    def fix_title(self):
        """
        Helper function which checks the current title and removes and space separated block which contains
        * only SngTitleNumberChars
        * any SngSongBookPrefix
        :return: None - item itself is fixed
        """

        title_as_list = self.filename[:-4].split(" ")

        for part in title_as_list:
            if all(digit.upper() in SNG_DEFAULTS.SngTitleNumberChars for digit in part) \
                    or any(filter_t in part.upper() for filter_t in SNG_DEFAULTS.SngSongBookPrefix):
                title_as_list.remove(part)
                self.update_editor_because_content_modified()
        self.header['Title'] = " ".join(title_as_list)

    def fix_songbook(self):
        """
        Function used to try to fix the songbook and churchsong ID
        gets first space separated block of filename as reference number
        checks if this part contains only numbers and applies prefix + number for new Songbook and ChurchSongID
        otherwise writes an empty Songbook and ChurchSongID if no prefix
        or loggs error for invalid format if prefix is given but no matching number found
        :return: if something was updated
        """
        number = self.filename.split(" ")[0]

        if all(digit in SNG_DEFAULTS.SngTitleNumberChars for digit in number):  # Filename starts with number
            if "FJ" in self.songbook_prefix:
                songbook = self.songbook_prefix + '/' + number
            elif "EG" in self.songbook_prefix and 701 <= float(number) <= 758:
                # EG Psalms in EG Württemberg EG 701-758
                logging.warning(
                    'EG Psalm "{}" can not be auto corrected - please adjust manually'.format(self.filename))
                return False
            else:  # All other cases
                songbook = self.songbook_prefix + ' ' + number
            self.header["Songbook"] = songbook
            self.header["ChurchSongID"] = songbook
        else:  # Filename does not start with number
            if self.songbook_prefix in SNG_DEFAULTS.KnownSongBookPrefix:
                logging.warning('Invalid number format in Filename - can\'t fix songbook of ' + self.filename)

            elif not self.songbook_prefix == '':  # Not empty Prefix
                logging.warning('Unknown Songbook Prefix - can\'t complete fix songbook of ' + self.filename)
                if "Songbook" not in self.header.keys():
                    self.header["Songbook"] = self.songbook_prefix + ' ???'
                    self.header["ChurchSongID"] = self.songbook_prefix + ' ???'
            else:  # No Prefix or Number
                self.header["Songbook"] = ' '
                self.header["ChurchSongID"] = ' '
        self.update_editor_because_content_modified()
        return True

    def fix_content_slides_number_of_lines(self, number_of_lines=4):
        """
        Method that rearranges slides to contain 4 lines except for last block which can have less than 4
        :param number_of_lines max number of lines allowed per slide
        :return: True if something was fixed
        """

        result = False

        for key, value in self.content.items():  # Iterate all blocks
            # any which is not last not 4 lines is wrong
            has_issues = any([len(slide) != 4 for slide in value[1:-1]])
            # any which is last > 4 is wrong
            has_issues |= len(value[-1]) > 4

            if has_issues:
                logging.debug("Fixing block {} of {}".format(key, self.filename))

                all_lines = []  # Merge list of all text lines
                for slide in value[1:]:
                    all_lines.extend(slide)

                self.content[key] = [value[0]]  # Remove all old text lines except for Verse Marker
                for i in range(0, len(all_lines), number_of_lines):
                    self.content[key].append(all_lines[i:i + number_of_lines])
                result = True
            else:
                result = False
        return result

def is_verse_marker_line(line):
    """
    Function used to check if a line begins with a verse marker
    Needs to begin with Verse Marker and either have no extra content or another block split by space
    In case of $$= equal sign is used as separator
    :param line:
    :return: True in case matches, otherwise False
    """
    marker = ['Unbekannt', 'Unbenannt', 'Unknown', 'Intro', 'Vers', 'Verse', 'Strophe', 'Pre - Bridge', 'Bridge',
              'Misc', 'Pre-Refrain', 'Refrain', 'Pre-Chorus', 'Chorus', 'Pre-Coda',
              'Zwischenspiel', 'Instrumental', 'Interlude', 'Coda', 'Ending', 'Outro', 'Teil', 'Part', 'Chor', 'Solo'
              ]
    if line.startswith('$$M='):
        return True
    else:
        line = line.split(" ")
        if line[0] in marker:
            return True
    return False


def get_verse_marker_line(text):
    """
    Function used to convert a verse marker to a list of marker and number
    Needs to begin with Verse Marker and either have no extra content or another block split by space
    In case of $$= equal sign is used as separator
    :param text:
    :return: list of marker and optional detail in case matches, otherwise false
    """
    if is_verse_marker_line(text):
        if text.startswith('$$M='):
            return ['$$M=', text[4:]]
        else:
            return text.split(" ")
