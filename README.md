# Initial Remarks

This code is version-controlled as is. It is kinda dirty.
It was specifically built for use at Evangelische Kirchengemeinde Baiersbronn and requires a specific structure of the files.
The idea was to clean an existing collection of SNG files and prepare it for upload to ChurchTools

It will for sure require adjustments if you intend to use it.
Future versions might clean up some of the "grown" code which was originally meant to help with a specific cleanup and organisation task.

There is no documentation except from the docstrings and this readme!

WARNING - if you are not a developer please do not intend to use the code.
Even if you get it running it might damage your collection!

# Setup
Some attention is required before use (even for thos who know how to code)

## ChurchTools Authentification
ENV Variables need to be set
* CT_DOMAIN = https://https://YOURINSTANCE.tools
* CT_TOKEN = XXX (token obtained from user configuration)

## Required directories not included in Git Repo need to be created before use
In order to execute the tests or script parts a couple of folders and files are required which are not included in the git repo
as part of issue #1 Public Domain files might be included in future

* ./logs
* ./output
  * SUBFOLDER by Songbook
* ./testData
  * Psalm
    * SNG Files for EG Psalms
  * Various Copyrighted SNG files

## Structure of SNG Library
The scripts assume that there is one Subfolder per Songbook and a repsective prefix is defined in SNG_DEFAULTS.py
Each Song filename should start with a 3 digit number followed by space.

## Execution
* TestCases for most Classes require specific data!
* main.py is used to execute specific actions

## Dependency
The code is highly linked to another Repo required for uploading to ChurchTools
https://github.com/bensteUEM/ChurchToolsAPI

Make sure to either understand this module or remove it's usages within the code.

# License
This code is provided with a CC-BY-SA license See https://creativecommons.org/licenses/by-sa/2.0/ for details.
In short this means - feel free to do anything with it BUT you are required to publish any changes or additional functionality (even if you intended to add functionality for yourself only!)
Anybody using this code is more than welcome to contribute with change requests to the original repository.
