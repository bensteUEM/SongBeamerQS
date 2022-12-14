from datetime import date

SngDefaultHeader = {
    'LangCount': '1',
    'Editor': 'Benedict\'s Python Script am ' + str(date.today()),
    'Version': '3'
}

SngRequiredHeader = [
    'Title',
    'Author',
    'Melody',
    '(c)',
    'CCLI',
    'Songbook',
    'ChurchSongID',
    'VerseOrder',
    'Version',
    'Editor'
]

SngOptionalHeader = [
    'ID',  # ChurchTools ID
    'OTitle',  # TODO Title parts slides - e.g. FJ5/073
    'TitleLang2',  # TODO Title parts slides - e.g. FJ5/073
    'Translation',
    'Bible',  # Checked with Psalms only
    'RECHTE'  # TODO check spelling
]

SngIllegalHeader = [
    'TitleFormat',
    'FontSize',
    'Format',
    'TitleFormat'
]

SngTitleNumberChars = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '.']
SngSongBookPrefix = ['EG', 'FJ', "WWDLP"]

# All Prefix which are known to be followed by a number
KnownSongBookPrefix = {'EG', 'FJ1', 'FJ2', 'FJ3', 'FJ4', 'FJ5', 'Wwdlp', 'test'}
KnownDirectory = '/home/benste/Documents/Kirchengemeinde Baiersbronn/Beamer/Songbeamer - Songs/'
KnownFolderWithPrefix = {
    'EG Lieder': 'EG',
    'EG Psalmen & Sonstiges': 'EG',
    'Feiert Jesus 1': 'FJ1',
    'Feiert Jesus 2': 'FJ2',
    'Feiert Jesus 3': 'FJ3',
    'Feiert Jesus 4': 'FJ4',
    'Feiert Jesus 5': 'FJ5',
    'Sonstige Lieder': '',
    'Sonstige Texte': '',
    'Hintergrundmusik': '',
    'Test': '',
    'Wwdlp (Wo wir dich loben, wachsen neue Lieder plus)': 'Wwdlp'
}

VerseMarker = ['Unbekannt', 'Unbenannt', 'Unknown', 'Intro', 'Vers', 'Verse', 'Strophe', 'Pre - Bridge', 'Bridge',
               'Misc', 'Pre-Refrain', 'Refrain', 'Pre-Chorus', 'Chorus', 'Pre-Coda',
               'Zwischenspiel', 'Instrumental', 'Interlude', 'Coda', 'Ending', 'Outro', 'Teil', 'Part', 'Chor', 'Solo'
               ]
