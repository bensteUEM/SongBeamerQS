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

    # 4. fix caps of CCLI entry if required
    df_to_change["SngFile"].apply(lambda x: x.fix_header_ccli_caps())

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


def get_ct_songs_as_df(api):
    """
    Helper function reading all songs into a df
    :param api: reference to a churchtools system
    :type api: ChurchToolsApi
    :return: Dataframe with all Songs from ChurchTools Instance
    :rtype:  pandas.DataFrame
    """

    songs = api.get_songs()
    result = pd.json_normalize(songs)
    return result


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


def write_df_to_file(target_dir=None):
    """
    write files to either it's original main directory or use a separate dir
    :param target_dir: e.g. './output' to write output into a separate folder
    :return:
    """
    if target_dir is not None:
        logging.info('starting write_path_change({})'.format(target_dir))
        df_sng['SngFile'].apply(lambda x: x.write_path_change(target_dir))

    logging.info('starting write_file()')
    df_sng['SngFile'].apply(lambda x: x.write_file())


def check_ct_song_categories_exist_as_folder(ct_song_categories, path):
    """
    Method which check whether all Song Categories of ChurchTools exist in the specified folder
    :param ct_song_categories: List of all ChurchTools Song categories
    :param path: for local files
    :return: if all CT categories exist as folder in local path
    """
    logging.debug("checking categories{} in {}".format(ct_song_categories, path))
    local_directories = os.listdir(path)

    for category in ct_song_categories:
        if category not in local_directories:
            logging.warning('Missing CT category {} in {}'.format(category, path))
            return False

    return True


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


def add_id_to_local_song_if_available_in_ct(df_sng, df_ct):
    """
    Helper function which write the ID of into each SNG file that
    * does not have a valid ChurchTools Song ID
    * AND does have a match using name and category comparison with ChurchTools Dataframe
    :param df_sng: All local songs to check - a copy i used for processing ...
    :param df_ct:  All known songs from ChurchTools
    :return:
    """
    logging.info("Starting add_id_to_local_song_if_available_in_ct()")
    logging.critical(
        "This function might destroy your data in case a songname exists twice in one songbook #13")  # 13 TODO

    compare_by_id_df = validate_ct_songs_exist_locally_by_id(df_ct, df_sng)

    # Part used to overwrite local IDs with CT name_cat in case it exists in CT
    ct_missing_by_id_df = compare_by_id_df[compare_by_id_df['_merge'] == 'right_only'].copy()
    ct_missing_by_id_df.drop(['name_x', 'category.name_x', '_merge'], axis=1, inplace=True)
    ct_missing_by_id_df.rename(columns={'name_y': 'name', 'category.name_y': 'category.name'}, inplace=True)
    overwrite_id_by_name_cat = validate_ct_songs_exist_locally_by_name_and_category(ct_missing_by_id_df, df_sng)

    for index, row in overwrite_id_by_name_cat.iterrows():
        if isinstance(row['SngFile_x'], SngFile):
            row['SngFile_x'].set_id(row['id_y'])
            logging.debug('Prepare overwrite id  {} for song {} with new id {}'.format(
                row['id_y'], row['filename_x'], row['id_y']))
        else:
            logging.warning('CT song ID= {} from ({}) with title "{}" not found locally'.format(
                row['id_y'], row['category.name'], row['name']))

    missing_files = overwrite_id_by_name_cat['SngFile_x'].apply(lambda x: not isinstance(x, SngFile))
    overwrite_id_by_name_cat[~missing_files]['SngFile_x'].apply(lambda x: x.write_file())


def download_missing_online_songs(df_sng, df_ct, ct_api_reference):
    """
    Function which will check which songs are missing (by ID) and tries to download them to the respective folders
    It is highly recommended to execute add_id_to_local_song_if_available_in_ct() and
    upload_new_local_songs_and_generate_ct_id() before in order to try to match all songs local and avoid duplicates
    :param df_sng: DataFrame with all local files
    :param df_ct: DataFrame with all online files
    :param ct_api_reference: direct access to ChurchTools API instance
    :return: Success message
    :rtype: bool
    """

    compare = validate_ct_songs_exist_locally_by_id(df_ct, df_sng)
    song_path = compare[compare['path'].notnull()].iloc[0]['path']
    collection_path = "/".join(song_path.split('/')[:-1])

    ids = compare[compare['SngFile'].apply(lambda x: not isinstance(x, SngFile))]['id']

    is_successful = True
    for id in ids:
        song = ct_api_reference.get_songs(song_id=id)
        logging.debug('Downloading CT song id={} "{}" ({})'.format(id, song['name'], song['category']))

        default_arrangement_id = [item['id'] for item in song['arrangements'] if item['isDefault'] is True][0]
        category_name = song['category']['name']
        file_path_in_collection = os.sep.join([collection_path, category_name])
        filename = '{}.sng'.format(song['name'])

        if os.path.exists(os.sep.join([file_path_in_collection, filename])):
            logging.warning(
                'Local file {} from CT ID {} does already exist - try automatch instead!'.format(filename, id))
            is_successful &= False
            continue

        result = ct_api_reference.file_download(filename=filename,
                                                domain_type='song_arrangement',
                                                domain_identifier=default_arrangement_id,
                                                path_for_download=file_path_in_collection)
        if result:
            logging.debug('Downloaded {} into {} from CT IT {}'.format(filename, file_path_in_collection, id))
        else:
            logging.debug('Failed to download {} into {} from CT IT {}'.format(filename, file_path_in_collection, id))
        is_successful &= result

    return is_successful


