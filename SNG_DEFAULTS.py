from datetime import date

SngDefaultHeader = {
    'LangCount': '1',
    'Editor': 'Benedict\'s Python Script am ' + str(date.today()),
    'Version': '3'
}

SngRequiredHeader = [
    'Title',
    'Author',
    '(c)',
    'CCLI',
    'Songbook',
    'ChurchSongID',
    'VerseOrder',
    'Version',
    'Editor'
]

SngOptionalHeader = [
    'MUSIK',  # TODO left out in many cases when identical to Author ...
    'Translation',
    'BIBLE',  # TODO check spelling
    'RECHTE',  # TODO check spelling
]

SngIllegalHeader = [
    'TitleFormat',
    'FontSize',
    'Format',
    'TitleFormat'
]

SngTitleNumberChars = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '.']
SngSongBookPrefix = ['EG', 'FJ', "WWDLP"]
