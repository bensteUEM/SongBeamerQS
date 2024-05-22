"""This file is used to define SngFile class and somee helper methods related to it's usage."""

import abc
import logging

logger = logging.getLogger(__name__)


class SngFileLanguagePart(abc.ABC):
    """Part of SngFile class used with language specific actions.

    Args:
        abc: placeholder that this class can not be used on it's own - SngFile should be used instead
    """

    def get_content(self, languages: list[str] | None = None) -> dict:
        """Gets content list of the file.

        Arguments:
            languages: optional - list of language lines to keep, defaults to all

        Returns:
            content dict with only the languages indicated in argument
        """
        if not languages:
            languages = [None, "##1", "##2", "##3", "##4"]
        # TODO@benste: Implement
        # https://github.com/bensteUEM/SongBeamerQS/issues/61
        not_implemented_link = "https://github.com/bensteUEM/SongBeamerQS/issues/61"
        raise NotImplementedError(not_implemented_link)

        return self.content

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

    def validate_language_count(self, fix: bool = False) -> bool:
        """Validate the language count option in header.

        * counts the number of languages explicitly used in content
        * checks if LangCount matches
        if fix LangCount header will be overwritten by number of identified languages

        Args:
            fix: should LangCount Header be overwritten? Defaults to False.

        Returns:
            if language_count is valid
        """
        if fix:
            pass
        # TODO@benste: Implement
        # https://github.com/bensteUEM/SongBeamerQS/issues/61
        not_implemented_link = "https://github.com/bensteUEM/SongBeamerQS/issues/61"
        raise NotImplementedError(not_implemented_link)

    def validate_language_marker(self, fix: bool = False) -> bool:
        """Validate the language markers used in content.

        Args:
            fix: attempt to fix language marker usage Defaults to False.

        Returns:
            if language markers match LangCount header
        """
        if fix:
            pass
        # TODO@benste: Implement
        # https://github.com/bensteUEM/SongBeamerQS/issues/61
        not_implemented_link = "https://github.com/bensteUEM/SongBeamerQS/issues/61"
        raise NotImplementedError(not_implemented_link)
