"""This module is used to run the code.

defining some "activites" reading local files and connecting to a server
It mainly works based on df comparison
"""

import logging
import os.path
import time
from pathlib import Path

import pandas as pd
from ChurchToolsApi import ChurchToolsApi

import SNG_DEFAULTS
from secure.config import ct_domain, ct_token  # local config ommited from github repo
from SngFile import SngFile


def parse_sng_from_directory(
    directory: str, songbook_prefix: str = "", filenames: list[str] | None = None
) -> list[SngFile]:
    """Method which reads all SNG Files from a directory and adds missing default values if missing.

    Params:
        directory: directory to read from
        songbook_prefix: which should be used for Songbook number - usually related to directory
        filenames: optional list of filenames which should be covered - if none all from directory will be read
    Returns:
        list of SngFile items read from the directory
    """
    if filenames is None:
        filenames = []
    logging.info("Parsing: %s", directory)
    logging.info("With Prefix: %s", songbook_prefix)

    result = []
    directory_list = filter(
        lambda x: x.endswith((".sng", ".SNG", ".Sng")), os.listdir(directory)
    )

    if len(filenames) > 0:
        directory_list = filenames

    for sng_filename in directory_list:
        current_song = SngFile(directory + "/" + sng_filename, songbook_prefix)
        if "Editor" not in current_song.header:
            current_song.header["Editor"] = SNG_DEFAULTS.SngDefaultHeader["Editor"]
            logging.info("Added missing Editor for: %s", sng_filename)
        result.append(current_song)
    return result


def validate_all_headers(df_to_change: pd.DataFrame, fix: bool = False) -> pd.Series:
    """Method to start validation for all headers.

    1. Validate Title
    2. Validate all Songbook Entries
    3. Remove all Illegal headers
    4. Psalm Backgrounds
    5. Check that all required headers are present

    Params:
        df_to_change: Dataframe which should me used
        fix: boolean if data should be fixed - so far only applies for remove illegal headers and songbook fixing
    Returns:
        boolean Series with True for all entries that have no issues
    """
    logging.info("Starting validate_all_headers(%s)", fix)

    # 1. Validate Title
    logging.info("Starting validate_header_title(%s)", fix)
    headers_valid = df_to_change["SngFile"].apply(
        lambda x: x.validate_header_title(fix)
    )

    # 2. Validate Songbook Entries
    logging.info("Starting validate_header_songbook(%s)", fix)
    headers_valid &= df_to_change["SngFile"].apply(
        lambda x: x.validate_header_songbook(fix)
    )

    # 3. Remove all Illegal headers
    logging.info("Starting validate_headers_illegal_removed(%s)", fix)
    headers_valid &= df_to_change["SngFile"].apply(
        lambda x: x.validate_headers_illegal_removed(fix)
    )

    # 4. fix caps of CCLI entry if required
    df_to_change["SngFile"].apply(lambda x: x.fix_header_ccli_caps())

    # Set Background for all Psalm entries
    psalms_select = df_to_change["SngFile"].apply(lambda x: x.is_psalm())
    logging.info(
        "Starting validate_header_background(%s) for %s psalms", fix, sum(psalms_select)
    )
    headers_valid &= df_to_change[psalms_select]["SngFile"].apply(
        lambda x: x.validate_header_background(fix)
    )

    # 6. Check that all required headers are present
    logging.info("Starting validate_headers()")
    df_to_change["SngFile"].apply(lambda x: x.validate_headers())

    return headers_valid


def read_songs_to_df(testing: bool = False) -> pd.DataFrame:
    """Default method which reads all known directories used at Evangelische Kirchengemeinde Baiersbronn.

    requires all directories from SNG_DEFAULTS to be present
    Arguments:
        * testing: if SNG_DEFAULTS.KnownDirectory or "testData/" should be used
    """
    songs_temp = []

    for key, value in SNG_DEFAULTS.KnownFolderWithPrefix.items():
        if testing:
            dirname = "testData/" + key
            if not Path(dirname).exists():
                continue
        else:
            dirname = SNG_DEFAULTS.KnownDirectory + key
        dirprefix = value
        songs_temp.extend(
            parse_sng_from_directory(directory=dirname, songbook_prefix=dirprefix)
        )

    result_df = pd.DataFrame(songs_temp, columns=["SngFile"])
    result_df["filename"] = ""
    result_df["path"] = ""

    for index, value in result_df["SngFile"].items():
        result_df.loc[(index, "filename")] = value.filename
        result_df.loc[(index, "path")] = value.path
    return result_df


