"""This module includes utilities used independant of sng instances."""

import logging
import re

import SNG_DEFAULTS


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
