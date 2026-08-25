# This Python file uses the following encoding: utf-8
from PySide6.QtCore import QDir, QDirIterator, QMimeDatabase, QStandardPaths, QSortFilterProxyModel, Qt, QModelIndex
from PySide6.QtGui import QImageReader, QStandardItem, QStandardItemModel
from PySide6.QtMultimedia import QMediaFormat, QSoundEffect
import logging
import re

logger = logging.getLogger(__name__)

class TagFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_terms = []
        self._match_all = False
        self._sfx_only = False
        self._sfx_extensions = set()

    def set_sfx_extensions(self, raw_extensions: set[str]):
        # Strip wildcards and lower case once during startup
        self._sfx_extensions = {ext.lstrip("*.").lower() for ext in raw_extensions}

    def set_filter(self, query: str, match_all: bool, sfx_only: bool = False):
        # Pre-process search terms ONCE per filter change, not per row
        self._search_terms = query.strip().lower().split()
        self._match_all = match_all
        self._sfx_only = sfx_only
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        index = self.sourceModel().index(source_row, 0, source_parent)
        # Directly retrieve pre-parsed lowered set stored during indexing
        item_tags: set = index.data(Qt.ItemDataRole.UserRole + 1) or set()

        # 1. Hard SFX Check - O(1) set intersection
        if self._sfx_only and not (self._sfx_extensions & item_tags):
            return False

        # 2. Empty query pass
        if not self._search_terms:
            return True

        # 3. Substring search over pre-indexed tag tokens
        if self._match_all:
            return all(
                any(term in tag for tag in item_tags)
                for term in self._search_terms
            )
        return any(
            any(term in tag for tag in item_tags)
            for term in self._search_terms
        )

class MediaFileRegistry:
    def __init__(self):
        # Data storage models
        self.media_model = QStandardItemModel()
        self.sounds_model = QStandardItemModel()

        # Format detection
        self._media_supported = {"*." + fmt.data().decode("utf-8") for fmt in QImageReader.supportedImageFormats()}
        self._sounds_supported = self._get_supported_audio_formats()
        self._soundfx_supported = self._get_supported_soundfx_formats()

    def _get_supported_audio_formats(self) -> set[str]:
        media_format = QMediaFormat()
        mime_db = QMimeDatabase()
        extensions = set()
        for file_format in media_format.supportedFileFormats(QMediaFormat.ConversionMode.Decode):
            media_format.setFileFormat(file_format)
            mime_type_obj = mime_db.mimeTypeForName(media_format.mimeType().name())
            for suffix in mime_type_obj.suffixes():
                extensions.add(f"*.{suffix}")
        logger.info(f"Supported audio formats: {sorted(extensions)}")
        return extensions

    def _get_supported_soundfx_formats(self) -> set[str]:
        mime_db = QMimeDatabase()
        extensions = set()
        for mime_name in QSoundEffect.supportedMimeTypes():
            mime_type_obj = mime_db.mimeTypeForName(mime_name)
            for suffix in mime_type_obj.suffixes():
                extensions.add(f"*.{suffix}")
        logger.info(f"Supported QSoundEffect formats: {sorted(extensions)}")
        return extensions

    # --- Format Utility Methods (Preserved API) ---
    def media_supported(self): return self._media_supported
    def sounds_supported(self): return self._sounds_supported
    def sfx_supported(self): return self._soundfx_supported
    def get_media_supported_for_dialog(self): return " ".join(sorted(self._media_supported))
    def get_sounds_supported_for_dialog(self): return " ".join(sorted(self._sounds_supported))
    def get_sfx_supported_for_dialog(self): return " ".join(sorted(self._soundfx_supported))

    # --- Indexing ---
    def _index_files(self, path: str, supported_formats: set[str], model: QStandardItemModel) -> int:
        # Force QDir to drop cached file system entries
        d = QDir(path)
        d.refresh()

        model.beginResetModel()
        model.removeRows(0, model.rowCount())

        file_count = 0
        # Include Subdirectories; refresh directory entry status
        dir_iter = QDirIterator(
            path,
            list(supported_formats),
            QDir.Filter.Files,
            QDirIterator.IteratorFlag.Subdirectories
        )

        while dir_iter.hasNext():
            dir_iter.next()
            file_info = dir_iter.fileInfo()

            # Ensure file exists and is completely written/readable by OS
            if not file_info.exists() or file_info.size() == 0:
                continue

            file_count += 1
            base_file_name = file_info.completeBaseName()
            tag_list = re.split(r'[_+\-.\s]+', base_file_name.lower())
            tag_list.append(file_info.suffix().lower())

            item = QStandardItem(file_info.fileName())
            item.setData(file_info.canonicalFilePath(), Qt.ItemDataRole.UserRole)
            item.setData(set(tag_list), Qt.ItemDataRole.UserRole + 1)
            model.appendRow(item)

        model.endResetModel()
        return file_count

    def index_media(self, path: str) -> int:
        logger.info(f"Indexing Media Files in {path}")
        if not QDir(path).exists():
            logger.error(f"Media indexing path not found: {path}. Using Default.")
            path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        # Pass self.media_model (QStandardItemModel), NOT self.media_table
        return self._index_files(path, self._media_supported, self.media_model)

    def index_sounds(self, path: str) -> int:
        logger.info(f"Indexing Sound Files in {path}")
        if not QDir(path).exists():
            logger.error(f"Sound indexing path not found: {path}. Using Default.")
            path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MusicLocation)
        # Pass self.sounds_model (QStandardItemModel), NOT self.sounds_table
        return self._index_files(path, self._sounds_supported, self.sounds_model)

    def search_media(self, tags: str = "", all_tags: bool = True) -> list[str]:
        """Query source model tags directly without touching UI proxies."""
        if not tags.strip():
            # Return all canonical paths if search is empty
            return [
                self.media_model.item(row).data(Qt.ItemDataRole.UserRole)
                for row in range(self.media_model.rowCount())
            ]

        search_tokens = set(re.split(r'[_+\-.\s]+', tags.lower()))
        results = []

        for row in range(self.media_model.rowCount()):
            item = self.media_model.item(row)
            item_tags = item.data(Qt.ItemDataRole.UserRole + 1)
            if not item_tags:
                continue

            matches = (
                all_tags and search_tokens.issubset(item_tags)
            ) or (
                not all_tags and bool(search_tokens & item_tags)
            )
            if matches:
                results.append(item.data(Qt.ItemDataRole.UserRole))

        return results

    def search_sounds(self, tags: str = "", all_tags: bool = True, sfx_only: bool = False) -> list[str]:
        query_str = tags.strip().lower()
        tokens = set(filter(None, re.split(r'[_+\-.\s]+', query_str)))
        clean_sfx = {ext.lstrip("*.").lower() for ext in self._soundfx_supported}
        results = []

        for row in range(self.sounds_model.rowCount()):
            item = self.sounds_model.item(row)
            if not item:
                continue

            item_tags = item.data(Qt.ItemDataRole.UserRole + 1) or set()

            # SFX Filter Guard
            if sfx_only and not (clean_sfx & item_tags):
                continue

            # Tag Query Guard
            if not tokens:
                is_match = True
            elif all_tags:
                is_match = tokens.issubset(item_tags)
            else:
                is_match = bool(tokens & item_tags)

            if is_match:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path:
                    results.append(path)

        return results
