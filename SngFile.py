"""This file is used to define SngFile class and somee helper methods related to it's usage."""

import logging
import re
from io import TextIOWrapper
from itertools import chain
from pathlib import Path

import SNG_DEFAULTS
from SNG_DEFAULTS import KnownSongBookPsalmRange, SngDefaultHeader, SngIllegalHeader


class SngFile:
    """Main class that defines one single SongBeamer SNG file."""

    def __init__(self, filename: str, songbook_prefix: str = "") -> None:
        """Default Construction for a SNG File and it's params.

        Args:
            filename: filename with optional directory which should be opened
            songbook_prefix: prefix of songbook e.g. EG. Defaults to "".
        """
        self.filename = Path(filename).name
        self.path = Path(filename).parent
        self.header = {}
        self.content = {}
        self.songbook_prefix = songbook_prefix
        self.parse_file()

    def parse_file(self) -> None:
        """Parse an SNG file.

        Opens a file and tries to parse the respective lines
        by default utf8 is tried. INFO is logged if BOM is missing.
        In case of Decoding errors iso-8859-1 is tried instead logging an INFO message

        triggers parse_file_content to process file content
        """
        filename = self.path / self.filename

        try:
            with Path(filename).open(encoding="utf-8") as file_object:
                content = file_object.read()
            if content[0] == "\ufeff":
                logging.debug("%s is detected as utf-8 because of BOM", filename)
                content = content[1:]
            else:
                logging.info("%s is read as utf-8 but no BOM", filename)
        except UnicodeDecodeError:
            with Path(filename).open(encoding="iso-8859-1") as file_object:
                content = file_object.read()
            logging.info(
                "%s is read as iso-8859-1 - be aware that encoding is change upon write!",
                filename,
            )
        self.parse_file_content(content)

    def parse_file_content(self, all_lines: list[str]) -> None:
        """Parse sng file content on a line by lane base.

        Args:
            all_lines: list of lines from sng file
        """
        song_blocks = []
        for line in all_lines.splitlines():
            line_no_space = line.lstrip()
            if len(line_no_space) > 0:
                if (
                    line_no_space[0] == "#" and line_no_space[1] != "#"
                ):  # Tech Param for Header
                    self.parse_param(line_no_space)
                elif (
                    line_no_space == "---"
                ):  # For each new Slide within a block add new list and increase index
                    song_blocks.append([])
                else:  # lyrics line
                    song_blocks[-1].append(line_no_space)
        logging.debug("Parsing content for: %s", self.filename)
        self.parse_content(song_blocks)

    def parse_content(self, temp_content: list[list[str]]) -> None:
        """Parses the content of slides.

        Iterates through a list of slides
        in case a versemarker is detected a new dict items with the name of the block is created
        in case there is no previous current content name a new "Unknown" block is created and a new list started
        otherwise the lines are added to the previously set content block

        Args:
            temp_content: list of Textline lists preferably each first str entry should be verse marker
        """
        current_contentname = None  # Use Unknown if no content name is specified
        for content in temp_content:
            if len(content) == 0:  # Skip in case there is no content
                self.update_editor_because_content_modified()
                continue
            if get_verse_marker_line(content[0]) is not None:  # New named content
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

    def parse_param(self, line: str) -> None:
        """Function which is used to interpret the context of one specific line as a param.

        Saves self.params dictionary with detected params and prints all unknown lines to console
        Converts Verse Order to list of elements

        Args:
            line: string of one line from a SNG file
        """
        if line.__contains__("="):
            line_split = line.split("=", 1)
            key = line_split[0][1:]
            value = line_split[1].split(",") if key == "VerseOrder" else line_split[1]
            self.header[key] = value

    def update_editor_because_content_modified(self) -> None:
        """Method used to update editor to mark files that are updated compared to it's original."""
        self.header["Editor"] = SngDefaultHeader["Editor"]

    def write_path_change(
        self, new_parent_dir: Path = Path("/home/benste/Desktop")
    ) -> None:
        """Method to change the path entry to a different directory keeping the file collection specific last level folder.

        Args: new_parent_dir: default path to insert before folder name of songbook
        """
        new_path = new_parent_dir / self.path.name
        new_path.mkdir(parents=True, exist_ok=True)
        logging.debug("Changing path from %s to %s", self.path, new_path)
        self.path = new_path

    def write_file(self, suffix: str = "", encoding: str = "utf-8") -> None:
        """Function used to write a processed SngFile to disk.

        It writes a new file line by line with
        1. Encoding indicator
        2. All header items using key=value and making verse order a comma seperated list
        3. All Content
            starting with --- separator
            adding versemarker
            parsing all lines from slides
            adding -- separator before each new slide except first

        Args:
            suffix: suffix to append to file name - default ist _new, test should use _test overwrite by ""
            encoding: name of the encoding usually utf-8 alternatively iso-8859-1 for older files
        """
        filename = Path(str(self.path) + "/" + self.filename[:-4] + suffix + ".sng")
        with Path(filename).open(encoding=encoding, mode="w") as new_file:
            # 1. Encoding indicator
            if encoding == "utf-8":
                new_file.write(
                    "\ufeff"
                )  # BOM to indicate UTF-8 encoding for legacy compatibility
            self.write_file_headers(new_file)
            self.write_file_content(new_file)

    def write_file_headers(self, output_file: TextIOWrapper) -> None:
        """Write headers of sng file to already opened file.

        Args:
            output_file: the file object to write into
        """
        for key, value in self.header.items():
            if key == "VerseOrder":
                output_file.write("#" + key + "=" + ",".join(value) + "\n")
            else:
                output_file.write("#" + key + "=" + value + "\n")

    def write_file_content(self, output_file: TextIOWrapper) -> None:
        """Write content of sng file to already opened file.

        * blocks with verse markers
        * slides with dividers

        Args:
            output_file: the file object to write into
        """
        for key, verse_block in self.content.items():
            result = ["---", key]
            is_new_verse_block = True
            for slide in verse_block[1:]:
                if not is_new_verse_block:
                    result.append("---")
                if len(slide) != 0:
                    result.extend(slide)
                    is_new_verse_block = False
            output_file.writelines(f"{line}\n" for line in result)

    def validate_headers(self) -> bool:
        """Checks if all required headers are present.

        Logs info in case something is missing and returns respective list of keys

        Args:
            bool indicating if anything is missing
        """
        missing = [
            key for key in SNG_DEFAULTS.SngRequiredHeader if key not in self.header
        ]

        if self.is_eg_psalm() and "Bible" not in self.header:
            missing.append("Bible")

        if (
            "LangCount" in self.header
            and int(self.header["LangCount"]) > 1
            and "Translation" not in self.header
        ):
            missing.append("Translation")
            # TODO (bensteUEM): Add language validation
            # https://github.com/bensteUEM/SongBeamerQS/issues/33

        result = len(missing) == 0

        if not result:
            logging.warning(
                "Missing required headers in (%s) %s", self.filename, missing
            )

        return result

    def validate_header_title(self, fix: bool = False) -> bool:  # noqa: C901
        """Validation method for title header.

        checks:
        * if title exists
        * existance of SngTitleNumberChars
        * existance of contains_number

        Anything that has no Songbook prefix could be special and is skipped as valid

        Args:
            fix: if it should be attempt to fix itself

        Returns:
            if Title is valid at end of method
        """
        title = self.header.get("Title", "")
        error_message = None

        if not title:
            error_message = f"Song without a Title in Header: {self.filename}"

        elif not self.songbook_prefix:
            # special case - songs without prefix might contain numbers e.g. "Psalm 21.sng" - not the one in EG...
            return True

        contains_number = any(
            digit.upper() in SNG_DEFAULTS.SngTitleNumberChars for digit in title
        )
        if contains_number:
            error_message = f'Song with Number in Title "{title}" ({self.filename})'

        if contains_songbook_prefix(title):
            error_message = f'Song with Songbook in Title "{title}" ({self.filename})'

        if fix and bool(error_message):
            return self.fix_header_title()

        if bool(error_message):
            logging.warning(error_message)
            return False
        # no fix, but no error
        return True

    def fix_header_title(self) -> bool:
        """Method which tries to fix title information in header based on filename.

        Returns:
           if title is valid after fix
        """
        title_as_list = self.filename[:-4].split(" ")

        if "Psalm" in title_as_list:
            error_message = (
                f"Can't fix title is Psalm {self.filename} without complete heading"
            )
            logging.warning(error_message)
        else:
            for part in title_as_list:
                if all(
                    digit.upper() in SNG_DEFAULTS.SngTitleNumberChars for digit in part
                ) or contains_songbook_prefix(part):
                    title_as_list.remove(part)
                    self.update_editor_because_content_modified()
            self.header["Title"] = " ".join(title_as_list)
            logging.debug(
                "Fixed title to (%s) in %s", self.header["Title"], self.filename
            )
        return self.validate_header_title(fix=False)

    def validate_header_songbook(self, fix: bool = False) -> bool:
        """Validation method for Songbook and ChurchSongID headers.

        Args:
            fix: if it should be attempt to fix itself

        Returns:
            if songbook is valid at end of method
        """
        # Validate Headers
        if "ChurchSongID" not in self.header or "Songbook" not in self.header:
            # Hint - ChurchSongID ' '  or '' is automatically removed from SongBeamer on Editing in Songbeamer itself
            songbook_valid = False
        else:
            songbook_valid = self.header["ChurchSongID"] == self.header["Songbook"]

            # Check that songbook_prefix is part of songbook
            songbook_valid &= self.songbook_prefix in self.header["Songbook"]

            # Check Syntax with Regex, either FJx/yyy, EG YYY, EG YYY.YY or or EG XXX - Psalm X or Wwdlp YYY
            # ^(Wwdlp \d{3})|(FJ([1-6])\/\d{3})|(EG \d{3}(( - Psalm )\d{1,3})?)$
            songbook_regex = (
                r"^(Wwdlp \d{3})$|(^FJ([1-6])\/\d{3})$|"
                r"^(EG \d{3}(\.\d{1,2})?)( - Psalm \d{1,3}( .{1,3})?)?$"
            )
            songbook_valid &= (
                re.match(songbook_regex, self.header["Songbook"]) is not None
            )

            # Check for remaining that "&" should not be present in Songbook
            # songbook_invalid |= self.header["Songbook"].contains('&')
            # sample is EG 548 & WWDLP 170 = loc 77
            # -> no longer needed because of regex check

            # TODO (bensteUEM): low Prio - check numeric range of songbooks
            # https://github.com/bensteUEM/SongBeamerQS/issues/34

            # EG 1 - 851 incl.non numeric e.g. 178.14
            # EG Psalms in EG Württemberg EG 701-758
            # Syntax should be EG xxx - Psalm Y

        logging.debug("songbook_valid == %s", songbook_valid)

        if fix and not songbook_valid:
            self.fix_header_church_song_id_caps()
            self.fix_songbook_from_filename()
            songbook_valid = self.validate_header_songbook(fix=False)

        if not songbook_valid:
            logging.error(
                "Problem occurred with Songbook Fixing of %s - kept original Songbook=%s,ChurchSongID=%s",
                self.filename,
                self.header["Songbook"],
                self.header["ChurchSongID"],
            )
            return False

        return True

    def validate_header_background(self, fix: bool = False) -> bool:
        """Checks that background matches certain criteria.

        1. Background image should exist
        2. for EG Psalms a specific image should be set (for common visual appearance)

        Args:
            fix: bool if it should be attempt to fix itself
        Returns:
            bool if backgrounds are ok
        """
        error_message = None
        if "BackgroundImage" not in self.header:
            error_message = f"No Background in ({self.filename})"
        elif (
            self.is_eg_psalm()
            and self.header["BackgroundImage"] != "Evangelisches Gesangbuch.jpg"
        ):
            error_message = (
                f"Incorrect background for Psalm in ({self.filename}) not fixed"
            )

        if not bool(error_message):
            return True

        if fix:
            return self.fix_header_background()

        logging.debug(error_message)
        return False

        # TODO (bensteUEM): validate background against resolution list
        # https://github.com/bensteUEM/SongBeamerQS/issues/29

        # TODO (bensteUEM): validate background against copyright available
        # https://github.com/bensteUEM/SongBeamerQS/issues/30

    def fix_header_background(self) -> bool:
        """Helper which tries to fix background image information automatically.

        1. if EG Psalm - set hard-coded default background picture
        2. no fixes for other cases available

        Returns:
            if header background was fixed - assuming fixes do fix ...
        """
        if self.is_eg_psalm():
            self.header["BackgroundImage"] = "Evangelisches Gesangbuch.jpg"
            logging.debug("Fixing background for Psalm in (%s)", self.filename)
            self.update_editor_because_content_modified()
            return True

        logging.warning("Can't fix background for (%s)", self.filename)
        return False

    def validate_verse_order_coverage(self, fix: bool = False) -> bool:
        """Checks that all items of content are part of Verse Order.

        and all items of VerseOrder are available in content

        Args:
            fix: bool if it should be attempt to fix it
        Returns:
            bool if verses_in_order
        """
        if "VerseOrder" in self.header:
            verse_order_covers_all_blocks = all(
                i in self.content or "$$M=" + i in self.content or i == "STOP"
                for i in self.header["VerseOrder"]
            )

            all_blocks_in_verse_order = all(
                i[4:] if i[:4] == "$$M=" else i in self.header["VerseOrder"]
                for i in self.content
            )

            if (
                verses_in_order := all_blocks_in_verse_order
                & verse_order_covers_all_blocks
            ):
                return True

        verses_in_order = False

        if fix:
            return self.fix_verse_order_coverage()

        logging.warning("Verse Order and Blocks don't match in %s", self.filename)
        if "VerseOrder" not in self.header:
            logging.debug("Missing VerseOrder in (%s)", self.filename)
        else:
            logging.debug("\t Not fixed: Order: %s", str(self.header["VerseOrder"]))
            logging.debug("\t Not fixed: Blocks: %s", list(self.content.keys()))

        return verses_in_order

    def fix_verse_order_coverage(self) -> bool:
        """Fix verse order coverage assuming it's broken.

        1. Add all verse labels from blocks that are not yet part of VerseOrder
        2. Delete all verse labels from VerseOrder that do not exist as block
        """
        self.header["VerseOrder"] = self.header.get("VerseOrder", [])

        # Add blocks to Verse Order if they are missing
        for content_block in self.content:
            if (
                content_block[:4] == "$$M="
                and content_block[4:] not in self.header["VerseOrder"]
            ):
                self.header["VerseOrder"].append(content_block[4:])
            elif content_block not in self.header["VerseOrder"]:
                self.header["VerseOrder"].append(content_block)

        # Remove blocks from verse order that don't exist
        self.header["VerseOrder"][:] = [
            v
            for v in self.header["VerseOrder"]
            if v in self.content or "$$M=" + v in self.content or v == "STOP"
        ]

        logging.debug(
            "Fixed VerseOrder to %s in (%s)",
            self.header["VerseOrder"],
            self.filename,
        )
        self.update_editor_because_content_modified()
        return True

    def generate_verses_from_unknown(self) -> dict | None:
        """Method used to split any "Unknown" Block into auto detected segments of numeric verses or chorus.

        Changes the songs VerseOrder and content blocks if possible
        Does not change parts of verses that already have a verse label !

        Returns:
            dict of blocks or None
        """
        logging.info("Started generate_verses_from_unknown()")

        old_block = self.content.get("Unknown")

        if not old_block:
            return None

        current_block_name = "Unknown"
        new_blocks = {"Unknown": []}
        for slide in old_block:
            first_line = slide[0]

            new_block_name, new_text = generate_verse_marker_from_line(first_line)

            # not new verse add to last block as next slide
            if not new_block_name:
                new_blocks[current_block_name].append(slide)
                continue

            current_block_name = " ".join(new_block_name).strip()

            logging.debug(
                "Detected new '%s' in 'Unknown' block of (%s)",
                current_block_name,
                self.filename,
            )
            # add remaining text lines from slide
            new_slides = [new_text] + slide[1:]
            new_blocks[current_block_name] = [new_block_name, new_slides]

        # Cleanup Legacy if not used
        if len(new_blocks["Unknown"]) == 1:
            del new_blocks["Unknown"]
        new_block_keys = list(new_blocks.keys())

        # look for position of "Unknown" and replace
        position_of_unknown = self.header["VerseOrder"].index("Unknown")
        self.header["VerseOrder"][
            position_of_unknown : position_of_unknown + 1
        ] = new_block_keys
        logging.info(
            "Added new '%s' in Verse Order of (%s)", new_block_keys, self.filename
        )
        self.content.pop("Unknown")
        self.content.update(new_blocks)
        # TODO (bensteUEM): check what happens if already exists
        # https://github.com/bensteUEM/SongBeamerQS/issues/35

        logging.info(
            "Replaced 'Unknown' with '%s' in Verse Order of (%s)",
            new_block_keys,
            self.filename,
        )

        self.update_editor_because_content_modified()
        return new_blocks

    def fix_intro_slide(self) -> None:
        """Checks if Intro Slide exists as content block.

        and adds in case one is required
        Also ensures that Intro is part of VerseOrder
        """
        if "Intro" not in self.header["VerseOrder"]:
            self.header["VerseOrder"].insert(0, "Intro")
            self.update_editor_because_content_modified()
            logging.debug("Added Intro to VerseOrder of (%s)", self.filename)

        if "Intro" not in self.content:
            intro = {"Intro": [["Intro"], []]}
            self.content = {**intro, **self.content}
            self.update_editor_because_content_modified()
            logging.debug("Added Intro Block to (%s)", self.filename)

    def fix_header_church_song_id_caps(self) -> bool:
        """Function which replaces any caps of e.g. ChurchSongId to ChurchSongID in header keys."""
        if "ChurchSongID" not in self.header:
            for i in self.header:
                if "ChurchSongID".upper() == i.upper():
                    self.header["ChurchSongID"] = self.header[i]
                    del self.header[i]
                    logging.debug(
                        "Changed Key from %s to ChurchSongID in %s", i, self.filename
                    )
                    self.update_editor_because_content_modified()
                    return True
        return False

    def fix_header_ccli_caps(self) -> bool:
        """Function which replaces any caps of e.g. ccli Ccli CCLi to CCLI in header keys.

        Args:
            if updated
        """
        if "CCLI" not in self.header:
            for i in self.header:
                if i.upper() == "CCLI":
                    self.header["CCLI"] = self.header[i]
                    del self.header[i]
                    logging.debug("Changed Key from %s to CCLI in %s", i, self.filename)
                    self.update_editor_because_content_modified()
                    return True
        return False

    def validate_headers_illegal_removed(self, fix: bool = False) -> bool:
        """Checks if all illegeal headers are removed and optionally fixes it by removing illegal ones.

        Args:
            fix: bool whether should be fixed
        Returns:
            if all illegal headers are removed
        """
        for key in list(self.header.keys()):
            if key in SngIllegalHeader:
                if fix:
                    self.header.pop(key)
                    self.update_editor_because_content_modified()
                    logging.debug(
                        "Removed %s from (%s) as illegal header", key, self.filename
                    )
                else:
                    logging.debug(
                        "Not fixing illegal header %s in (%s)", key, self.filename
                    )
                    return False
        return True

    def fix_songbook_from_filename(self) -> bool:
        """Function used to try to fix the songbook and churchsong ID based on filename.

        gets first space separated block of filename as reference number
        1. checks if this part contains only numbers and apply fix from fix_song_book_with_numbers
        2. otherwise writes an empty Songbook and ChurchSongID if no prefix
        3. or loggs error for invalid format if prefix is given but no matching number found

        Returns:
            if something was updated
        """
        first_part_of_symbol = self.filename.split(" ")[0]
        songbook_before_change = self.header.get("Songbook", "NOT SET")

        # Filename starts with number
        if all(
            digit in SNG_DEFAULTS.SngTitleNumberChars for digit in first_part_of_symbol
        ):
            return self.fix_song_book_with_numbers(number_string=first_part_of_symbol)

        if self.songbook_prefix != "":  # Not empty Prefix
            # If the file should follow a songbook prefix logic
            if self.songbook_prefix in SNG_DEFAULTS.KnownSongBookPrefix:
                logging.warning(
                    "Missing required digits as first block in filename %s - can't fix songbook",
                    self.filename,
                )
            else:
                logging.warning(
                    "Unknown Songbook Prefix - can't complete fix songbook of %s",
                    self.filename,
                )

        # No Prefix or Number
        if not (
            self.header.get("Songbook", None) == " "
            and self.header.get("ChurchSongID", None) == " "
        ):
            self.header["Songbook"] = " "
            self.header["ChurchSongID"] = " "
            logging.debug(
                "Corrected Songbook / ChurchSongID from (%s) to (%s) in %s",
                songbook_before_change,
                self.header["Songbook"],
                self.filename,
            )
            self.update_editor_because_content_modified()
            return True
        return False

    def fix_song_book_with_numbers(self, number_string: str) -> bool:
        """Subfunction used for fixing songbook entries based on filename space separated first part which contains numbers only.

        Args:
            number_string: the text line which should be checked usally a number

        Returns:
            if something was updated
        """
        songbook_before_change = self.header.get("Songbook", "NOT SET")

        # Evangelisches Gesangsbuch - Psalm
        if self.is_eg_psalm():
            self.header["Songbook"] = self.header.get("Songbook", " ")
            self.header["ChurchSongID"] = self.header.get("ChurchSongID", " ")
            logging.info(
                'Psalm "%s" can not be auto corrected - please adjust manually (%s,%s)',
                self.filename,
                self.header["Songbook"],
                self.header["ChurchSongID"],
            )
            return False

        # Feiert Jesus Prefix
        if "FJ" in self.songbook_prefix:
            songbook = self.songbook_prefix + "/" + number_string
        # All other with filename that starts with number
        else:
            songbook = self.songbook_prefix + " " + number_string

        if (
            self.header.get("Songbook", None) != songbook
            or self.header.get("ChurchSongID", None) != songbook
        ):
            self.header["Songbook"] = songbook
            self.header["ChurchSongID"] = songbook
            logging.debug(
                "Corrected Songbook / ChurchSongID from (%s) to (%s) in %s",
                songbook_before_change,
                self.header["Songbook"],
                self.filename,
            )
            self.update_editor_because_content_modified()

            return True
        return False

    def validate_content_slides_number_of_lines(
        self, number_of_lines: int = 4, fix: bool = False
    ) -> bool:
        """Method that checks if slides need to contain # (default 4) lines except for last block which can have less.

        and optionally fixes it

        Params:
            number_of_lines max number of lines allowed per slide
             fix: if it should be attempt to fix itself
        Returns:
            True if something was fixed
        """
        for verse_label, verse_block in self.content.items():  # Iterate all blocks
            # any slide which (except last one) which does not have the correct number of lines is wrong
            has_issues = any(
                len(slide) != number_of_lines for slide in verse_block[1:-1]
            )
            # any last slide which has more lines than desired is wrong
            has_issues |= len(verse_block[-1]) > number_of_lines

            if has_issues and fix:
                logging.debug(
                    "Fixing block length %s in (%s) to %s lines",
                    verse_label,
                    self.filename,
                    number_of_lines,
                )

                all_lines = list(
                    chain(*verse_block[1:])
                )  # Merge list of all text lines

                # Remove all old text lines except for Verse Marker
                self.content[verse_label] = [verse_block[0]]
                # Append 4 lines per slide as one list - last slide will exceed available lines but simply fill available
                for i in range(0, len(all_lines), number_of_lines):
                    self.content[verse_label].append(all_lines[i : i + number_of_lines])
                has_issues = False
                self.update_editor_because_content_modified()
            if not has_issues:
                continue
            return False
        return True

    def validate_verse_numbers(self, fix: bool = False) -> bool:
        """Method which checks Verse Numbers for numeric parts that are non-standard - e.g. 1b.

        * tries to remove letters in 2nd part if fix is enabled
        * merges consecutive similar parts

        does only work if versemarker exists!
        """
        all_verses_valid = True
        new_content = {}
        for key, verse_block in self.content.items():
            # if block starts with a verse label and some additional information
            verse_label_list = verse_block[0]

            is_valid_verse_label_list = self.is_valid_verse_label_list(verse_label_list)

            if not is_valid_verse_label_list and fix:
                # fix verse label
                old_key = " ".join(verse_label_list)
                new_number = re.sub(r"\D+", "", verse_label_list[1])
                new_label = [verse_label_list[0], new_number]
                new_key = " ".join(new_label)

                # check if new block name already exists
                if new_key in new_content:
                    logging.debug(
                        "\t Appending %s to existing Verse label %s",
                        old_key,
                        new_key,
                    )
                    # if yes, append content and remove old label from verse order
                    new_content[new_key].extend(verse_block[1:])
                    # remove old key from verse order (replacement already exists)
                    self.header["VerseOrder"] = [
                        item for item in self.header["VerseOrder"] if item != old_key
                    ]
                # If it's a new label after fix
                else:
                    logging.debug(
                        "New Verse label from %s to %s in (%s)",
                        old_key,
                        new_key,
                        self.filename,
                    )
                    # if no, rename block in verse order and dict
                    self.header["VerseOrder"] = [
                        new_key if item == old_key else item
                        for item in self.header["VerseOrder"]
                    ]
                    new_content[new_key] = [new_label] + verse_block[1:]
                self.update_editor_because_content_modified()
                continue

            # Any regular block w/o versemarker
            if not is_valid_verse_label_list:
                all_verses_valid &= is_valid_verse_label_list
                logging.debug(
                    "Invalid verse label %s not fixed in (%s)",
                    verse_label_list,
                    self.filename,
                )

            # Keep content because either error was logged or it was valid content
            new_content[key] = verse_block

        self.content = new_content
        return all_verses_valid

    def is_valid_verse_label_list(self, verse_label_list: str) -> bool:
        """Checks if a list extracted from SNG content could be a valid verse label.

        Args:
            verse_label_list: list from content which should be checked

        Returns:
            whether the line is a valid verse_label
        """
        result = verse_label_list[0] in SNG_DEFAULTS.VerseMarker

        if len(verse_label_list) > 1:
            result &= verse_label_list[1].isdigit()

        return result

    def validate_stop_verseorder(
        self, fix: bool = False, should_be_at_end: bool = False
    ) -> bool:
        """Method which checks that a STOP exists in VerseOrder headers and corrects it.

        Params:
            should_be_at_end removes any 'STOP' and makes sure only one at end exists
            fix: bool if it should be attempt to fix itself
        Returns:
            if something is wrong after applying method
        """
        result = True
        # STOP exists but not at end
        if (
            should_be_at_end
            and "STOP" in self.header["VerseOrder"]
            and self.header["VerseOrder"][-1] != "STOP"
        ):
            if fix:
                logging.debug("Removing STOP from %s", self.header["VerseOrder"])
                self.header["VerseOrder"].remove("STOP")
                self.update_editor_because_content_modified()
                logging.debug(
                    "STOP removed at old position in (%s) because not at end",
                    self.filename,
                )
                result = True
            else:
                logging.warning(
                    "STOP from (%s) not at end but not fixed in %s",
                    self.filename,
                    self.header["VerseOrder"],
                )
                result = False

        # STOP missing overall
        if "STOP" not in self.header["VerseOrder"]:
            if fix:
                self.header["VerseOrder"].append("STOP")
                logging.debug(
                    "STOP added at end of VerseOrder of %s: %s",
                    self.filename,
                    self.header["VerseOrder"],
                )
                self.update_editor_because_content_modified()
                result = True
            else:
                result = False
                logging.warning(
                    "STOP missing in (%s) but not fixed in %s",
                    self.filename,
                    self.header["VerseOrder"],
                )
        return result

    def validate_suspicious_encoding(self, fix: bool = False) -> bool:
        """Function that checks the SNG content for suspicious characters which might be result of previous encoding errors.

        utf8_as_iso dict is used to check for common occurances of utf-8 german Umlaut when read as iso8895-1

        Params:
            fix: if method should try to fix the encoding issues
        Returns:
            if no suspicious encoding exists
        """
        # Check headers
        valid_header = self.validate_suspicious_encoding_header(fix=fix)

        # Check content
        valid_content = self.validate_suspicious_encoding_content(fix=fix)

        return valid_header & valid_content

    def validate_suspicious_encoding_header(self, fix: bool = False) -> bool:
        """Function that checks the SNG HEADER for suspicious characters which might be result of previous encoding errors.

        utf8_as_iso dict is used to check for common occurances of utf-8 german Umlaut when read as iso8895-1
        All headers will be checked even if one has an issue

        Params:
            fix: if method should try to fix the encoding issues
        Returns:
            if no suspicious encoding exists
        """
        valid = True

        # Check headers
        for headername, header in self.header.items():
            is_valid, checked_line = validate_suspicious_encoding_str(header, fix=fix)
            if not is_valid:
                valid = False
                logging.info(
                    "Found problematic encoding [%s] in header [%s] in %s",
                    checked_line,
                    headername,
                    self.filename,
                )

        return valid

    def validate_suspicious_encoding_content(self, fix: bool = False) -> bool:
        """Function that checks the SNG CONTENT for suspicious characters which might be result of previous encoding errors.

        utf8_as_iso dict is used to check for common occurances of utf-8 german Umlaut when read as iso8895-1
        Only lines upon first "non-fixed" line will be checked

        Params:
            fix: if method should try to fix the encoding issues
        Returns:
            if no suspicious encoding exists
        """
        for verse in self.content.values():
            text_slides = verse[1:]  # skip verse marker
            for slide_no, slide in enumerate(text_slides):
                for line_no, line in enumerate(slide):
                    is_valid, checked_line = validate_suspicious_encoding_str(
                        line, fix=fix
                    )
                    if not is_valid:
                        logging.info(
                            "Found problematic encoding [%s] in %s %s slide line %s of %s",
                            checked_line,
                            verse[1],
                            slide_no,
                            line_no,
                            self.filename,
                        )
                        return False  # if not fixed can abort on first error
        return True

    def get_id(self) -> int:
        """Helper function accessing ID in header mapping not existant to -1.

        Returns:
            id
        """
        if "id" in self.header:
            return int(self.header["id"])
        return -1

    def set_id(self, new_id: int) -> None:
        """Helper function for easy access to write header ID.

        Args:
            new_id: ID (ideally ChurchTools) which should be set for the specific song
        """
        self.header["id"] = str(new_id)
        self.update_editor_because_content_modified()

    def is_eg_psalm(self) -> bool:
        """Helper function to determine if the song is an EG Psalm.

        Conditions are
        1. must have EG in Songbook Prefix
        2. filename must start with number in correct range
            EG Psalms in EG Württemberg EG 701-758

        Returns:
            if condition applies
        """
        return (
            "EG" in self.songbook_prefix
            and KnownSongBookPsalmRange["EG"][0]
            <= float(self.filename.split(" ")[0])
            <= KnownSongBookPsalmRange["EG"][1]
        )