def get_ct_songs_as_df(api: ChurchToolsApi) -> pd.DataFrame:
    """Helper function reading all songs into a df.

    Params:
        api: reference to a churchtools system
    Returns:
        Dataframe with all Songs from ChurchTools Instance
    """
    songs = api.get_songs()
    return pd.json_normalize(songs)


def generate_title_column(df_to_change: pd.DataFrame) -> None:
    """Method used to generate the 'Title' column for all items in a df based on the headers.

    Params:
        df_to_change: Dataframe which should be used
    """
    for index, value in df_to_change["SngFile"].items():
        if "Title" in value.header:
            df_to_change.loc[(index, "Title")] = value.header["Title"]
        else:
            df_to_change.loc[(index, "Title")] = None
            logging.info("Song without a Title in Header: %s", value.filename)


def generate_songbook_column(df_to_change: pd.DataFrame) -> pd.DataFrame:
    """Method used to generate the 'Songbook' and 'ChurchSongID' columns on all items in a df based on the headers.

    Currently works inplace, but also returns the df reference

    Params:
        df_to_change: Dataframe which should me used
    Returns:
        df with Songbook and ChurchSongID columns
    """
    df_to_change["Songbook"] = df_to_change["SngFile"].apply(
        lambda x: x.header.get("Songbook", None)
    )
    df_to_change["ChurchSongID"] = df_to_change["SngFile"].apply(
        lambda x: x.header.get("ChurchSongID", None)
    )
    return df_to_change


def generate_background_image_column(df_to_change: pd.DataFrame) -> None:
    """Method used to generate the 'BackgroundImage' column for all items in a df based on the headers.

    Params:
        df_to_change: Dataframe which should me used
    """
    for index, value in df_to_change["SngFile"].items():
        if "BackgroundImage" in value.header:
            df_to_change.loc[(index, "BackgroundImage")] = value.header[
                "BackgroundImage"
            ]


def generate_ct_compare_columns(df_sng: pd.DataFrame) -> None:
    """Method used to generate the "id", 'name', 'category.name' for a local SNG Dataframe.

    in order to match columns used in ChurchTools Dataframe

    Params:
        df_sng: Dataframe generated from SNG Files which which should me used
    """
    df_sng["id"] = df_sng["SngFile"].apply(lambda x: x.get_id())
    df_sng["name"] = df_sng["filename"].apply(lambda x: x[:-4])
    df_sng["category.name"] = df_sng["SngFile"].apply(lambda x: x.path.name)


def clean_all_songs(df_sng: pd.DataFrame) -> pd.DataFrame:
    """Helper function which runs cleaning methods for sng files on a dataframe.

    Arguments:
        df_sng: Dataframe to work on - must have SngFile instances as attribute column
    Returns:
        a copy of the original dataframe with cleaning improvements applied
    """
    df_result = df_sng.copy()

    logging.info("starting validate_verse_order_coverage() with fix")
    df_result["SngFile"].apply(lambda x: x.validate_verse_order_coverage(fix=True))

    logging.info("starting fix_intro_slide()")
    df_result["SngFile"].apply(lambda x: x.fix_intro_slide())

    # Fixing without auto moving to end because sometimes on purpose, and cases might be
    logging.info("starting validate_stop_verseorder(fix=True, should_be_at_end=False)")
    df_result["SngFile"].apply(
        lambda x: x.validate_stop_verseorder(fix=True, should_be_at_end=False)
    )
    # Logging cases that are not at end ...
    # logging.info('starting validate_stop_verseorder(fix=False, should_be_at_end=True)')
    # df_sng['SngFile'].apply(lambda x: x.validate_stop_verseorder(fix=False, should_be_at_end=True))

    logging.info("starting validate_verse_numbers() with fix")
    df_result["SngFile"].apply(lambda x: x.validate_verse_numbers(fix=True))

    logging.info("starting validate_content_slides_number_of_lines() with fix")
    df_result["SngFile"].apply(
        lambda x: x.validate_content_slides_number_of_lines(fix=True)
    )

    validate_all_headers(df_result, True)

    return df_result


