"""This file is used to define SngFile class and somee helper methods related to it's usage."""

import abc
import logging
import re
from pathlib import Path

import SNG_DEFAULTS
from SNG_DEFAULTS import KnownSongBookPsalmRange, SngIllegalHeader
from sng_utils import contains_songbook_prefix

logger = logging.getLogger(__name__)


class SngFileHeaderValidation(abc.ABC):
    """Part of SngFile class that defines methods used to validate and fix headers."""

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

    def validate_headers(self) -> bool:
        """Checks if all required headers are present.

        Logs info in case something is missing and returns respective list of keys

        Args:
            bool indicating if anything is missing
        """
        missing = [
            key for key in SNG_DEFAULTS.SngRequiredHeader if key not in self.header
        ]

        if self.is_psalm() and "Bible" not in self.header:
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
            logger.warning(
                "Missing required headers in (%s) %s", self.filename, missing
            )

        return result

    def validate_header_title(self, fix: bool = False) -> bool:  # noqa: C901
        """Validation method for title header.

        checks:
        * if title exists
        * existance of SngTitleNumberChars
        * existance of contains_number

        Anything that has no Songbook prefix could be special (e.g. is psalm) is skipped as valid

        Args:
            fix: if it should be attempt to fix itself

        Returns:
            if Title is valid at end of method
        """
        title = self.header.get("Title", "")
        error_message = None

        if not title:
            error_message = f"Song without a Title in Header: {self.filename}"

        elif not self.songbook_prefix or self.is_psalm():
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
            logger.warning(error_message)
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
            logger.warning(error_message)
        else:
            for part in title_as_list:
                if all(
                    digit.upper() in SNG_DEFAULTS.SngTitleNumberChars for digit in part
                ) or contains_songbook_prefix(part):
                    title_as_list.remove(part)
                    self.update_editor_because_content_modified()
            self.header["Title"] = " ".join(title_as_list)
            logger.debug(
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
        songbook_valid = True

        # Validate Headers
        if "ChurchSongID" not in self.header or "Songbook" not in self.header:
            # Hint - ChurchSongID ' '  or '' is automatically removed from SongBeamer on Editing in Songbeamer itself
            songbook_valid = False
        else:
            # All entries that are consistent and not part of knwon songbooks are considered valids
            songbook_valid = self.header["ChurchSongID"] == self.header["Songbook"]

            if (
                self.songbook_prefix in self.header["Songbook"]
                and self.songbook_prefix != ""
            ):
                # Check that songbook_prefix is part of songbook
                songbook_valid = self.songbook_prefix in self.header["Songbook"]

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

        logger.debug("songbook_valid == %s", songbook_valid)

        if fix and not songbook_valid:
            self.fix_header_church_song_id_caps()
            self.fix_songbook_from_filename()
            songbook_valid = self.validate_header_songbook(fix=False)

        if not songbook_valid:
            logger.error(
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
            self.is_psalm()
            and self.header["BackgroundImage"] != "Evangelisches Gesangbuch.jpg"
        ):
            error_message = (
                f"Incorrect background for Psalm in ({self.filename}) not fixed"
            )

        if not bool(error_message):
            return True

        if fix:
            return self.fix_header_background()

        logger.debug(error_message)
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
        if self.is_psalm():
            self.header["BackgroundImage"] = "Evangelisches Gesangbuch.jpg"
            logger.debug("Fixing background for Psalm in (%s)", self.filename)
            self.update_editor_because_content_modified()
            return True

        logger.warning("Can't fix background for (%s)", self.filename)
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

        logger.warning("Verse Order and Blocks don't match in %s", self.filename)
        if "VerseOrder" not in self.header:
            logger.debug("Missing VerseOrder in (%s)", self.filename)
        else:
            logger.debug("\t Not fixed: Order: %s", str(self.header["VerseOrder"]))
            logger.debug("\t Not fixed: Blocks: %s", list(self.content.keys()))

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

        logger.debug(
            "Fixed VerseOrder to %s in (%s)",
            self.header["VerseOrder"],
            self.filename,
        )
        self.update_editor_because_content_modified()
        return True

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

    def fix_header_church_song_id_caps(self) -> bool:
        """Function which replaces any caps of e.g. ChurchSongId to ChurchSongID in header keys."""
        if "ChurchSongID" not in self.header:
            for i in self.header:
                if "ChurchSongID".upper() == i.upper():
                    self.header["ChurchSongID"] = self.header[i]
                    del self.header[i]
                    logger.debug(
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
                    logger.debug("Changed Key from %s to CCLI in %s", i, self.filename)
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
                    logger.debug(
                        "Removed %s from (%s) as illegal header", key, self.filename
                    )
                else:
                    logger.debug(
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
                logger.warning(
                    "Missing required digits as first block in filename %s - can't fix songbook",
                    self.filename,
                )
            else:
                logger.warning(
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
            logger.debug(
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
        if self.is_psalm():
            self.header["Songbook"] = self.header.get("Songbook", " ")
            self.header["ChurchSongID"] = self.header.get("ChurchSongID", " ")
            logger.info(
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
            logger.debug(
                "Corrected Songbook / ChurchSongID from (%s) to (%s) in %s",
                songbook_before_change,
                self.header["Songbook"],
                self.filename,
            )
            self.update_editor_because_content_modified()

            return True
        return False

    def validate_header_stop_verseorder(
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
                logger.debug("Removing STOP from %s", self.header["VerseOrder"])
                self.header["VerseOrder"].remove("STOP")
                self.update_editor_because_content_modified()
                logger.debug(
                    "STOP removed at old position in (%s) because not at end",
                    self.filename,
                )
                result = True
            else:
                logger.warning(
                    "STOP from (%s) not at end but not fixed in %s",
                    self.filename,
                    self.header["VerseOrder"],
                )
                result = False

        # STOP missing overall
        if "STOP" not in self.header["VerseOrder"]:
            if fix:
                self.header["VerseOrder"].append("STOP")
                logger.debug(
                    "STOP added at end of VerseOrder of %s: %s",
                    self.filename,
                    self.header["VerseOrder"],
                )
                self.update_editor_because_content_modified()
                result = True
            else:
                result = False
                logger.warning(
                    "STOP missing in (%s) but not fixed in %s",
                    self.filename,
                    self.header["VerseOrder"],
                )
        return result

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
                logger.info(
                    "Found problematic encoding [%s] in header [%s] in %s",
                    checked_line,
                    headername,
                    self.filename,
                )

        return valid

    def is_psalm(self) -> bool:
        """Helper function to determine if the song is a Psalm.

        this means it is allowed to have numbers in title
        and songbook can not be auto fixed because of combination.

        Conditions are
        1. must have Songbook Prefix which is defined in KnownSongBookPsalmRange
        2. filename must start with number in correct range
            EG Psalms in EG Württemberg EG 701-758

        Returns:
            if condition applies
        """
        songbook_prefix = next(
            (
                prefix
                for prefix in KnownSongBookPsalmRange
                if prefix in self.songbook_prefix
            ),
            None,
        )

        if not songbook_prefix:
            return False

        return (
            KnownSongBookPsalmRange[songbook_prefix]["start"]
            <= float(self.filename.split(" ")[0])
            <= KnownSongBookPsalmRange[songbook_prefix]["end"]
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
        logger.info("Found problematic encoding in str '%s'", text)
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
                logger.debug("replaced %s by %s", orginal_text, text)
            else:
                logger.warning("%s - could not be fixed automatically", orginal_text)
        else:
            valid = False
    return valid, text
