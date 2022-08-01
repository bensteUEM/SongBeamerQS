import logging
import os.path

import pandas as pd

import SNG_DEFAULTS
from SngFile import SngFile


def parse_sng_from_directory(directory, songbook_prefix="", filenames=[]):
    """
    Method which reads all SNG Files from a directory and adds missing default values if missing
    :param directory: directory to read from
    :param songbook_prefix: which should be used for Songbook number - usually related to directory
    :param filenames: optional list of filenames which should be covered - if none all from directory will be read
    :return: list of SngFile items read from the directory
    """
    logging.info('Parsing: ' + directory)
    logging.info('With Prefix: ' + songbook_prefix)

    result = []
    directory_list = filter(lambda x: x.endswith((".sng", ".SNG", ".Sng")), os.listdir(directory))

    if len(filenames) > 0:
        directory_list = filenames

    for sng_filename in directory_list:
        current_song = SngFile(directory + '/' + sng_filename, songbook_prefix)
        if "Editor" not in current_song.header.keys():
            current_song.header["Editor"] = SNG_DEFAULTS.SngDefaultHeader["Editor"]
            logging.info("Added missing Editor for:" + sng_filename)
        result.append(current_song)
    return result


def validate_all_headers(df_to_change, fix=False):
    """
    Method to start validation for all headers
    1. Validate Title
    2. Validate all Songbook Entries
    3. Remove all Illegal headers
    4. Psalm Backgrounds
    5. Check that all required headers are present

    :param df_to_change: Dataframe which should me used
    :param fix: boolean if data should be fixed - so far only applies for remove illegal headers and songbook fixing
    :return: boolean Series with True for all entries that have no issues
    """
    logging.info("Starting validate_all_headers({})".format(fix))

    # 1. Validate Title
    logging.info('Starting validate_header_title({})'.format(fix))
    headers_valid = df_to_change['SngFile'].apply(lambda x: x.validate_header_title(fix))

    # 2. Validate Songbook Entries
    logging.info("Starting validate_header_songbook({})".format(fix))
    headers_valid &= df_to_change["SngFile"].apply(lambda x: x.validate_header_songbook(fix))

    # 3. Remove all Illegal headers
    logging.info("Starting validate_headers_illegal_removed({})".format(fix))
    headers_valid &= df_to_change["SngFile"].apply(lambda x: x.validate_headers_illegal_removed(fix))

    # Set Background for all Psalm entries
    psalms_select = df_to_change["SngFile"].apply(lambda x: x.is_eg_psalm())
    logging.info("Starting validate_header_background({}) for {} psalms".format(fix, sum(psalms_select)))
    headers_valid &= df_to_change[psalms_select]["SngFile"] \
        .apply(lambda x: x.validate_header_background(fix))

    # 6. Check that all required headers are present
    logging.info("Starting validate_headers()")
    df_to_change["SngFile"].apply(lambda x: x.validate_headers())

    return headers_valid


def read_baiersbronn_songs_to_df():
    """
    Default method which reads all known directories used at Evangelische Kirchengemeinde Baiersbronn
    :return:
    """

    songs_temp = []
    """
    For Testing only!
    dirname = 'testData/'
    dirprefix = 'TEST'
    songs = parse_sng_from_directory(dirname, dirprefix)
    """

    for key, value in SNG_DEFAULTS.KnownFolderWithPrefix.items():
        dirname = SNG_DEFAULTS.KnownDirectory + key
        dirprefix = value
        songs_temp.extend(parse_sng_from_directory(dirname, dirprefix))

    result_df = pd.DataFrame(songs_temp, columns=["SngFile"])
    for index, value in result_df['SngFile'].items():
        result_df.loc[(index, 'filename')] = value.filename
        result_df.loc[(index, 'path')] = value.path
    return result_df


def read_baiersbronn_ct_songs():
    """
    Helper function reading all songs into a df
    :return:
    """
    from ChurchToolsApi import ChurchToolsApi

    api = ChurchToolsApi('https://elkw1610.krz.tools')
    songs = api.get_songs()
    df_ct = pd.json_normalize(songs)
    return df_ct