def write_df_to_file(df_sng: pd.DataFrame, target_dir: str | None = None) -> None:
    """Write files to either it's original main directory or use a separate dir.

    Params:
        target_dir: e.g. './output' to write output into a separate folder
    """
    if target_dir:
        target_path = Path(target_dir)

        logging.info("starting write_path_change(%s)", target_path)
        df_sng["SngFile"].apply(lambda x: x.write_path_change(target_path))

    logging.info("starting write_file()")
    df_sng["SngFile"].apply(lambda x: x.write_file())


def check_ct_song_categories_exist_as_folder(
    ct_song_categories: list[str], path: str
) -> bool:
    """Method which check whether all Song Categories of ChurchTools exist in the specified folder.

    Params:
        ct_song_categories: List of all ChurchTools Song categories
        path: for local files
    Returns:
        if all CT categories exist as folder in local path
    """
    logging.debug("checking categories %s in %s", ct_song_categories, path)
    local_directories = os.listdir(path)

    for category in ct_song_categories:
        if category not in local_directories:
            logging.warning("Missing CT category %s in %s", category, path)
            return False

    return True


def validate_ct_songs_exist_locally_by_name_and_category(
    df_ct: pd.DataFrame, df_sng: pd.DataFrame
) -> pd.DataFrame:
    """Function which checks that all song loaded from ChurchTools as DataFrame do exist locally.

    Uses Name and Category to match them - does not compare IDs !
    And logs warning for all elements that can not be mapped
    Can be used to identify changes in ChurchTools that were not updated locally

    Params:
        df_ct: DataFrame with all columns from a JSON response getting all songs from CT
        df_sng: DataFrame with all local SNG files with headings matching CT Dataframe
    Returns:
        reference to merged Dataframe
    """
    generate_ct_compare_columns(df_sng)

    logging.info("validate_ct_songs_exist_locally_by_name_and_category()")
    df_ct_join_name = df_sng.merge(
        df_ct, on=["name", "category.name"], how="right", indicator=True
    )

    issues = df_ct_join_name[df_ct_join_name["_merge"] != "both"].sort_values(
        by=["category.name", "name"]
    )
    for issue in issues[["name", "category.name", "id_y"]].iterrows():
        logging.warning(
            "Song (%s) in category (%s) exists as ChurchTools ID=%s but not matched locally",
            issue[1]["name"],
            issue[1]["category.name"],
            issue[1]["id_y"],
        )

    return df_ct_join_name


def validate_ct_songs_exist_locally_by_id(
    df_ct: pd.DataFrame, df_sng: pd.DataFrame
) -> pd.DataFrame:
    """Function which checks that all song loaded from ChurchTools as DataFrame do exist locally.

    Uses only ID to match them - does not compare name or cateogry !
    And logs warning for all elements that can not be mapped
    Can be used to identify changes in ChurchTools that were not updated locally

    Params:
        df_ct: DataFrame with all columns from a JSON response getting all songs from CT
        df_sng: DataFrame with all local SNG files with headings matching CT Dataframe
    Returns:
        reference to merged Dataframe
    """
    # prep df id, category and name columns
    generate_ct_compare_columns(df_sng)

    logging.info("validate_ct_songs_exist_locally_by_id()")
    df_ct_join_id = df_sng.merge(df_ct, on=["id"], how="right", indicator=True)

    issues = df_ct_join_id[df_ct_join_id["_merge"] != "both"].sort_values(
        by=["category.name_y", "name_y"]
    )
    for issue in issues[["name_y", "category.name_y", "id"]].iterrows():
        logging.warning(
            "Song (%s) in category (%s) exists with ChurchTools ID=%s online but ID not matched locally",
            issue[1]["name_y"],
            issue[1]["category.name_y"],
            issue[1]["id"],
        )

    return df_ct_join_id


