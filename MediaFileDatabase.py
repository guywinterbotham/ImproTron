# This Python file uses the following encoding: utf-8
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage
from PySide6.QtCore import QDir, QDirIterator
from PySide6.QtGui import QImageReader
import re
import logging

logger = logging.getLogger(__name__)

class MediaFileDatabase():
    def __init__(self):
        self.db = TinyDB(storage=MemoryStorage)
        self.media_table = self.db.table('media')
        self.sounds_table = self.db.table('sounds')

        self._media_supported = set()
        self._media_supported_dialog = ""

        self._media_supported = {"*." + fmt.data().decode('utf-8') for fmt in QImageReader.supportedImageFormats()}
        self._sounds_supported = {"*.alac", "*.aac", "*.mp3", "*.ac3", "*.wav", "*.flac"}

    def media_supported(self):
        return self._media_supported

    def sounds_supported(self):
        return self._sounds_supported

    def get_media_supported_for_dialog(self):
        return " ".join(self._media_supported)

    def get_sounds_supported_for_dialog(self):
        return " ".join(self._sounds_supported)

    # Helper utility for indexing
    def _index_files(self, path, supported_formats, table):
        file_count = 0
        dir_iter = QDirIterator(path, supported_formats, QDir.Files, QDirIterator.Subdirectories)

        table.truncate()
        while dir_iter.hasNext():
            file_info = dir_iter.nextFileInfo()
            file_count += 1
            base_file_name = file_info.completeBaseName()
            tag_list = re.split(r'[_+\-.\s]+', base_file_name.lower())
            tag_list.append(file_info.suffix().lower())
            table.insert({'name': file_info.canonicalFilePath(), 'tags': tag_list})

        return file_count

    def index_media(self, path):
        logger.info("Indexing Media Files ...")
        if not QDir(path).exists():
            logger.error(f"Media indexing path not found: {path}")
            raise FileNotFoundError(f"The path {path} does not exist.")
        return self._index_files(path, self._media_supported, self.media_table)

    def search_media(self, tags, all_tags = True):
        query = Query()
        tag_list = re.split(r'[_+\-.\s]+', tags)
        if all_tags:
            result = self.media_table.search(query.tags.all(tag_list))
        else:
            result = self.media_table.search(query.tags.any(tag_list))
        return [entry['name'] for entry in result]

    def index_sounds(self, path):
        logger.info("Indexing Sound Files ...")
        if not QDir(path).exists():
            logger.error(f"Sound indexing path not found: {path}")
            raise FileNotFoundError(f"The path {path} does not exist.")
        return self._index_files(path, self._sounds_supported, self.sounds_table)


    def search_sounds(self, tags, all_tags = True):
        query = Query()
        tag_list = re.split(r'[_+\-.\s]+', tags)
        if all_tags:
            result = self.sounds_table.search(query.tags.all(tag_list))
        else:
            result = self.sounds_table.search(query.tags.any(tag_list))
        return [entry['name'] for entry in result]