def validate_suspicious_encoding_str(text: str, fix: bool = False) -> tuple[bool, str]:
    """Function that checks a single text str assuming a utf8 encoded file has been accidentaly written as iso8995-1.

    and replacing common german 'Umlaut' and sz

    Params:
        text: the str to check and or correct
        fix: if method should try to fix the encoding issues
    Returns:
        * bool indicating whether suspicious characters remains
        * text (repaired if fix was True)
    """
    valid = True
    if re.match("Ã¤|Ã¶|Ã¼|Ã\\x84|Ã\\x96|Ã\\x9c|Ã\\x9f", text):
        logging.info("Found problematic encoding in str '%s'", text)
        if fix:
            orginal_text = text
            text = re.sub("Ã¤", "ä", text, count=0)
            text = re.sub("Ã¶", "ö", text, count=0)
            text = re.sub("Ã¼", "ü", text, count=0)
            text = re.sub("Ã\x84", "Ä", text, count=0)
            text = re.sub("Ã\x96", "Ö", text, count=0)
            text = re.sub("Ã\x9c", "Ü", text, count=0)
            text = re.sub("Ã\x9f", "ß", text, count=0)
            if text != orginal_text:
                logging.debug("replaced %s by %s", orginal_text, text)
            else:
                logging.warning("%s - could not be fixed automatically", orginal_text)
        else:
            valid = False
    return valid, text