def add_id_to_local_song_if_available_in_ct(
    df_sng: pd.DataFrame, df_ct: pd.DataFrame
) -> None:
    """Helper function which write the ID of into each SNG file that.

    * does not have a valid ChurchTools Song ID
    * AND does have a match using name and category comparison with ChurchTools Dataframe

    Params:
        df_sng: All local songs to check - a copy i used for processing ...
        df_ct:  All known songs from ChurchTools
    """
    logging.info("Starting add_id_to_local_song_if_available_in_ct()")
    logging.critical(
        "This function might destroy your data in case a songname exists twice in one songbook #13"
    )
    # TODO (bensteUEM):  Extend functionality of add_id_to_local_song_if_available_in_ct()
    # https://github.com/bensteUEM/SongBeamerQS/issues/13

    compare_by_id_df = validate_ct_songs_exist_locally_by_id(df_ct, df_sng)

    # Part used to overwrite local IDs with CT name_cat in case it exists in CT
    ct_missing_by_id_df = compare_by_id_df[
        compare_by_id_df["_merge"] == "right_only"
    ].copy()
    ct_missing_by_id_df = ct_missing_by_id_df.drop(
        ["name_x", "category.name_x", "_merge"], axis=1
    )
    ct_missing_by_id_df = ct_missing_by_id_df.rename(
        columns={"name_y": "name", "category.name_y": "category.name"}
    )
    overwrite_id_by_name_cat = validate_ct_songs_exist_locally_by_name_and_category(
        ct_missing_by_id_df, df_sng
    )

    for _index, row in overwrite_id_by_name_cat.iterrows():
        if isinstance(row["SngFile_x"], SngFile):
            row["SngFile_x"].set_id(row["id_y"])
            logging.debug(
                "Prepare overwrite id %s for song %s with new id %s",
                row["id_y"],
                row["filename_x"],
                row["id_y"],
            )
        else:
            logging.warning(
                'CT song ID= %s from (%s) with title "%s" not found locally',
                row["id_y"],
                row["category.name"],
                row["name"],
            )

    missing_files = overwrite_id_by_name_cat["SngFile_x"].apply(
        lambda x: not isinstance(x, SngFile)
    )
    overwrite_id_by_name_cat[~missing_files]["SngFile_x"].apply(
        lambda x: x.write_file()
    )


def download_missing_online_songs(
    df_sng: pd.DataFrame, df_ct: pd.DataFrame, ct_api_reference: ChurchToolsApi
) -> bool:
    """Function which will check which songs are missing (by ID) and tries to download them to the respective folders.

    It is highly recommended to execute add_id_to_local_song_if_available_in_ct() and
    upload_new_local_songs_and_generate_ct_id() before in order to try to match all songs local and avoid duplicates

    Params:
        df_sng: DataFrame with all local files
        df_ct: DataFrame with all online files
        ct_api_reference: direct access to ChurchTools API instance
    Returns:
        Success message
    """
    compare = validate_ct_songs_exist_locally_by_id(df_ct, df_sng)
    song_path = compare[compare["path"].notna()].iloc[0]["path"]
    collection_path = song_path.parent

    ids = compare[compare["SngFile"].apply(lambda x: not isinstance(x, SngFile))]["id"]

    is_successful = True
    for song_id in ids:
        song = ct_api_reference.get_songs(song_id=song_id)[0]
        logging.debug(
            'Downloading CT song id=%s "%s" (%s)',
            song_id,
            song["name"],
            song["category"],
        )

        default_arrangement_id = next(
            item["id"] for item in song["arrangements"] if item["isDefault"] is True
        )
        category_name = song["category"]["name"]
        file_path_in_collection = Path(f"{collection_path}/{category_name}")
        filename = f"{song['name']}.sng"

        if Path.exists(Path("{file_path_in_collection}/{filename}")):
            logging.warning(
                "Local file %s from CT ID %s does already exist - try automatch instead!",
                filename,
                song_id,
            )
            is_successful &= False
            continue

        result = ct_api_reference.file_download(
            filename=filename,
            domain_type="song_arrangement",
            domain_identifier=default_arrangement_id,
            target_path=str(file_path_in_collection),
        )
        if result:
            logging.debug(
                "Downloaded %s into %s from CT IT %s",
                filename,
                file_path_in_collection,
                song_id,
            )
        else:
            logging.debug(
                "Failed to download %s into %s from CT IT %s",
                filename,
                file_path_in_collection,
                song_id,
            )
        is_successful &= result

    return is_successful


