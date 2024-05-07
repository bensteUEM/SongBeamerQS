"""This file is used to define SngFile class and somee helper methods related to it's usage."""

import logging
import re
from itertools import chain

import SNG_DEFAULTS
from sng_utils import generate_verse_marker_from_line, validate_suspicious_encoding_str
from SngFileHeaderValidationPart import SngFileHeaderValidation
from SngFileParserPart import SngFileParserPart


class SngFile(SngFileParserPart, SngFileHeaderValidation):
    """Main class that defines one single SongBeamer SNG file."""

    def __init__(self, filename: str, songbook_prefix: str = "") -> None:
        """Default Construction for a SNG File and it's params.

        Args:
            filename: filename with optional directory which should be opened
            songbook_prefix: prefix of songbook e.g. EG. Defaults to "".
        """
        super().__init__(filename=filename, songbook_prefix=songbook_prefix)

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
