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
    1. Validate Title and Songbook Entries
    2. Remove all Illegal headers
    3. Check that all required headers are present

    :param df_to_change: Dataframe which should me used
    :param fix: boolean if data should be fixed - so far only applies for remove illegal headers and songbook fixing
    :return: boolean Series with True for all entries that have no issues
    """

    # 1. Validate Title and Songbook Entries
    headers_valid = validate_all_songbook(df_to_change, fix)
    headers_valid &= df_to_change["SngFile"].apply(lambda x: x.validate_header_title(fix))

    # 2. Remove all Illegal headers
    if fix:
        logging.info("Starting removal of illegal headers")
        df_to_change["SngFile"].apply(lambda x: x.fix_remove_illegal_headers())

    # 3. Check that all required headers are present
    logging.info("Starting to check for required headers")
    df_to_change["SngFile"].apply(lambda x: x.validate_headers())

    return headers_valid


def validate_all_songbook(df_to_change, fix=False):
    """
    Method which starts validation of songbook for whole dataframe
    optionally attempts to fix them while logging the cases

    :param df_to_change: Dataframe which should me used
    :param fix: boolean if data should be fixed
    :return: boolean Series with True for all entries that have no issues
    """
    logging.info("Starting Songbook Validation with fix={}".format(fix))

    songbook_valid = df_to_change["SngFile"].apply(lambda x: x.validate_header_songbook(fix=False))

    number_of_invalid_songbook = len(df_to_change[~songbook_valid])
    if number_of_invalid_songbook > 0:
        logging.info('{} of {} entries with invalid Songbook or ChurchSongID'
                     .format(number_of_invalid_songbook, len(df_to_change))
                     )

    if fix:
        logging.info('Starting Songbook Fixing')
        songbook_valid_fix = df_to_change["SngFile"][~songbook_valid].apply(
            lambda x: x.validate_header_songbook(fix=True))
        songbook_valid |= songbook_valid_fix

    return songbook_valid


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
    method used to generate the 'Songbook' and 'ChurchSongID' columns for all items in a df based on the headers
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


if __name__ == '__main__':
    logging.basicConfig(filename='logs/main.py.log', encoding='utf-8',
                        format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
                        level=logging.DEBUG)
    logging.info("Excecuting Main RUN")

    df_sng = read_baiersbronn_songs_to_df()

    # generate_background_image_column(df_sng)
    # validate_all_headers(df_sng, fix=True)
    # generate_title_column(df_sng)
    # generate_songbook_column(df_sng)

    """
    from ChurchToolsApi import ChurchToolsApi

    api = ChurchToolsApi('https://elkw1610.krz.tools')
    songs = api.get_songs()
    df_ct = pd.json_normalize(songs)
    """

    logging.info('starting validate_header_title()')
    df_sng['SngFile'].apply(lambda x: x.validate_header_title(fix=True))
    logging.info('starting validate_header_songbook()')
    df_sng['SngFile'].apply(lambda x: x.validate_header_songbook(fix=True))

    logging.info('starting validate_verse_order() with fix')
    df_sng['SngFile'].apply(lambda x: x.validate_verse_order(fix=True))
    #TODO
    # Check why reported in log even though fix is enabled
    # 2022-06-03 10:56:20,506 root       DEBUG    Missing VerseOrder in 644 Jesus hat die Kinder lieb.sng

    logging.info('starting fix_intro_slide()')
    df_sng['SngFile'].apply(lambda x: x.fix_intro_slide())
    logging.info('starting validate_stop_verseorder(fix=True, should_be_at_end=True)')
    df_sng['SngFile'].apply(lambda x: x.validate_stop_verseorder(fix=True, should_be_at_end=True))

    logging.info('starting validate_content_slides_number_of_lines() with fix')
    df_sng['SngFile'].apply(lambda x: x.validate_content_slides_number_of_lines(fix=True))

    # current_path = df_sng["SngFile"].iloc[0].path
    # output_path = '/'.join(current_path.split('/')[:-1])+'/test'

    output_path = './output'
    logging.info('starting write_path_change({})'.format(output_path))
    df_sng['SngFile'].apply(lambda x: x.write_path_change(output_path))

    logging.info('starting write_file()')
    df_sng['SngFile'].apply(lambda x: x.write_file())

    logging.info('Main Method finished')

    # TODO Ideensammlung
    # Check for leere Folie mit Strophe 0 - bsp. EG 449
    # Psalm Auto Language Marking if space idented
    # EG Bild hinter alle Psalmen ...#BackgroundImage=Evangelisches Gesangbuch.jpg
    # Check for verse or strophe with number followed by letter and correct it?

    # validate_header_songbook(df, True)
    # df.to_csv("Main_DF_Export.csv", quoting=csv.QUOTE_NONNUMERIC)
