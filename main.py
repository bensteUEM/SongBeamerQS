import csv
import logging
import os.path
import pandas as pd
import SNG_DEFAULTS
from SNG_File import SNG_File


def parse_sng_from_directory(directory, songbook_prefix=""):
    """
    Method which reads all SNG Files from a directory and adds missing default values if missing
    :param directory: directory to read from
    :param songbook_prefix: which should be used for Songbook number - usually related to directory
    :return: list of SNG_File items read from the directory
    """
    logging.info('Parsing: ' + directory)
    logging.info('With Prefix: ' + songbook_prefix)

    result = []
    directory_list = filter(lambda x: x.endswith((".sng", ".SNG", ".Sng")), os.listdir(directory))
    for sng in directory_list:
        current_song = SNG_File(directory + '/' + sng, songbook_prefix)
        if "Editor" not in current_song.header.keys():
            current_song.header["Editor"] = SNG_DEFAULTS.SngDefaultHeader["Editor"]
            logging.info("Added missing Editor for:" + sng.filename)
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
    for current_index, current_value in df["SNG_File"].items():
        if "Title" in current_value.header.keys():
            df.loc[(current_index, "Title")] = current_value.header["Title"]
            df.loc[(current_index, "contains_number_in_title")] = any(
                char.isdigit() for char in current_value.header["Title"])
        else:
            logging.info("Song without a Title in Header:" + current_value.filename)

    title_invalid = df_to_change["Title"].isna() | df_to_change["contains_number_in_title"] == True

    if fix:
        for current_index, current_value in df_to_change[title_invalid]["SNG_File"].items():
            logging.info(
                "Invalid title (" + str(df_to_change.loc[(current_index, "Title")]) + ") in " + current_value.filename)
            current_value.fix_title()
            df_to_change.loc[(current_index, "Title")] = current_value.header["Title"]

    return title_invalid


def validate_songbook(df_to_change, fix=False):
    """
    Method to add validation columns for all songs regarding SongBook and ChurchSongID
    :param df_to_change: Dataframe which should me used
    :param fix: boolean if data should be fixed
    :return: boolean Series with True for all entries that have issues
    """

    # Generate Required Columns
    for current_index, current_value in df_to_change["SNG_File"].items():
        df_to_change.loc[(current_index, "songbook_prefix")] = current_value.songbook_prefix
        if "Songbook" in current_value.header.keys():
            df_to_change.loc[(current_index, "Songbook")] = current_value.header["Songbook"]
        else:
            logging.info("Song without Songbook in Header:\t" + current_value.filename)

        if "ChurchSongID" in current_value.header.keys():
            df_to_change.loc[(current_index, "ChurchSongID")] = current_value.header["ChurchSongID"]
        else:
            logging.info("Song without ChurchSongID in Header:" + current_value.filename)

    # Validate Content of the columns

    songbook_invalid = df_to_change['ChurchSongID'] != df_to_change['Songbook']
    songbook_invalid |= df_to_change['ChurchSongID'].isna()
    songbook_invalid |= df_to_change['Songbook'].isna()
    # ChurchSongID ' '  or '' is automatically removed from SongBeamer on Editing hence = to isna() after updates

    # TODO check that Songbook Prefix is part of Songbook otherwise mark as invalid

    # combined?? with &
    # Psalm => is EG specific number range 7xx should contain additional - Psalm XXX  not auto validated
    # TODO log warning if prefix EG and number in specific range?

    # if df['ChurchSongID'] == df['ChurchSongID']:
    # TODO split by ' ' erster Absatz für Songbook darf nur DIGIT oder . enthalten bsp. 190.2

    number_of_invalid_songbook = len(df_to_change[songbook_invalid])
    if number_of_invalid_songbook > 0:
        logging.info(str(number_of_invalid_songbook) + " entries with invalid Songbook or ChurchSongID")

    if fix:
        for current_index, current_value in df_to_change[songbook_invalid]["SNG_File"].items():
            if 'Songbook' in current_value.header.keys():
                text = 'Corrected Songbook from (' + current_value.header["Songbook"] + ')'
            else:
                text = 'New Songbook'
            current_value.fix_songbook()
            df_to_change.loc[(current_index, "Songbook")] = current_value.header["Songbook"]
            df_to_change.loc[(current_index, "ChurchSongID")] = current_value.header["ChurchSongID"]

            # if 'Songbook' not in value.header.keys(): #TODO DEBUG wenn ungültige Zeichen in Nummer
            #    raise NotImplementedError("Strange case ...") #TODO remove
            # else:
            logging.info(text + ' to (' + current_value.header['Songbook'] + ') in ' + current_value.filename)

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

    df = pd.DataFrame(songs, columns=["SNG_File"])
    for index, value in df['SNG_File'].items():
        df.loc[(index, 'filename')] = value.filename
        df.loc[(index, 'path')] = value.path
    return df


def generate_title_column(df_to_change):
    """
    method used to generate the 'Title' column for all items in a df based on the headers
    :param df_to_change: Dataframe which should me used
    :return:
    """

    for index, value in df_to_change['SNG_File'].items():
        if 'Title' in value.header.keys():
            df_to_change.loc[(index, 'Title')] = value.header['Title']


def generate_background_image_column(df_to_change):
    """
    method used to generate the 'BackgroundImage' column for all items in a df based on the headers
    :param df_to_change: Dataframe which should me used
    :return:
    """

    for index, value in df_to_change['SNG_File'].items():
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
    # TODO check max number of chars per line
    # TODo make blocks of 4 lines only

    # validate_titles(df, True)
    # validate_songbook(df, True)
    df.to_csv("Main_DF_Export.csv", quoting=csv.QUOTE_NONNUMERIC)
    logging.info('Main Method finished')
