import logging
import re

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
        """
        Opens a file and tries to parse the respective lines
        by default utf8 is tried. INFO is logged if BOM is missing.
        In case of Decoding errors iso-8859-1 is tried instead logging an INFO message
        :param filename: name including file extension of the file to be opened
        :type filename: str
        :return: None because the object itself is created
        :rtype: None
        """

        try:
            file = open(filename, 'r', encoding='utf-8')
            content = file.read()
            if content[0] == '\ufeff':
                logging.debug('{} is detected as utf-8 because of BOM'.format(filename))
                content = content[1:]
            else:
                logging.info('{} is read as utf-8 but no BOM'.format(filename))
        except UnicodeDecodeError:
            file.close()
            file = open(filename, 'r', encoding='iso-8859-1')
            content = file.read()
            logging.info('{} is read as iso-8859-1 - be aware that encoding is change upon write!'.format(filename))

        temp_content = []
        for line in content.splitlines():
            if len(line) == 0:  # Skip empty row
                continue
            if line[0] == "#" and line[1] != "#":  # Tech Param for Header
                self.parse_param(line)
                continue
            if line[0:4] == 'ï»¿#':
                logging.error("File ({}) starts with ï»¿# likely encoding error!".format(filename))
                continue
            if line == "---":  # For each new Slide within a block add new list and increase index
                temp_content.append([])
            else:  # Textzeile
                if len(temp_content) == 0:
                    logging.error("Something is wrong with the line {} of file {}".format(line, filename))
                    break
                temp_content[-1].append(line)
        file.close()
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
            if len(content) == 0:  # Skip in case there is no content
                self.update_editor_because_content_modified()
                continue
            elif get_verse_marker_line(content[0]) is not None:  # New named content
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

    def parse_param(self, line):
        """
        Function which is used to interpret the context of one specific line as a param
        Safes self.params dictionary with detected params and prints all unknown lines to console

        Converts Verse Order to list of elements

        :param line: string of one line from a SNG file
        """
        if line.__contains__("="):
            line_split = line.split("=", 1)
            key = line_split[0][1:]
            if key == "VerseOrder":
                value = line_split[1].split(",")
            else:
                value = line_split[1]
            self.header[key] = value

    def update_editor_because_content_modified(self):
        """
        Method used to update editor to mark files that are updated compared to it's original
        :return:
        """
        self.header["Editor"] = SngDefaultHeader["Editor"]

    def write_path_change(self, dirname='/home/benste/Desktop'):
        """
        Method to change the path entry to a different directory keeping the file collection specific last level folder
        :param: dirname: default path to insert before folder name
        :return:
        """
        new_path = "/".join([dirname, self.path.split("/")[-1]])
        logging.debug("Changing path from {} to {}".format(self.path, new_path))
        self.path = new_path

    def write_file(self, suffix="", encoding='utf-8'):
        """
        Function used to write a processed SngFile to disk
        Converts Verse Order from list to string
        :param suffix: suffix to append to file name - default ist _new, test should use _test overwrite by ""
        :param encoding: name of the encoding usually utf-8 alternatively iso-8859-1 for older files
        :type encoding: str
        :return:
        """
        filename = self.path + '/' + self.filename[:-4] + suffix + ".sng"
        new_file = open(filename, 'w', encoding=encoding)
        if encoding == 'utf-8':
            new_file.write('\ufeff') #BOM to indicate UTF-8 encoding for legacy compatibility
        for key, value in self.header.items():
            if key == "VerseOrder":
                new_file.write("#" + key + "=" + ','.join(value) + "\n")
            else:
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

    def validate_headers(self):
        """
        Checks if all required headers are present
        Logs info in case something is missing and returns respective list of keys
        :return: bool indicating if anything is missing
        """
        missing = []
        for key in SNG_DEFAULTS.SngRequiredHeader:
            if key not in self.header.keys():
                missing.append(key)

        if self.is_eg_psalm():
            if "Bible" not in self.header.keys():
                missing.append('Bible')

        if 'LangCount' in self.header:
            if int(self.header['LangCount']) > 1:
                if 'Translation' not in self.header.keys():
                    missing.append('Translation')
                    # TODO add test case for language validation

                    # TODO add TitleLang2 validation

        result = len(missing) == 0

        if not result:
            logging.warning('Missing required headers in ({}) {}'.format(self.filename, missing))

        return result

    def validate_header_title(self, fix=False):
        """
        Validation method for Title header checks for existance and numbers
        :param fix: bool if it should be attempt to fix itself
        :return: bool if Title is valid at end of method
        """

        if "Title" not in self.header.keys():
            logging.debug("Song without a Title in Header:" + self.filename)
            title_valid = False
        else:
            title_as_list = self.header['Title'].split(" ")

            contains_number = False
            does_contain_songbook_prefix = False
            for part in title_as_list:
                contains_number |= \
                    any(digit.upper() in SNG_DEFAULTS.SngTitleNumberChars for digit in part)
                does_contain_songbook_prefix |= contains_songbook_prefix(part)
            # Exception - Songs without prefix may contain numbers e.g. Psalm 21 ...
            if len(self.songbook_prefix) == 0:
                title_valid = True
            else:
                title_valid = not (contains_number or does_contain_songbook_prefix)
            # Log Errors
            if not title_valid and contains_number:
                logging.debug('Song with Number in Title "{}" ({})'.format(title_as_list, self.filename))
            elif not title_valid and does_contain_songbook_prefix:
                logging.debug('Song with Songbook in Title "{}" ({})'.format(title_as_list, self.filename))

        if fix and not title_valid:
            title_as_list = self.filename[:-4].split(" ")
            for part in title_as_list:
                if all(digit.upper() in SNG_DEFAULTS.SngTitleNumberChars for digit in part) \
                        or contains_songbook_prefix(part):
                    title_as_list.remove(part)
                    self.update_editor_because_content_modified()
            self.header['Title'] = " ".join(title_as_list)
            logging.debug("Fixed title to ({}) in {}".format(self.header['Title'], self.filename))
            title_valid = self.validate_header_title(fix=False)

            if self.header['Title'] == 'Psalm':
                logging.warning('Can\'t fix title is Psalm {} without complete heading'.format(self.filename))

        return title_valid

    def validate_header_songbook(self, fix=False):
        """
        Validation method for Songbook and ChurchSongID headers
        :param fix: bool if it should be attempt to fix itself
        :return: if songbook is valid at end of method
        """

        # Validate Headers
        if 'ChurchSongID' not in self.header.keys() or 'Songbook' not in self.header.keys():
            # Hint - ChurchSongID ' '  or '' is automatically removed from SongBeamer on Editing in Songbeamer itself
            songbook_valid = False
        else:
            songbook_valid = self.header['ChurchSongID'] == self.header['Songbook']

            # Check that songbook_prefix is part of songbook
            songbook_valid &= self.songbook_prefix in self.header['Songbook']

            # Check Syntax with Regex, either FJx/yyy, EG YYY, EG YYY.YY or or EG XXX - Psalm X or Wwdlp YYY
            # ^(Wwdlp \d{3})|(FJ([1-6])\/\d{3})|(EG \d{3}(( - Psalm )\d{1,3})?)$
            songbook_regex = r"^(Wwdlp \d{3})$|(^FJ([1-6])\/\d{3})$|" \
                             r"^(EG \d{3}(\.\d{1,2})?)( - Psalm \d{1,3}( .{1,3})?)?$"
            songbook_valid &= re.match(songbook_regex, self.header["Songbook"]) is not None

            # Check for remaining that "&" should not be present in Songbook
            # songbook_invalid |= self.header["Songbook"].contains('&')
            # sample is EG 548 & WWDLP 170 = loc 77
            # -> no longer needed because of regex check

            # TODO low Prio - check numeric range of songbooks
            # EG 1 - 851 incl.non numeric e.g. 178.14
            # EG Psalms in EG Württemberg EG 701-758
            # Syntax should be EG xxx - Psalm Y

        if fix and not songbook_valid:
            self.fix_header_church_song_id_caps()
            fixed = self.fix_songbook()

            if not fixed and 'Songbook' not in self.header.keys():
                logging.error("Problem occured with Songbook Fixing of {} - check logs!".format(self.filename))
                self.header["Songbook"] = None
            if not fixed and 'ChurchSongID' not in self.header.keys():
                logging.error("Problem occured with ChurchSongID Fixing of {} - check logs!".format(self.filename))
                self.header["ChurchSongID"] = None
            elif not fixed:
                logging.error(
                    "Problem occurred with Songbook Fixing of {} - kept original {},{}".format(
                        self.filename, self.header["Songbook"], self.header["ChurchSongID"]))

            songbook_valid = self.validate_header_songbook(fix=False)

        return songbook_valid

    def validate_header_background(self, fix=False):
        """
        Checks that background matches certain criteria
        :param fix: bool if it should be attempt to fix itself
        :return: bool if backgrounds are ok
        """

        if "BackgroundImage" not in self.header.keys():
            if not fix:
                logging.debug("No Background in ({})".format(self.filename))
            result = False
        else:
            if self.is_eg_psalm():
                if self.header["BackgroundImage"] != 'Evangelisches Gesangbuch.jpg':
                    if not fix:
                        logging.debug("Incorrect background for Psalm in ({}) not fixed".format(self.filename))
                    result = False
                else:
                    result = True
            else:
                result = True

        if fix and not result:
            if self.is_eg_psalm():
                self.header["BackgroundImage"] = 'Evangelisches Gesangbuch.jpg'
                logging.debug("Fixing background for Psalm in ({})".format(self.filename))
                self.update_editor_because_content_modified()
                result = True
            else:
                logging.warning("Can't fix background for ({})".format(self.filename))

        return result
        # TODO validate background against resolution list
        # TODO validate background against copyright available

    def validate_verse_order_coverage(self, fix=False):
        """
        Checks that all items of content are part of Verse Order
        and all items of VerseOrder are available in content
        :param fix: bool if it should be attempt to fix itself
        :return: bool if verses_in_order
        """

        if 'VerseOrder' not in self.header.keys():
            verses_in_order = False
        else:
            verse_order_covers_all_blocks = all(
                [i in self.content.keys()
                 or '$$M=' + i in self.content.keys()
                 or i == 'STOP'
                 for i in self.header["VerseOrder"]]
            )

            all_blocks_in_verse_order = all(
                [i[4:] if i[:4] == '$$M=' else i in self.header["VerseOrder"]
                 for i in self.content.keys()]
            )
            verses_in_order = all_blocks_in_verse_order & verse_order_covers_all_blocks

        if fix and not verses_in_order:
            if 'VerseOrder' not in self.header.keys():
                self.header['VerseOrder'] = []

            # Add blocks to Verse Order if they are missing
            for content_block in self.content.keys():
                if not (content_block[:4] == '$$M=' and content_block[4:] in self.header["VerseOrder"]
                        or content_block in self.header["VerseOrder"]):
                    if content_block[:4] == '$$M=':
                        self.header["VerseOrder"].append(content_block[4:])
                    else:
                        self.header["VerseOrder"].append(content_block)

            # Remove blocks from verse order that don't exist
            self.header["VerseOrder"][:] = [v for v in self.header["VerseOrder"]
                                            if v in self.content.keys()
                                            or '$$M=' + v in self.content.keys()
                                            or v == 'STOP']

            logging.debug('Fixed VerseOrder to {} in ({})'.format(self.header["VerseOrder"], self.filename))
            self.update_editor_because_content_modified()
            verses_in_order = True

        elif not fix and not verses_in_order:
            logging.warning('Verse Order and Blocks don\'t match in {}'.format(self.filename))
            if "VerseOrder" not in self.header.keys():
                logging.debug('Missing VerseOrder in ({})'.format(self.filename))
            else:
                logging.debug('\t Not fixed: Order: {}'.format(str(self.header["VerseOrder"])))
                logging.debug('\t Not fixed: Blocks: {}'.format(str(list(self.content.keys()))))

        return verses_in_order

    def generate_verses_from_unknown(self):
        """
        Method used to split any "Unknown" Block into Auto detected segments of numeric verses or Refrain
        :return:
        """
        logging.info("Started generate_verses_from_unknown()")

        if 'Unknown' in self.content.keys():
            current_block_name = 'Unknown'
            old_block = self.content[current_block_name]
            new_blocks = {'Unknown': []}
            for block in old_block:
                if re.match(r'^(\d+\.).+|(R:).+', block[0]) is not None:  # is new verse
                    current_block_name = re.match(r'^(\d+)|(R:)', block[0])[0]
                    if current_block_name == 'R:':
                        current_block_name = 'Refrain'
                    else:
                        current_block_name = 'Verse {}'.format(current_block_name)
                    logging.debug(
                        ("Detected new '{}' in 'Unknown' block of ({})".format(current_block_name, self.filename)))
                    new_text = [re.sub(r'^(\d\.) +|(R:) +', '', block[0])]
                    new_text.extend(block[1:])
                    new_blocks[current_block_name] = [current_block_name, new_text]
                else:  # not new verse add to last block of new block
                    new_blocks[current_block_name].append(block)

            # Cleanup Legacy if not used
            if len(new_blocks['Unknown']) == 1:
                del new_blocks['Unknown']
            new_block_keys = list(new_blocks.keys())

            for i in range(len(self.header["VerseOrder"])):
                if self.header["VerseOrder"][i] == 'Unknown':
                    del self.header["VerseOrder"][i]
                    for key in new_block_keys:
                        if key not in self.header["VerseOrder"]:
                            self.header["VerseOrder"].insert(i, key)
                            i += 1
                            logging.debug("Added new '{}' in Verse Order of ({})".format(key, self.filename))
                        else:
                            logging.warning(
                                "Not adding duplicate '{}' in Verse Order of ({})".format(key, self.filename))
                    break

            self.update_editor_because_content_modified()
            return new_blocks

    def fix_intro_slide(self):
        """
        Checks if Intro Slide exists as content block and adds in case one is required
        Also ensures that Intro is part of VerseOrder
        :return:
        """
        if 'Intro' not in self.header["VerseOrder"]:
            self.header["VerseOrder"].insert(0, 'Intro')
            self.update_editor_because_content_modified()
            logging.debug("Added Intro to VerseOrder of ({})".format(self.filename))

        if 'Intro' not in self.content.keys():
            intro = {'Intro': [['Intro'], []]}
            self.content = {**intro, **self.content}
            self.update_editor_because_content_modified()
            logging.debug("Added Intro Block to ({})".format(self.filename))

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

    def fix_header_ccli_caps(self):
        """
        Function which replaces any caps of e.g. ccli Ccli CCLi to CCLI in header keys
        :return: if updated
        """
        if "CCLI" not in self.header.keys():
            for i in self.header.keys():
                if i.upper() == 'CCLI':
                    self.header['CCLI'] = self.header[i]
                    del self.header[i]
                    logging.debug("Changed Key from {} to CCLI in {}".format(i, self.filename))
                    self.update_editor_because_content_modified()
                    return True
        return False

    def validate_headers_illegal_removed(self, fix=False):
        """
        Checks if all illegeal headers are removed and optionally fixes it by removing illegal ones
        :param fix: bool whether should be fixed
        :return: if all illegal headers are removed
        """
        result = True
        removed = []
        for key in list(self.header.keys()):
            if key in SngIllegalHeader:
                if fix:
                    removed.append(key)
                    self.header.pop(key)
                    self.update_editor_because_content_modified()
                    result &= True
                else:
                    result &= False

        if fix and len(removed) > 0:
            logging.debug('Removed {} from ({}) as illegal header'.format(removed, self.filename))
        elif not fix and len(removed) > 0:
            logging.debug('Not fixing illegal header {} in ({})'.format(removed, self.filename))

        return result

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
        if 'Songbook' in self.header.keys():
            songbook_before_change = self.header['Songbook']
        else:
            songbook_before_change = 'NOT SET'

        if all(digit in SNG_DEFAULTS.SngTitleNumberChars for digit in number):  # Filename starts with number
            # Feiert Jesus Prefix
            if "FJ" in self.songbook_prefix:
                songbook = self.songbook_prefix + '/' + number

            # Evangelisches Gesangsbuch - Psalm
            elif self.is_eg_psalm():
                logging.warning(
                    'EG Psalm "{}" can not be auto corrected - please adjust manually'.format(self.filename))
                return False
            # All other with filename that starts with number
            else:
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
            elif 'Songbook' in self.header.keys() and 'ChurchSongID' in self.header.keys():
                if self.header["Songbook"] == ' ' and self.header["ChurchSongID"] == ' ':
                    return True
                else:
                    logging.warning('This case should not exist! please check code logic')
            else:  # No Prefix or Number
                self.header["Songbook"] = ' '
                self.header["ChurchSongID"] = ' '

        # In any case that was not returned before
        if 'Songbook' in self.header.keys():  # Prepare Logging text
            text = 'Corrected Songbook / ChurchSongID from ({})  to ({}) in {}' \
                .format(songbook_before_change, self.header['Songbook'], self.filename)
            logging.debug(text)

        self.update_editor_because_content_modified()
        return True

    def validate_content_slides_number_of_lines(self, number_of_lines=4, fix=False):
        """
        Method that checks if slides need to contain # (default 4) lines except for last block which can have less
        and optionally fixes it
        :param number_of_lines max number of lines allowed per slide
        :param fix: bool if it should be attempt to fix itself
        :return: True if something was fixed
        """
        for key, value in self.content.items():  # Iterate all blocks
            # any which is not last not 4 lines is wrong
            has_issues = any([len(slide) != 4 for slide in value[1:-1]])
            # any which is last > 4 is wrong
            has_issues |= len(value[-1]) > 4

            if has_issues and fix:
                logging.debug("Fixing block length {} in ({}) to {} lines".format(key, self.filename, number_of_lines))

                all_lines = []  # Merge list of all text lines
                for slide in value[1:]:
                    all_lines.extend(slide)

                self.content[key] = [value[0]]  # Remove all old text lines except for Verse Marker
                for i in range(0, len(all_lines), number_of_lines):
                    self.content[key].append(all_lines[i:i + number_of_lines])
                self.update_editor_because_content_modified()
            elif has_issues:
                return False
        return True

    def validate_verse_numbers(self, fix=False):
        """
        Method which checks Verse Numbers for numeric parts that are non-standard - e.g. 1b
        and tries to merge consecutive similar parts
        :return:
        """
        all_verses_valid = True
        new_content = {}
        for key, block in self.content.items():
            # if block starts with a Versemarker and some additional information
            if block[0][0] in SNG_DEFAULTS.VerseMarker and len(block[0]) > 1:
                if not fix:
                    all_verses_valid &= block[0][1].isdigit()
                    new_content[key] = block
                    if not all_verses_valid:
                        logging.debug("Invalid verse label {} not fixed in ({})".
                                      format(block[0], self.filename))
                elif fix and not block[0][1].isdigit():
                    # change block label
                    old_key = " ".join(block[0])
                    new_number = re.sub(r'\D+', '', block[0][1])
                    new_label = [block[0][0], new_number]
                    new_key = " ".join(new_label)

                    # check if new block name already exists
                    if new_key in new_content.keys():
                        logging.debug("\t Appending {} to existing Verse label {}".
                                      format(old_key, new_key))
                        # if yes, append content and remove old label from verse order
                        new_content[new_key].append(block[1])
                        self.header["VerseOrder"] = [item for item in self.header["VerseOrder"] if item != old_key]
                    else:
                        logging.debug("New Verse label from {} to {} in ({})".
                                      format(old_key, new_key, self.filename))
                        # if no, rename block in verse order and dict
                        self.header["VerseOrder"] = \
                            [new_key if item == old_key else item for item in self.header["VerseOrder"]]
                        new_content[new_key] = [new_label] + block[1:]
                    all_verses_valid &= True
                    self.update_editor_because_content_modified()
                else:  # In Case block is something different than regular verse with number
                    new_content[key] = block
            else:  # In Case block is something different than regular verse with number
                new_content[key] = block

        self.content = new_content
        return all_verses_valid

    def validate_stop_verseorder(self, fix=False, should_be_at_end=False):
        """
        Method which checks that a STOP exists in VerseOrder headers and corrects it
        :param should_be_at_end removes any 'STOP' and makes sure only one at end exists
        :param fix: bool if it should be attempt to fix itself
        :return: if something is wrong after applying method
        """
        result = True
        # STOP exists but not at end
        if should_be_at_end and 'STOP' in self.header['VerseOrder'] and not 'STOP' == self.header['VerseOrder'][-1]:
            if fix:
                logging.debug('Removing STOP from {}'.format(self.header['VerseOrder']))
                self.header['VerseOrder'].remove('STOP')
                self.update_editor_because_content_modified()
                logging.debug('STOP removed at old position in ({}) because not at end'.format(self.filename))
                result = True
            else:
                logging.warning('STOP from ({}) not at end but not fixed in {}'.
                                format(self.filename, self.header["VerseOrder"]))
                result = False

        # STOP missing overall
        if 'STOP' not in self.header['VerseOrder']:
            if fix:
                self.header['VerseOrder'].append('STOP')
                logging.debug(
                    'STOP added at end of VerseOrder of {}: {}'.format(self.filename, self.header['VerseOrder']))
                self.update_editor_because_content_modified()
                result = True
            else:
                result = False
                logging.warning('STOP missing in ({}) but not fixed in {}'.
                                format(self.filename, self.header["VerseOrder"]))
        return result

    def get_id(self):
        """
        Helper function accessing ID in header mapping not existant to -1
        :return: id
        :rtype: int or None
        """
        if 'id' in self.header.keys():
            return int(self.header['id'])
        else:
            return -1

    def set_id(self, id: int):
        """
        Helper function for easy access to write header ID
        :param id: ID (ideally ChurchTools) which should be set for the specific song
        :type int
        :return:
        """
        self.header['id'] = str(id)
        self.update_editor_because_content_modified()

    def is_eg_psalm(self):
        """ Helper function to determine if the song is an EG Psalm
        Conditions are
        1. must have EG in Songbook Prefix
        2. filename must start with number in correct range
            EG Psalms in EG Württemberg EG 701-758
        @:return bool
        """
        return "EG" in self.songbook_prefix and 701 <= float(self.filename.split(" ")[0]) <= 758


def get_verse_marker_line(line):
    """
    Function used to convert a verse marker to a list of marker and number
    Line needs to begin with Verse Marker and either have no extra content or another block split by space
    In case of $$= equal sign is used as separator
    :param line:
    :return: list of marker and optional detail in case matches, otherwise None
    """

    """
    Function used to check if a line begins with a verse marker and return respective
    Needs to begin with Verse Marker and either have no extra content or another block split by space
    :param line:
    :return: True in case matches, otherwise False
    """
    from SNG_DEFAULTS import VerseMarker

    if line.startswith('$$M='):
        return ['$$M=', line[4:]]
    else:
        line = line.split(" ")
        if line[0] in VerseMarker:
            return line
    return None


def contains_songbook_prefix(text):
    """
    Helper function to determine whether text contains a songbook prefix
    :param text:
    :return: result of check
    """
    result = False
    for prefix in SNG_DEFAULTS.SngSongBookPrefix:
        songbook_regex = r"({}\W+.*)|(.*\W+{})|({}\d+.*)|(.*\d+{})|(^{})|({}$)" \
            .format(prefix, prefix, prefix, prefix, prefix, prefix)
        result |= re.match(songbook_regex, text.upper()) is not None

    return result