def get_verse_marker_line(line: str) -> list:
    """Function used to check if a line begins with a verse marker and return respective.

    Needs to begin with Verse Marker and either have no extra content or another block split by space
    Params:
        line: text to check
    Returns:
        True in case matches, otherwise False
    """
    from SNG_DEFAULTS import VerseMarker

    if line.startswith("$$M="):
        return ["$$M=", line[4:]]

    line = line.split(" ")

    # Case with implicit line label which is not verse label yet
    number_of_blocks_if_verse_marker = 2
    if len(line) > number_of_blocks_if_verse_marker:
        return None

    if line[0] in VerseMarker:
        return line

    return None


def contains_songbook_prefix(text: str) -> bool:
    """Helper function to determine whether text contains a songbook prefix.

    Params:
        text: content to check for prefix
    Returns:
        result of check
    """
    result = False
    for prefix in SNG_DEFAULTS.SngSongBookPrefix:
        songbook_regex = r"({}\W+.*)|(.*\W+{})|({}\d+.*)|(.*\d+{})|(^{})|({}$)".format(
            prefix, prefix, prefix, prefix, prefix, prefix
        )
        result |= re.match(songbook_regex, text.upper()) is not None

    return result


def generate_verse_marker_from_line(line: str) -> tuple[list[str, str] | None, str]:
    """Helper which is used to detect a verse marker from a text line.

    Returns no verse_marker and unchanged text if nothing detected

    Args:
        line: text line which shold be analyzed

    Returns:
        list of 2 items
        1. parsed versemarker (None if not detected) e.g. ["Chorus", 1] or ["Bridge",""]]
        2. remaining text
    """
    chorus_prefix = r"(?:(?:R(?:efrain)?)|(?:C(?:horus)?)) ?"
    verse_prefix = r"(?:(?:V(?:erse)?)|(?:S(?:trophe)?)) ?"
    bridge_prefix = r"(?:(?:B(?:ridge)?)) ?"
    combined_prefix = f"{chorus_prefix}|{verse_prefix}|{bridge_prefix}"

    match_groups = re.split(
        rf"^({combined_prefix})?(\d*)(?:[:.]?)?", line, flags=re.IGNORECASE
    )
    verse_marker = None
    text = line
    match_number = match_groups[2]
    number = match_number if match_number else ""

    if (
        (match_groups[1] is None and bool(match_groups[2]))
        or match_groups[1] is not None
        or (match_groups[1] is None and not number)
    ):
        text = match_groups[3]

        if (match_groups[1] is None and match_groups[2]) or re.match(
            verse_prefix, str(match_groups[1])
        ):
            verse_marker = ["Verse", number]
        elif re.match(chorus_prefix, str(match_groups[1])):
            verse_marker = ["Chorus", number]
        elif re.match(bridge_prefix, str(match_groups[1])):
            verse_marker = ["Bridge", number]

    return verse_marker, text.lstrip()
