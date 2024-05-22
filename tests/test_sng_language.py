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
        ("filename", "expected_result", "verse"),
        [
            (Path("testData/Test") / "sample_languages.sng", {None}, "Verse 1"),
            (Path("testData/Test") / "sample_languages.sng", {"##1", "##2"}, "Verse 2"),
            (
                Path("testData/EG Psalmen & Sonstiges")
                / "709 Herr, sei nicht ferne.sng",
                {"##1", "##3"},
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
