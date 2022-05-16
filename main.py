import logging
import os.path

import pandas as pd

import SNG_DEFAULTS
from SngFile import SngFile


def parse_sng_from_directory(directory, songbook_prefix=""):
    """
    Method which reads all SNG Files from a directory and adds missing default values if missing
    :param directory: directory to read from
    :param songbook_prefix: which should be used for Songbook number - usually related to directory
    :return: list of SngFile items read from the directory
    """
    logging.info('Parsing: ' + directory)
    logging.info('With Prefix: ' + songbook_prefix)

    result = []
    directory_list = filter(lambda x: x.endswith((".sng", ".SNG", ".Sng")), os.listdir(directory))
    for sng_filename in directory_list:
        current_song = SngFile(directory + '/' + sng_filename, songbook_prefix)
        if "Editor" not in current_song.header.keys():
            current_song.header["Editor"] = SNG_DEFAULTS.SngDefaultHeader["Editor"]
            logging.info("Added missing Editor for:" + sng_filename)
        result.append(current_song)
    return result


def validate_titles(df_to_change, fix=False):
    """
    Method which checks Title entries for invalid content e.g. numbers
    and runs fix_title for all broken items
    :param df_to_change: Dataframe which should be used
    :param fix: boolean if data should be fixed
    :return: boolean Series with True for all entries that have issues
    """

    # Generate Dataframe Column with Title
    for current_index, current_value in df["SngFile"].items():
        if "Title" in current_value.header.keys():
            df.loc[(current_index, "Title")] = current_value.header["Title"]
            df.loc[(current_index, "contains_number_in_title")] = any(
                char.isdigit() for char in current_value.header["Title"])
        else:
            logging.info("Song without a Title in Header:" + current_value.filename)
            df.loc[(current_index, "contains_number_in_title")] = False

    title_invalid = df_to_change["Title"].isna() | df_to_change["contains_number_in_title"]

    if fix:
        for current_index, current_value in df_to_change[title_invalid]["SngFile"].items():
            logging.info(
                "Invalid title (" + str(df_to_change.loc[(current_index, "Title")]) + ") in " + current_value.filename)
            current_value.fix_title()
            df_to_change.loc[(current_index, "Title")] = current_value.header["Title"]

    return title_invalid


def validate_headers(df_to_change, fix=False):
    """
    Method to start validation for all headers
    1. Validate Songbook Entries
    2. Remove all Illegal headers
    3. Check that all required headers are present

    :param df_to_change: Dataframe which should me used
    :param fix: boolean if data should be fixed - so far only applies for remove illegal headers and songbook fixing
    :return: boolean Series with True for all entries that have issues
    """

    headers_invalid = validate_songbook(df_to_change, fix)
    headers_invalid = headers_invalid | validate_titles(df_to_change, fix)

    if fix:
        logging.info("Starting removal of illegal headers")
        df_to_change["SngFile"].apply(lambda x: x.fix_remove_illegal_headers())

    logging.info("Starting to check for required headers")
    df_to_change["SngFile"].apply(lambda x: x.contains_required_headers())

    return headers_invalid


