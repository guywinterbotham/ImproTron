# This Python file uses the following encoding: utf-8
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage
import re

class MediaFileDatabase():
    def __init__(self):
        self.db = TinyDB(storage=MemoryStorage)
        self.imagesTable = self.db.table('media')

    def indexMedia(self, media):
        mediaCount = 0
        while media.hasNext():
            mediaFile = media.nextFileInfo()
            mediaCount += 1
            # Add parts of the file name as tags
            baseFileName = mediaFile.completeBaseName()
            tagList = re.split('[_+-.\s+]{1}', baseFileName.lower())
            tagList.append(mediaFile.suffix().lower()) # Add the extension as a tag
            self.imagesTable.insert({ 'mediaName': mediaFile.canonicalFilePath(), 'tags': tagList})

        return mediaCount

    def searchFiles(self, tags, allTags = True):
        imageQuery = Query()
        tagList = re.split('[_+-.\s+]{1}', tags)
        if allTags:
            result = self.imagesTable.search(imageQuery.tags.all(tagList))
        else:
            result = self.imagesTable.search(imageQuery.tags.any(tagList))
        return [entry['mediaName'] for entry in result]