def upload_new_local_songs_and_generate_ct_id(df_sng, df_ct, default_tag_id=52):
    """
    Helper Function which creates new ChurchTools Songs for all SNG Files from dataframe which don't have a song ID
    Iterates through all songs in df_sng that don't match
    New version of the SNG file including the newly created id is overwritten locally
    :param df_sng: Pandas DataFrame with SNG objects that should be checked against
    :type df_sng: pd.DataFrame
    :param df_ct: Pandas DataFrame with Information retrieved about all ChurchTools Songs
    :type df_ct: pd.DataFrame
    :param default_tag_id: default ID used to tag new songs - depends on instance of churchtools used !
    :return:
    """

    generate_ct_compare_columns(df_sng)

    to_upload = df_sng.merge(df_ct, on=['id'], how='left', indicator=True)
    to_upload = to_upload[to_upload['_merge'] == 'left_only']

    api = ChurchToolsApi('https://elkw1610.krz.tools')
    song_category_dict = api.get_song_category_map()

    for index, row in to_upload.iterrows():
        title = row['filename'][:-4]
        category_id = song_category_dict[row['category.name_x']]

        author1 = row['SngFile'].header['Author'].split(', ') if 'Author' in row['SngFile'].header.keys() else []
        author2 = row['SngFile'].header['Melody'].split(', ') if 'Melody' in row['SngFile'].header.keys() else []

        authors = []
        for author in author1:
            if author not in authors:
                authors.append(author)
        for author in author2:
            if author not in authors:
                authors.append(author)

        authors = ', '.join([author for author in authors if author is not None])

        ccli = row['SngFile'].header['CCLI'] if 'CCLI' in row['SngFile'].header.keys() else ''
        copy = row['SngFile'].header['(c)'] if '(c)' in row['SngFile'].header.keys() else ''

        logging.info("Uploading Song '{}' with Category ID '{}' from '{}' with (C) from '{}' and CCLI '{}'"
                     .format(title, category_id, authors, copy, ccli))
        song_id = api.create_song(title=title, songcategory_id=category_id, author=authors,
                                  copyright=copy, ccli=ccli)
        logging.debug("Created new Song with ID '{}'".format(song_id))
        api.add_song_tag(song_id=song_id, song_tag_id=default_tag_id)
        row['SngFile'].set_id(song_id)
        row['SngFile'].write_file()

        song = api.get_songs(song_id=song_id)

        api.file_upload("/".join([row['path'], row['filename']]), domain_type='song_arrangement',
                        domain_identifier=[i['id'] for i in song['arrangements'] if i['isDefault'] is True][0],
                        overwrite=False)


def upload_local_songs_by_id(df_sng, df_ct):
    """
    Helper function that overwrites the SNG file of the default arrangement in ChurchTools with same song id
    :return:
    """
    logging.critical("upload_local_songs_by_id is not fully implemnted yet - check issue #14")  # TODO #14

    generate_ct_compare_columns(df_sng)
    to_upload = df_sng.merge(df_ct, on=['id'], how='left', indicator=True)
    api = ChurchToolsApi('https://elkw1610.krz.tools')

    to_upload['arrangement_id'] = to_upload['arrangements'].apply(
        lambda x: [i['id'] for i in x if i['isDefault'] is True][0])

    to_upload = to_upload[to_upload['filename'] == '019 Die Gnade.sng']  # TODO debugging - one song only #14

    for index, row in to_upload.iterrows():
        api.file_upload("/".join([row['path'], row['filename']]), domain_type='song_arrangement',
                        domain_identifier=row['arrangement_id'],
                        overwrite=True)

    logging.info("upload_local_songs_by_id - will overwrite all CT SNG default arrangement files with known ID")


if __name__ == '__main__':
    logging.basicConfig(filename='logs/main.py.log', encoding='utf-8',
                        format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
                        level=logging.DEBUG)
    logging.info("Excecuting Main RUN")

    songs_temp = []
    """
    #For Testing only!

    for key, value in SNG_DEFAULTS.KnownFolderWithPrefix.items():
        dirname = '/home/benste/Documents/Kirchengemeinde Baiersbronn/Beamer/Songbeamer - Songs/' + key
        dirprefix = value
        songs_temp.extend(parse_sng_from_directory(dirname, dirprefix))

    """
    # TODO CHECK why new songs from CT download are UTF8 problematic #4
    df_sng = read_baiersbronn_songs_to_df()
    clean_all_songs(df_sng)
    write_df_to_file()

    from ChurchToolsApi import ChurchToolsApi

    api = ChurchToolsApi('https://elkw1610.krz.tools')

    # Match all SongIDs from CT to local songs where missing
    df_ct = get_ct_songs_as_df(api)
    add_id_to_local_song_if_available_in_ct(df_sng, df_ct)

    # Upload all songs into CT that are new
    df_ct = get_ct_songs_as_df(api)
    upload_new_local_songs_and_generate_ct_id(df_sng, df_ct)

    # To be safe - re-read all data sources and upload
    df_sng = read_baiersbronn_songs_to_df()
    df_ct = get_ct_songs_as_df(api)
    download_missing_online_songs(df_sng, df_ct, api)

    """
    df_sng = read_baiersbronn_songs_to_df()
    df_ct = get_ct_songs_as_df()
    upload_local_songs_by_id(df_sng, df_ct)
    """

    logging.info('Main Method finished')

    # TODO Ideensammlung
    # Check for leere Folie mit Strophe 0 - bsp. EG 449
    # Psalm Auto Language Marking if space idented

    # Check Verses in numerical order
    # Replace Vers and Strophe by Verse and Chorus by Refrain

    # validate_header_songbook(df, True)
    # df.to_csv("Main_DF_Export.csv", quoting=csv.QUOTE_NONNUMERIC)
