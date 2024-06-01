import logging
from pathlib import Path

import pytest

from SngFile import SngFile


class TestSngLanguage:
    """This class is used to test anything defined in SngFileLanguagePart."""

    def test_sample_file(self) -> None:
        """Checks that sample file is loaded as expceted."""
        path = Path("testData/Test")
        filename = "sample_languages.sng"
        sample_song = SngFile(filename=path / filename)

        expected_lang_count = 2
        assert int(sample_song.header["LangCount"]) == expected_lang_count

    @pytest.mark.parametrize(
        ("filename", "languages"),
        [
            (Path("testData/Test") / "sample_languages.sng", [None]),
            (Path("testData/Test") / "sample_languages.sng", [None, "##1", "##2"]),
            (Path("testData/Test") / "sample_languages.sng", ["##1", "##2"]),
            (Path("testData/Test") / "sample_languages.sng", ["##1"]),
            (Path("testData/Test") / "sample_languages.sng", ["##2"]),
            (Path("testData/Test") / "sample_languages.sng", ["##3"]),
        ],
    )
    def test_get_content(self, filename: Path, languages: list[str] | None) -> None:
        """Method which validated the get_content method.

        1. Excecutes method
        2. checks remaining language markers
        3. checks numeric structure of song is still the same

        leverages get_content_unique_lang_markers for validation

        Args:
            languages: _the languages which should be kept_. Defaults to None.
            filename: locationm of sng to use for testing
        """
        sample_song = SngFile(filename=filename)
        expected_blocks = len(sample_song.content)
        expected_slides = [len(block) for block in sample_song.content.values()]

        result_song = SngFile(filename=filename)
        result_song.content = sample_song.get_content(languages=languages)

        # verify remaining language markers
        assert result_song.get_content_unique_lang_markers() - set(languages) == set()

        # verify integrity of song
        result_blocks = len(result_song.content)
        result_slides = [len(block) for block in result_song.content.values()]

        assert expected_blocks == result_blocks
        assert expected_slides == result_slides

    @pytest.mark.parametrize(
        ("filename", "expected_result", "verse"),
        [
            (Path("testData/Test") / "sample_languages.sng", {None}, "Verse 1"),
            (Path("testData/Test") / "sample_languages.sng", {"##1", "##2"}, "Verse 2"),
            (
                Path("testData/EG Psalmen & Sonstiges")
                / "709 Herr, sei nicht ferne.sng",
                {"##1", "##3", None},
                None,
            ),
        ],
    )
    def test_get_content_unique_lang_markers(
        self,
        filename: Path,
        expected_result: set,
        verse: str | None,
    ) -> None:
        """Checks functionality of get_content_unique_lang_markers.

        Using 3. different cases
        1. sample with no verse markers
        2. sample with 2 language versemarkers
        3. psalm sample with ##1 and ##3

        Sample file contains 2 verses, one with and one without language markers
        therefore it is used twice - with one verse only in each case

        Argument

        Args:
            filename: locationm of sng to use for testing
            expected_result: result which is expected
            verse: limit song to the one specified verse only. Defaults to None.
        """
        # 1b. with language markers
        sample_song = SngFile(filename=filename)
        if verse:
            sample_song.content = {verse: sample_song.content[verse]}
        assert expected_result == sample_song.get_content_unique_lang_markers()

    @pytest.mark.parametrize(
        ("line", "languages", "expected_result"),
        [
            ("nix", [None], True),
            ("nix", [None, "##1", "##2"], True),
            ("nix", ["##1", "##2"], False),
            ("nix", ["##1"], False),
            ("nix", ["##2"], False),
            ("##1 text", [None], False),
            ("##1 text", [None, "##1", "##2"], True),
            ("##1 text", ["##1", "##2"], True),
            ("##1 text", ["##1"], True),
            ("##1 text", ["##2"], False),
            ("#header a", [None], True),
            ("#header a", [None, "##1", "##2"], True),
            ("#header a", ["##1", "##2"], False),
            ("#header a", ["##1"], False),
            ("#header a", ["##2"], False),
        ],
    )
    def test__line_matches_languages(
        self, line: str, languages: list[str] | None, expected_result: bool
    ) -> None:
        """Check _line matches_languages with some samples.

        Args:
            line: the line to check
            languages: _the languages which should be kept
            expected_result: bool result to check against
        """
        result = SngFile._line_matches_languages(line=line, languages=languages)  # noqa: SLF001
        assert result == expected_result

    @pytest.mark.parametrize(
        ("filename", "verses", "fix", "expected_result"),
        [
            (Path("testData/Test") / "sample_languages.sng", ["Verse 1"], False, False),
            (Path("testData/Test") / "sample_languages.sng", ["Verse 1"], True, True),
            (Path("testData/Test") / "sample_languages.sng", ["Verse 2"], False, True),
            (
                Path("testData/Test") / "sample_languages.sng",
                ["Verse 2", "Verse 2"],
                False,
                True,
            ),
        ],
    )
    def test_validate_header_language_count(
        self, filename: str, verses: list[str] | None, fix: bool, expected_result: bool
    ) -> None:
        """Method testing different cases of validate_header_language_count.

        Args:
            filename: the file to use
            verses: limit song to the specified list of verses only.
            fix: if fix should be attempted_
            expected_result: _description_
        """
        sample_song = SngFile(filename=filename)
        sample_song.content = {
            key: value for key, value in sample_song.content.items() if key in verses
        }
        result = sample_song.validate_header_language_count(fix=fix)
        assert expected_result == result

    @pytest.mark.parametrize(
        ("filename", "verses", "fix", "expected_result"),
        [
            (Path("testData/Test") / "sample_languages.sng", ["Verse 2"], False, True),
            (Path("testData/Test") / "sample_languages.sng", ["Verse 3"], False, False),
            (Path("testData/Test") / "sample_languages.sng", ["Verse 4"], True, True),
            (Path("testData/Test") / "sample_languages.sng", ["Verse 5"], False, False),
        ],
    )
    def test_validate_language_marker(
        self, filename: str, verses: list[str] | None, fix: bool, expected_result: bool
    ) -> None:
        """Checking different params with validate_language_marker.

        Args:
            filename: the file to use
            verses: the verse selection to use as content
            fix: if fix attempt should be performed
            expected_result: if should be valid after function run
        """
        sample_song = SngFile(filename=filename)
        sample_song.content = {
            key: value for key, value in sample_song.content.items() if key in verses
        }
        result = sample_song.validate_language_marker(fix=fix)
        assert expected_result == result

        # check language marker equals Lang x. text in line of verse 3-5
        if fix:
            for block in sample_song.content.values():
                if block[1][2] in [3, 4, 5]:
                    continue
                for slide in block[1:]:
                    self.helper_language_marker_as_expected(slide=slide)

    def helper_language_marker_as_expected(self, slide: list[str]) -> bool:
        """Helper for test_validate_language_marker.

        Validates marker matches syntax for all lines
        e.g. '##2 Lang 2.1' ma

        Args:
            slide: one slide with all it's text lines

        Returns:
            if everything is as expected
        """
        for line in slide:
            assert line.startswith("##")
            text_items = line.split(" ")
            marked_language = text_items[0][2:]
            expected_language = text_items[2][:1]
            assert marked_language == expected_language

    @pytest.mark.usefixtures("caplog")
    def test_validate_language_marker_psalm(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Checking psalm cases of validate_language_marker.

        Psalms should not be fixable or already valid
        complete sample should be invalid because of error
        attempt to fix it should log an "unfixable"
        looking at first 2 slides of verse only it should be valid
        """
        filepath = Path("testData/EG Psalmen & Sonstiges")
        filename = "709 Herr, sei nicht ferne.sng"
        sample_song = SngFile(filename=filepath / filename, songbook_prefix="EG")
        result = sample_song.validate_language_marker_psalm(fix=False)
        assert not result

        caplog.set_level(logging.INFO)
        result = sample_song.validate_language_marker_psalm(fix=True)
        assert not result
        assert len(caplog.records) > 0

        # reduced scope should be valid
        sample_song.content["Verse"] = sample_song.content["Verse"][0:2]
        result = sample_song.validate_language_marker_psalm(fix=False)
        assert result

    @pytest.mark.usefixtures("caplog")
    def test_validate_langauge_marker_indirect_psalm(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Checks that running validate_langauge_marker results in psalm specific log message."""
        filepath = Path("testData/EG Psalmen & Sonstiges")
        filename = "709 Herr, sei nicht ferne.sng"
        sample_song = SngFile(filename=filepath / filename, songbook_prefix="EG")

        caplog.set_level(logging.INFO)
        result = sample_song.validate_language_marker(fix=True)
        assert not result

        problematic_line = "1 Unsere V�ter hofften auf dich;"
        expected_log = "WARNING  SngFileLanguagePart:SngFileLanguagePart.py:229 "
        f"Can't fix '{problematic_line}' line"
        f" in ({sample_song.filename}) because it's a Psalm\n"

        assert expected_log in caplog.text