def upload_new_local_songs_and_generate_ct_id(
    df_sng: pd.DataFrame, df_ct: pd.DataFrame, default_tag_id: int = 52
) -> None:
    """Helper Function which creates new ChurchTools Songs for all SNG Files from dataframe which don't have a song ID.

    Iterates through all songs in df_sng that don't match
    New version of the SNG file including the newly created id is overwritten locally

    Param:
        df_sng: Pandas DataFrame with SNG objects that should be checked against
        df_ct: Pandas DataFrame with Information retrieved about all ChurchTools Songs
        default_tag_id: default ID used to tag new songs - depends on instance of churchtools used !
    """
    generate_ct_compare_columns(df_sng)

    to_upload = df_sng.merge(df_ct, on=["id"], how="left", indicator=True)
    to_upload = to_upload[to_upload["_merge"] == "left_only"]

    api = ChurchToolsApi(domain=ct_domain, ct_token=ct_token)
    song_category_dict = api.get_song_category_map()

    for _index, row in to_upload.iterrows():
        title = row["filename"][:-4]
        category_id = song_category_dict[row["category.name_x"]]

        author1 = row["SngFile"].header.get("Author", "").split(", ")
        author2 = row["SngFile"].header.get("Melody", "").split(", ")

        authors = list(set(author1) | set(author2))
        authors = ", ".join(filter(None, authors))

        ccli = row["SngFile"].header.get("CCLI", "")
        copy = row["SngFile"].header.get("(c)", "")

        logging.info(
            "Uploading Song '%s' with Category ID '%s' from '%s' with (C) from '%s' and CCLI '%s'",
            title,
            category_id,
            authors,
            copy,
            ccli,
        )
        song_id = api.create_song(
            title=title,
            songcategory_id=category_id,
            author=authors,
            copyright=copy,
            ccli=ccli,
        )
        logging.debug("Created new Song with ID '%s'", song_id)
        api.add_song_tag(song_id=song_id, song_tag_id=default_tag_id)
        row["SngFile"].set_id(song_id)
        row["SngFile"].write_file()

        song = api.get_songs(song_id=song_id)[0]

        api.file_upload(
            str(row["path"] / row["filename"]),
            domain_type="song_arrangement",
            domain_identifier=next(
                i["id"] for i in song["arrangements"] if i["isDefault"] is True
            ),
            overwrite=False,
        )


def upload_local_songs_by_id(df_sng: pd.DataFrame, df_ct: pd.DataFrame) -> None:
    """Helper function that overwrites the SNG file of the default arrangement in ChurchTools with same song id.

    Params:
        df_sng: the local song library as dataframe
        df_ct: the remote song library as dataframe
    """
    generate_ct_compare_columns(df_sng)
    to_upload = df_sng.merge(df_ct, on=["id"], how="left", indicator=True)
    api = ChurchToolsApi(domain=ct_domain, ct_token=ct_token)

    to_upload["arrangement_id"] = to_upload["arrangements"].apply(
        lambda x: next(i["id"] for i in x if i["isDefault"])
    )

    progress = 0
    target = len(to_upload)
    for progress, data in enumerate(to_upload.iterrows()):
        _index, row = data
        api.file_upload(
            str(row["path"] / row["filename"]),
            domain_type="song_arrangement",
            domain_identifier=row["arrangement_id"],
            overwrite=True,
        )
        if progress % 50 == 0:
            logging.info("Finished upload %s of %s - sleep 15", progress, target)
            time.sleep(15)

    logging.info(
        "upload_local_songs_by_id - will overwrite all CT SNG default arrangement files with known ID"
    )


