"""This file is used to define SngFile class and somee helper methods related to it's usage."""

import abc
import logging
from io import TextIOWrapper
from pathlib import Path

from SNG_DEFAULTS import SngDefaultHeader


class SngFileParserPart(abc.ABC):
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
