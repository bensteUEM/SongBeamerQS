"""This file is used to define SngFile class and somee helper methods related to it's usage."""

import abc
import itertools
import logging

logger = logging.getLogger(__name__)


class SngFileLanguagePart(abc.ABC):
    """Part of SngFile class used with language specific actions.

    Args:
        abc: placeholder that this class can not be used on it's own - SngFile should be used instead
    """

    def get_content(self, languages: list[str] | None = None) -> dict:
        """Gets content list of the file.

        Does NOT fix number of lines per slide
        Keeps original song structure even in case of empty parts

        Arguments:
            languages: optional - list of language lines to keep, defaults to all

        Returns:
            content dict with only the languages indicated in argument
        """
        if not languages:
            languages = [None, "##1", "##2", "##3", "##4"]

        block: list
        for block in self.content.values():
            slide: list
            for slide in block[1:]:
                slide[:] = [
                    line
                    for line in slide
                    if self._line_matches_languages(line, languages)
                ]
                # versemarker ???

        return self.content

    @classmethod
    def _line_matches_languages(
        cls, line: str, languages: list[str] | None = None
    ) -> bool:
        """Helper function which checks whether a line matches any of the language marker selections.

        Args:
            line: the line to check
            languages: list of langaugemarkers to check for - None equals no langauge marker. Defaults to All.

        Returns:
            Whether the specified line starts with any of the languagemarkers
        """
        if not languages:
            languages = [None, "##1", "##2", "##3", "##4"]

        if None in languages and not line.startswith("##"):
            return True

        try:
            languages_no_none = languages[:]
            languages_no_none.remove(None)
        except ValueError:
            pass  # do nothing!

        return line.startswith(tuple(languages_no_none))

    def genereate_content_by_lang(self, content: list[list]) -> dict:
        """Generate a new content dict by joining multiple content blocks overwriting the language order.

        This will not overwrite content but provide a new content which could be used

        Args:
            content: list of content blocks, language marker will be overwritten to position in list

        Returns:
            one content list which includes any provided content block with respective language markers
        """
        # TODO@benste: Implement
        # https://github.com/bensteUEM/SongBeamerQS/issues/61
        not_implemented_link = "https://github.com/bensteUEM/SongBeamerQS/issues/61"
        raise NotImplementedError(not_implemented_link)

        return content

    def get_content_unique_lang_markers(self) -> set:
        """Helper which gets the unique language markers explicitly used in the song.

        * Can be None or any combination of ##1 ##2 ##3 ##4
        * number of items equals the number of languages used
        * ignores header LangCount option

        Returns:
            set of all language markers used within the song
        """
        language_markers = []
        block: list
        for block in self.content.values():
            slide: list
            for slide in block[1:]:
                line: str
                for line in slide:
                    if line.startswith("##"):
                        language_markers.append(line[:3])
                    else:
                        language_markers.append(None)

        return set(language_markers)

    def validate_header_language_count(self, fix: bool = False) -> bool:
        """Validate the language count option in header.

        * counts the number of languages explicitly used in content
        * checks if LangCount matches
        if fix LangCount header will be overwritten by number of identified languages
        lines without langauge will count as ##1 in case explicit language markers exist

        leverages get_content_unique_lang_markers in order to get number of languages

        Args:
            fix: should LangCount Header be overwritten? Defaults to False.

        Returns:
            if language_count is valid
        """
        if "LangCount" in self.header:
            languages_current_count = int(self.header["LangCount"])
        else:
            languages_current_count = -1

        languages = self.get_content_unique_lang_markers()
        languages_used_count = len(languages)
        if len(languages) > 1 and None in languages:
            languages_used_count -= 1

        valid = languages_current_count == languages_used_count

        if not valid and fix:
            logger.info(
                "overwriting langauge count from %s to %s",
                languages_current_count,
                languages_used_count,
            )
            self.header["LangCount"] = str(languages_used_count)
            self.update_editor_because_content_modified()
            valid = self.validate_header_language_count(fix=False)

        return valid

    def validate_language_marker(self, fix: bool = False) -> bool:
        """Validate the language markers used in content.

        checks that the number of langauges in content matches the configuration from header

        Args:
            fix: attempt to fix language marker usage. Defaults to False.
            * in case there are no language markers and the expected number is greater ##1 and ##2 will be added alternatly
            * in case some lines do have language markers and others don't the former will apply, skipping lines that already have a language marker
            * this method MUSTN'T be applied on Psalms because they can have different language orders blocks longer than one line

        Returns:
            if language markers match LangCount header
        """
        if self.is_psalm():
            return self.validate_language_marker_psalm(fix=fix)

        languages_expected = int(self.header["LangCount"])

        # if only single language
        if len(self.get_content_unique_lang_markers()) == 1 == languages_expected:
            return True

        language_markers_expected = [f"##{i+1} " for i in range(languages_expected)]
        valid = True
        for block in self.content.values():
            for slide in block[1:]:
                valid &= self.validate_language_marker_slide(
                    slide, language_markers_expected=language_markers_expected, fix=fix
                )
        return valid

    def validate_language_marker_slide(
        self, slide: list[str], language_markers_expected: list, fix: bool = False
    ) -> bool:
        """More complex cases of validate_language_marker.

        Args:
            slide: the slide (list of lines) to check
            language_markers_expected: prepared language markers that should be used
            fix: attempt to fix language marker usage. Defaults to False.

        Returns:
            if language markers match LangCount header
        """
        # reset iterator for each slide
        language_markers_iterator = itertools.cycle(language_markers_expected)
        for index, line in enumerate(slide):
            # skip lines with existing language marker
            if line.startswith("##"):
                continue
            # add next language marker from iterator
            if fix:
                slide[index] = next(language_markers_iterator) + line
                self.update_editor_because_content_modified()
                continue
            return False
        return True

    def validate_language_marker_psalm(self, fix: bool = False) -> bool:  # noqa: C901
        """Method used for language_marker validation of psalms.

        Auto Fixing is not possible!
        Psalms should have 2 or 3 langauges indicated by ##1, ##3 and ##4 but not ##2
        Arguments:
            fix: if fix should be attempted - impossible for psalm!
        Returns:
            if language markers are as expected
        """
        for block in self.content.values():
            for slide in block[1:]:
                for line in slide:
                    if line.startswith(("##1", "##3", "##4")):
                        continue
                    if fix:
                        logger.warning(
                            "Can't fix '%s' line in (%s) because it's a Psalm",
                            line,
                            self.filename,
                        )
                    return False

        return True
