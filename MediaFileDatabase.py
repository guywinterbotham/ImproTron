# This Python file uses the following encoding: utf-8
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage
import re

class MediaFileDatabase():
    def __init__(self):
        self.db = TinyDB(storage=MemoryStorage)
        self.mediaTable = self.db.table('media')
        self.soundsTable = self.db.table('sounds')

    def indexMedia(self, media):
        mediaCount = 0
        self.mediaTable.truncate()
        while media.hasNext():
            mediaFile = media.nextFileInfo()
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

    def indexSounds(self, sounds):
        soundsCount = 0
        self.soundsTable.truncate()
        while sounds.hasNext():
            soundsFile = sounds.nextFileInfo()
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