def generate_title_column(df_to_change):
    """
    method used to generate the 'Title' column for all items in a df based on the headers
    :param df_to_change: Dataframe which should be used
    :return:
    """

    for index, value in df_to_change['SngFile'].items():
        if 'Title' in value.header.keys():
            df_to_change.loc[(index, 'Title')] = value.header['Title']
        else:
            df_to_change.loc[(index, 'Title')] = None
            logging.info("Song without a Title in Header:" + value.filename)


def generate_songbook_column(df_to_change):
    """
    method used to generate the 'Songbook' and 'ChurchSongID' columns on all items in a df based on the headers
    :param df_to_change: Dataframe which should me used
    :return:
    """
    df_to_change["Songbook"] = df_to_change["SngFile"].apply(
        lambda x: x.header['Songbook'] if 'Songbook' in x.header else None)
    df_to_change["ChurchSongID"] = df_to_change["SngFile"].apply(
        lambda x: x.header['ChurchSongID'] if 'ChurchSongID' in x.header else None)


def generate_background_image_column(df_to_change):
    """
    method used to generate the 'BackgroundImage' column for all items in a df based on the headers
    :param df_to_change: Dataframe which should me used
    :return:
    """

    for index, value in df_to_change['SngFile'].items():
        if 'BackgroundImage' in value.header.keys():
            df_to_change.loc[(index, 'BackgroundImage')] = value.header['BackgroundImage']


def generate_ct_compare_columns(df_sng):
    """
    method used to generate the "id", 'name', 'category.name' for a local SNG Dataframe
    in order to match columns used in ChurchTools Dataframe
    :param df_sng: Dataframe generated from SNG Files which which should me used
    :type df_sng: pd.DataFrame
    :return: None because applied directly onto df
    """
    df_sng["id"] = df_sng["SngFile"].apply(
        lambda x: x.get_id())
    df_sng["name"] = df_sng["filename"].apply(
        lambda x: x[:-4])
    df_sng["category.name"] = df_sng["SngFile"].apply(
        lambda x: x.path.split("/")[-1])


def clean_all_songs(df: pd.DataFrame):
    """
    Helper function which runs cleaning methods for sng files on a dataframe
    :param df_sng: Dataframe to work on
    :type df_sng: pd.DataFrame
    :return:
    """
    logging.info('starting validate_verse_order_coverage() with fix')
    df['SngFile'].apply(lambda x: x.validate_verse_order_coverage(fix=True))

    logging.info('starting fix_intro_slide()')
    df['SngFile'].apply(lambda x: x.fix_intro_slide())

    # Fixing without auto moving to end because sometimes on purpose, and cases might be
    logging.info('starting validate_stop_verseorder(fix=True, should_be_at_end=False)')
    df['SngFile'].apply(lambda x: x.validate_stop_verseorder(fix=True, should_be_at_end=False))
    # Logging cases that are not at end ...
    # logging.info('starting validate_stop_verseorder(fix=False, should_be_at_end=True)')
    # df_sng['SngFile'].apply(lambda x: x.validate_stop_verseorder(fix=False, should_be_at_end=True))

    logging.info('starting validate_verse_numbers() with fix')
    df['SngFile'].apply(lambda x: x.validate_verse_numbers(fix=True))

    logging.info('starting validate_content_slides_number_of_lines() with fix')
    df['SngFile'].apply(lambda x: x.validate_content_slides_number_of_lines(fix=True))

    validate_all_headers(df, True)


def write_df_to_file():
    # Writing Output
    output_path = './output'
    logging.info('starting write_path_change({})'.format(output_path))
    df_sng['SngFile'].apply(lambda x: x.write_path_change(output_path))

    logging.info('starting write_file()')
    df_sng['SngFile'].apply(lambda x: x.write_file())


def check_ct_song_categories_exist_as_folder(ct_song_categories, path):
    """
    Method which check whether all Song Categories of ChurchTools exist in the specified folder
    :param ct_song_categories: List of all ChurchTools Song categories
    :param path: for local files
    :return:
    """
    logging.debug("checking categories{} in {}".format(ct_song_categories, path))
    local_directories = os.listdir(path)
    return all([category in local_directories for category in ct_song_categories])


