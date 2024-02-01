# This Python file uses the following encoding: utf-8
from PySide6.QtCore import QDirIterator, QStandardPaths, QDir
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage
import re

class MediaFileDatabase():
    def __init__(self):
        self.db = TinyDB(storage=MemoryStorage)
        self.imagesTable = self.db.table('media')
        self.indexMedia()

    def indexMedia(self):
        pictureDir = QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0]
        media = QDirIterator(pictureDir, {"*.jpg","*.gif", "*.bmp", "*.png"}, QDir.Files, QDirIterator.Subdirectories)
        while media.hasNext():
            mediaFile = media.nextFileInfo()
            baseFileName = mediaFile.completeBaseName ()
            tags = re.split('[_+-.\s+]{1}', baseFileName)
            for tag in tags:
                self.imagesTable.insert({'tag': tag.lower(), 'mediaName': mediaFile.canonicalFilePath()})

    def searchFiles(self, tags):
        imageQuery = Query()
        result = self.imagesTable.search(imageQuery.tag.one_of(tags))
        return [entry['mediaName'] for entry in result]
