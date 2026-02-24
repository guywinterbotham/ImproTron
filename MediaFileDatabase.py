# This Python file uses the following encoding: utf-8
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage
from PySide6.QtCore import QDir, QDirIterator, QMimeDatabase
from PySide6.QtGui import QImageReader
from PySide6.QtMultimedia import QMediaFormat, QSoundEffect
import re
import logging
logger = logging.getLogger(__name__)

class MediaFileDatabase():
    def __init__(self):
        self.db = TinyDB(storage=MemoryStorage)
        self.media_table = self.db.table('media')
        self.sounds_table = self.db.table('sounds')

        # Dynamically get supported image formats
        self._media_supported = set()
        self._media_supported = {"*." + fmt.data().decode('utf-8') for fmt in QImageReader.supportedImageFormats()}

        # Dynamically get supported audio formats
        self._sounds_supported = set()
        self._sounds_supported = self._get_supported_audio_formats()

        # Dynamically get supported sound effects formats
        self._soundfx_supported = set()
        self._soundfx_supported = self._get_supported_soundfx_formats()

    def _get_supported_audio_formats(self):
        """Query Qt Multimedia for supported audio file extensions"""
        media_format = QMediaFormat()
        mime_db = QMimeDatabase()
        extensions = set()

        # Get all supported file formats for decoding (playback)
        supported_formats = media_format.supportedFileFormats(QMediaFormat.ConversionMode.Decode)

        for file_format in supported_formats:
            media_format.setFileFormat(file_format)
            mime_type = media_format.mimeType()
            mime_type_obj = mime_db.mimeTypeForName(mime_type.name())

            # Get file extensions for this MIME type
            for suffix in mime_type_obj.suffixes():
                extensions.add(f"*.{suffix}")

        logger.info(f"Supported audio formats: {sorted(extensions)}")
        return extensions

    def _get_supported_soundfx_formats(self):
        """Query Qt Multimedia for supported QSoundEffect MIME types and extensions"""
        mime_db = QMimeDatabase()
        extensions = set()

        # QSoundEffect provides a static method to get supported MIME types
        supported_mimes = QSoundEffect.supportedMimeTypes()

        for mime_name in supported_mimes:
            mime_type_obj = mime_db.mimeTypeForName(mime_name)

            # Extract file extensions (suffixes) for each supported MIME type
            for suffix in mime_type_obj.suffixes():
                extensions.add(f"*.{suffix}")

        logger.info(f"Supported QSoundEffect formats: {sorted(extensions)}")
        return extensions

    def media_supported(self):
        return self._media_supported

    def sounds_supported(self):
        return self._sounds_supported

    def sfx_supported(self):
        return self._soundfx_supported

    def get_media_supported_for_dialog(self):
        return " ".join(sorted(self._media_supported))

    def get_sounds_supported_for_dialog(self):
        return " ".join(sorted(self._sounds_supported))

    def get_sfx_supported_for_dialog(self):
        return " ".join(sorted(self._soundfx_supported))

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