def validate_ct_songs_exist_locally_by_name_and_category(df_ct, df_sng):
    """
    Function which checks that all song loaded from ChurchTools as DataFrame do exist locally
    Uses Name and Category to match them - does not compare IDs !

    And logs warning for all elements that can not be mapped

    Can be used to identify changes in ChurchTools that were not updated locally
    :param df_ct: DataFrame with all columns from a JSON response getting all songs from CT
    :type df_ct: pd.DataFrame
    :param df_sng: DataFrame with all local SNG files with headings matching CT Dataframe
    :type df_sng: pd.DataFrame
    :return: reference to merged Dataframe
    :rtype: pd.Dataframe
    """

    generate_ct_compare_columns(df_sng)

    logging.info("validate_ct_songs_exist_locally_by_name_and_category()")
    df_ct_join_name = df_sng.merge(df_ct, on=['name', 'category.name'], how='right', indicator=True)

    issues = df_ct_join_name[df_ct_join_name['_merge'] != 'both'].sort_values(by=['category.name', 'name'])
    for issue in issues[["name", 'category.name', 'id_y']].iterrows():
        logging.warning("Song ({}) in category ({}) exists as ChurchTools ID={} but not matched locally".format(
            issue[1]["name"], issue[1]["category.name"], issue[1]['id_y']))

    return df_ct_join_name


def validate_ct_songs_exist_locally_by_id(df_ct, df_sng):
    """
    Function which checks that all song loaded from ChurchTools as DataFrame do exist locally
    Uses only ID to match them - does not compare name or cateogry !

    And logs warning for all elements that can not be mapped

    Can be used to identify changes in ChurchTools that were not updated locally
    :param df_ct: DataFrame with all columns from a JSON response getting all songs from CT
    :type df_ct: pd.DataFrame
    :param df_sng: DataFrame with all local SNG files with headings matching CT Dataframe
    :type df_sng: pd.DataFrame
    :return: reference to merged Dataframe
    :rtype: pd.Dataframe
    """

    # prep df id, category and name columns
    generate_ct_compare_columns(df_sng)

    logging.info("validate_ct_songs_exist_locally_by_id()")
    df_ct_join_id = df_sng.merge(df_ct, on=['id'], how='right', indicator=True)

    issues = df_ct_join_id[df_ct_join_id['_merge'] != 'both'].sort_values(by=['category.name_y', 'name_y'])
    for issue in issues[["name_y", 'category.name_y', 'id']].iterrows():
        logging.warning(
            "Song ({}) in category ({}) exists with ChurchTools ID={} online but ID not matched locally".format(
                issue[1]["name_y"], issue[1]["category.name_y"], issue[1]['id']))

    return df_ct_join_id


if __name__ == '__main__':
    logging.basicConfig(filename='logs/main.py.log', encoding='utf-8',
                        format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
                        level=logging.DEBUG)
    logging.info("Excecuting Main RUN")

    df_sng = read_baiersbronn_songs_to_df()

    clean_all_songs(df_sng)

    # write_df_to_file()

    df_ct = read_baiersbronn_ct_songs()
    compare_by_name_and_category_df = validate_ct_songs_exist_locally_by_name_and_category(df_ct, df_sng)
    compare_by_id_df = validate_ct_songs_exist_locally_by_id(df_ct, df_sng)

    df_join_id = df_sng.merge(df_ct, on=['id'], how='left', indicator=True)

    logging.info('Main Method finished')

    # TODO Ideensammlung
    # Check for leere Folie mit Strophe 0 - bsp. EG 449
    # Psalm Auto Language Marking if space idented

    # Check Verses in numerical order
    # Replace Vers and Strophe by Verse and Chorus by Refrain

    # validate_header_songbook(df, True)
    # df.to_csv("Main_DF_Export.csv", quoting=csv.QUOTE_NONNUMERIC)
