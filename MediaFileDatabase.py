# This Python file uses the following encoding: utf-8
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage
from PySide6.QtCore import QDir, QDirIterator

import re

class MediaFileDatabase():
    def __init__(self):
        self.db = TinyDB(storage=MemoryStorage)
        self.mediaTable = self.db.table('media')
        self.soundsTable = self.db.table('sounds')
        self._mediaSupported = {"*.jpg", "*.jpeg","*.gif", "*.bmp", "*.png"}
        self._soundsSupported = {"*.alac", "*.aac","*.mp3", "*.ac3", "*.wav", "*.flac"}

    def mediaSupported(self):
        return self._mediaSupported

    def soundsSupported(self):
        return self._soundsSupported

    def indexMedia(self, mediaPath):
        mediaCount = 0
        mediaDirIter = QDirIterator(mediaPath, self._mediaSupported, QDir.Files, QDirIterator.Subdirectories)

        self.mediaTable.truncate()
        while mediaDirIter.hasNext():
            mediaFile = mediaDirIter.nextFileInfo()
            mediaCount += 1
            # Add parts of the file name as tags
            baseFileName = mediaFile.completeBaseName()
            tagList = re.split('[_+-.\s+]{1}', baseFileName.lower())
            tagList.append(mediaFile.suffix().lower()) # Add the extension as a tag
            self.mediaTable.insert({ 'mediaName': mediaFile.canonicalFilePath(), 'tags': tagList})

        return mediaCount

    def searchMedia(self, tags, allTags = True):
        imageQuery = Query()
        tagList = re.split('[_+-.\s+]{1}', tags)
        if allTags:
            result = self.mediaTable.search(imageQuery.tags.all(tagList))
        else:
            result = self.mediaTable.search(imageQuery.tags.any(tagList))
        return [entry['mediaName'] for entry in result]

    def indexSounds(self, soundsPath):
        soundsCount = 0
        soundsDirIter = QDirIterator(soundsPath, self._soundsSupported, QDir.Files, QDirIterator.Subdirectories)

        self.soundsTable.truncate()
        while soundsDirIter.hasNext():
            soundsFile = soundsDirIter.nextFileInfo()
            soundsCount += 1
            # Add parts of the file name as tags
            baseFileName = soundsFile.completeBaseName()
            tagList = re.split('[_+-.\s+]{1}', baseFileName.lower())
            tagList.append(soundsFile.suffix().lower()) # Add the extension as a tag
            self.soundsTable.insert({ 'soundName': soundsFile.canonicalFilePath(), 'tags': tagList})

        return soundsCount

    def searchSounds(self, tags, allTags = True):
        imageQuery = Query()
        tagList = re.split('[_+-.\s+]{1}', tags)
        if allTags:
            result = self.soundsTable.search(imageQuery.tags.all(tagList))
        else:
            result = self.soundsTable.search(imageQuery.tags.any(tagList))
        return [entry['soundName'] for entry in result]