def apply_ct_song_sng_count_qs_tag(
    api: ChurchToolsApi, song: dict, tags_by_name: dict
) -> None:
    """Helper function which adds tags to songs in case sng attachment counts mismatches expectations.

    Requires respective tags to be present - can be ensured using prepare_required_song_tags()

    Args:
        api: instance connected to any churchtools instance
        song: churchtools song as dict
        tags_by_name: dictionary referencing tag ids by name
    """
    for arrangement in song["arrangements"]:
        sngs = [True for file in arrangement["files"] if ".sng" in file["name"]]
        number_of_sngs = len(sngs)

        if number_of_sngs == 1:
            api.remove_song_tag(
                song_id=song["id"], song_tag_id=tags_by_name["QS: missing sng"]
            )
            api.remove_song_tag(
                song_id=song["id"], song_tag_id=tags_by_name["QS: too many sng"]
            )

        elif number_of_sngs == 0:
            api.add_song_tag(
                song_id=song["id"], song_tag_id=tags_by_name["QS: missing sng"]
            )
        elif number_of_sngs > 1:
            api.add_song_tag(
                song_id=song["id"], song_tag_id=tags_by_name["QS: too many sng"]
            )


def prepare_required_song_tags(api: ChurchToolsApi) -> dict:
    """Helper which retrieves all song tags, checks that all required ones exist and returns dict of values.

    Returns:
        dict of name:id pairs for song tags
    """
    tags = api.get_tags(type="songs")
    tags_by_name = {tag["name"]: tag["id"] for tag in tags}

    # missing sng
    if "QS: missing sng" not in tags_by_name:
        pass
        # TODO@Benedict: implement create_tag
        # https://github.com/bensteUEM/ChurchToolsAPI/issues/92
        # name = "QS: missing sng"
        # tag_id = api.create_tag(name=name,type="songs")
        # tags_by_name[name]=tag_id
        # logging.info("created %s with ID=%s on instance because song tag did not exist", name, tag_id)

    # too many sng
    if "QS: too many sng" not in tags_by_name:
        pass
        # TODO@Benedict: implement create_tag
        # https://github.com/bensteUEM/ChurchToolsAPI/issues/92
        # name = "QS: too many sng"
        # tag_id = api.create_tag(name=name,type="songs")
        # tags_by_name[name]=tag_id
        # logging.info("created %s with ID=%s on instance because song tag did not exist", name, tag_id)

    return tags_by_name


def validate_ct_song_sng_count(api: ChurchToolsApi) -> None:
    """Check that all arrangements from ChurchTools songs have exactly 1 sng attachment.

    If there is no sng file attachment the song arrangement is incomplete and should be tagged with a "missing SNG" tag.
    If there is more than one sng attachment agenda downloads might retrieve the wrong one therefore only should be tagged with "too many SNG" tag.

    Arguments:
        api: instance connected to any churchtools instance
    """
    tags_by_name = prepare_required_song_tags(api=api)

    songs = api.get_songs()

    len_songs = len(songs)
    for song_count, song in enumerate(songs):
        apply_ct_song_sng_count_qs_tag(
            api=api,
            song=song,
            tags_by_name=tags_by_name,
        )
        if song_count % 25 == 0:
            # avoid Too many requests. Rate Limit Exceeded.
            logging.debug("sleep 1 second after %s / %s", song_count, len_songs)
            time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(
        filename="logs/main.py.log",
        encoding="utf-8",
        format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
    )
    logging.info("Excecuting Main RUN")

    songs_temp = []
    df_sng = read_songs_to_df()
    df_sng = clean_all_songs(df_sng=df_sng)
    write_df_to_file(df_sng)

    api = ChurchToolsApi(domain=ct_domain, ct_token=ct_token)
    validate_ct_song_sng_count(api)

    # Match all SongIDs from CT to local songs where missing
    df_ct = get_ct_songs_as_df(api)
    add_id_to_local_song_if_available_in_ct(df_sng, df_ct)

    # Upload all songs into CT that are new
    df_ct = get_ct_songs_as_df(api)
    upload_new_local_songs_and_generate_ct_id(df_sng, df_ct)

    # To be safe - re-read all data sources and upload
    df_sng = read_songs_to_df()
    df_ct = get_ct_songs_as_df(api)
    download_missing_online_songs(df_sng, df_ct, api)

    """
    df_sng = read_baiersbronn_songs_to_df()
    df_ct = get_ct_songs_as_df()
    upload_local_songs_by_id(df_sng, df_ct)
    """

    logging.info("Main Method finished")