def validate_songbook(df_to_change, fix=False):
    """
    Method to add validation columns for all songs regarding SongBook and ChurchSongID
    :param df_to_change: Dataframe which should me used
    :param fix: boolean if data should be fixed
    :return: boolean Series with True for all entries that have issues
    """
    logging.info("Starting Songbook Validation with fix={}".format(fix))

    # Generate Required Columns
    for current_index, current_value in df_to_change["SngFile"].items():
        df_to_change.loc[(current_index, "songbook_prefix")] = current_value.songbook_prefix
        if "Songbook" in current_value.header.keys():
            df_to_change.loc[(current_index, "Songbook")] = current_value.header["Songbook"]
        else:
            logging.debug("Song without Songbook in Header:\t" + current_value.filename)

        if "ChurchSongID" in current_value.header.keys():
            df_to_change.loc[(current_index, "ChurchSongID")] = current_value.header["ChurchSongID"]
        else:
            logging.debug("Song without ChurchSongID in Header:" + current_value.filename)

    # Validate Content of the columns
    songbook_invalid = df_to_change['ChurchSongID'] != df_to_change['Songbook']
    songbook_invalid |= df_to_change['ChurchSongID'].isna()
    songbook_invalid |= df_to_change['Songbook'].isna()
    # ChurchSongID ' '  or '' is automatically removed from SongBeamer on Editing hence = to isna() after updates

    # Check for all remaining that songbook prefix is part of songbook
    songbook_invalid |= \
        df_to_change[~songbook_invalid].apply(lambda x: x['songbook_prefix'] not in x['Songbook'], axis=1)

    # Check Syntax with Regex, either FJx/yyy, EG YYY, EG YYY.YY or or EG XXX - Psalm X or Wwdlp YYY
    # ^(Wwdlp \d{3})|(FJ([1-5])\/\d{3})|(EG \d{3}(( - Psalm )\d{1,3})?)$
    songbook_regex = r"^(Wwdlp \d{3})|(FJ([1-5])\/\d{3})|(EG \d{3}(.\d{1,2})?(( - Psalm )\d{1,3})?( .{1,3})?)$"
    songbook_invalid |= ~df_to_change["Songbook"].str.fullmatch(songbook_regex, na=False)

    # Check for remaining that "&" should not be present in Songbook
    # songbook_invalid |= df_to_change["Songbook"].str.contains('&')
    # sample is EG 548 & WWDLP 170 = loc 77
    # -> no longer needed because of regex check

    # TODO low Prio - check numeric range of songbooks
    # EG 1 - 851 incl.non numeric e.g. 178.14
    # EG Psalms in EG Württemberg EG 701-758
    # Syntax should be EG xxx - Psalm Y

    number_of_invalid_songbook = len(df_to_change[songbook_invalid])
    if number_of_invalid_songbook > 0:
        logging.info('{} of {} entries with invalid Songbook or ChurchSongID'
                     .format(number_of_invalid_songbook, len(df_to_change))
                     )

    if fix:
        logging.info('Starting Songbook Fixing')
        for current_index, current_value in df_to_change[songbook_invalid]["SngFile"].items():
            if current_value.fix_header_church_song_id_caps():  # Simple Fixing attempt with caps change
                df_to_change.loc[(current_index, "ChurchSongID")] = current_value.header["ChurchSongID"]
                continue
            if 'Songbook' in current_value.header.keys():  # Prepare Logging text
                text = 'Corrected Songbook from (' + current_value.header["Songbook"] + ')'
            else:
                text = 'New Songbook'
            fixed = current_value.fix_songbook()

            if not fixed and 'Songbook' not in current_value.header.keys():
                logging.error("Problem occured with Songbook Fixing of {} - check logs!".format(current_value.filename))
                df_to_change.loc[(current_index, "Songbook")] = None
                df_to_change.loc[(current_index, "ChurchSongID")] = None
            elif not fixed:
                logging.error(
                    "Problem occured with Songbook Fixing of {} - kept original {}".format(
                        current_value.filename, current_value.header["Songbook"]))
            else:
                df_to_change.loc[(current_index, "Songbook")] = current_value.header["Songbook"]
                df_to_change.loc[(current_index, "ChurchSongID")] = current_value.header["ChurchSongID"]
                logging.debug(text + ' to (' + current_value.header['Songbook'] + ') in ' + current_value.filename)

    return songbook_invalid


def read_baiersbronn_songs_to_df():
    """
    Default method which reads all known directories used at Evangelische Kirchengemeinde Baiersbronn
    :return:
    """

    songs = []
    """
    For Testing only!
    dirname = 'testData/'
    dirprefix = 'TEST'
    songs = parse_sng_from_directory(dirname, dirprefix)
    """

    for key, value in SNG_DEFAULTS.KnownFolderWithPrefix.items():
        dirname = SNG_DEFAULTS.KnownDirectory + key
        dirprefix = value
        songs.extend(parse_sng_from_directory(dirname, dirprefix))

    result_df = pd.DataFrame(songs, columns=["SngFile"])
    for index, value in result_df['SngFile'].items():
        result_df.loc[(index, 'filename')] = value.filename
        result_df.loc[(index, 'path')] = value.path
    return result_df


def generate_title_column(df_to_change):
    """
    method used to generate the 'Title' column for all items in a df based on the headers
    :param df_to_change: Dataframe which should me used
    :return:
    """

    for index, value in df_to_change['SngFile'].items():
        if 'Title' in value.header.keys():
            df_to_change.loc[(index, 'Title')] = value.header['Title']


def generate_background_image_column(df_to_change):
    """
    method used to generate the 'BackgroundImage' column for all items in a df based on the headers
    :param df_to_change: Dataframe which should me used
    :return:
    """

    for index, value in df_to_change['SngFile'].items():
        if 'BackgroundImage' in value.header.keys():
            df_to_change.loc[(index, 'BackgroundImage')] = value.header['BackgroundImage']


if __name__ == '__main__':
    logging.basicConfig(filename='logs/main.log', encoding='utf-8',
                        format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
                        level=logging.DEBUG)
    logging.info("Excecuting Main RUN")

    df = read_baiersbronn_songs_to_df()
    generate_title_column(df)
    generate_background_image_column(df)

    # TODO Ideensammlung
    # - check max number of chars per line
    # - make blocks of 4 lines only

    # validate_titles(df, True)
    # validate_songbook(df, True)

    # df.to_csv("Main_DF_Export.csv", quoting=csv.QUOTE_NONNUMERIC)
    validate_headers(df, fix=True)

    logging.info('Main Method finished')
