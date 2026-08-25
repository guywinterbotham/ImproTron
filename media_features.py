# media_features.py
import logging
from PySide6.QtCore import (Qt, QObject, Slot, Signal, QFileInfo, QDirIterator, QUrl, QRandomGenerator, QVariantAnimation, QTimer,
                                QEasingCurve, QFile, QJsonDocument, QSaveFile, QIODevice, QDir, QModelIndex, QFileSystemWatcher)
from PySide6.QtGui import QImageReader, QColor, QMovie
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QStyle, QPushButton, QListWidgetItem, QColorDialog
from PySide6.QtMultimedia import QMediaPlayer, QSoundEffect, QAudioOutput, QMediaMetaData, QMediaFormat
from Improtronics import SoundFX
from MediaFileDatabase import TagFilterProxyModel, MediaFileRegistry
from monitor_preview import SmartOverlayLabel
import utilities

logger = logging.getLogger(__name__)

# Module to encapsulate image and media search along with the media database management
class MediaFeatures(QObject):
    mainMediaShow = Signal(str)    # Custom signal that decouples the media display from controlboard
    auxMediaShow  = Signal(str)    # Custom signal that decouples the media display from controlboard

    def __init__(self, ui, settings, media_model, mainDisplay, auxiliaryDisplay):
        super(MediaFeatures, self).__init__()

        self.ui = ui
        self.active_sound_effects = []
        self._settings = settings
        self.media_model = media_model
        self.mainDisplay = mainDisplay
        self.auxiliaryDisplay = auxiliaryDisplay

        # Set up the model

        # Native Qt Registries for sound and media
        self.media_file_database = MediaFileRegistry()

        # Wire Proxy Models for UI Views
        self.media_proxy = TagFilterProxyModel(self)
        self.media_proxy.setSourceModel(self.media_file_database.media_model)
        self.ui.mediaSearchResultsLV.setModel(self.media_proxy)

        self.sound_proxy = TagFilterProxyModel(self)
        self.sound_proxy.setSourceModel(self.media_file_database.sounds_model)
        # Seed supported extensions from MediaFileRegistry
        self.sound_proxy.set_sfx_extensions(self.media_file_database.sfx_supported())
        self.ui.soundSearchResultsLV.setModel(self.sound_proxy)

        # Initial Image Indexing
        media_count = self.media_file_database.index_media(self._settings.get_media_directory())
        self.ui.mediaFilesCountLBL.setText(str(media_count))

        # Initial Sound Indexing
        sound_count = self.media_file_database.index_sounds(self._settings.get_sound_directory())
        self.ui.soundFilesCountLBL.setText(str(sound_count))

        # Setup recursive filesystem watcher
        self._dir_watcher = QFileSystemWatcher(self)
        self._dir_watcher.directoryChanged.connect(self._on_directory_updated)

        # Initial binding of all active paths and subpaths
        self.refresh_directory_watches()

        # Get supported video file types
        self._video_extensions = set()
        self._supported_video_types = []
        self._initialize_supported_video_formats()

        self.all_supported_slide_formats = set()
        self._initialize_supported_slide_formats()

        # Audio Player
        self.music_player = QMediaPlayer(self)
        self.music_audio = QAudioOutput(self)
        self.music_player.setAudioOutput(self.music_audio)

        # Auto-advance logic
        self.music_player.mediaStatusChanged.connect(self._on_status_changed)

        # Variables for fade control
        self._fade_animation = QVariantAnimation(self)
        self._fade_animation.valueChanged.connect(self._handle_fade_step)
        self._fade_animation.finished.connect(self._finalize_music_stop)

        # Promote the screen preview labels so they can handle GIFs with smart overlays
        # --- 1. GAME TAB PREVIEW (mediaSearchPreviewLBL) REPLACEMENT ---
        if hasattr(self.ui, 'mediaSearchPreviewLBL') and not isinstance(self.ui.mediaSearchPreviewLBL, SmartOverlayLabel):
            old_label = self.ui.mediaSearchPreviewLBL
            if hasattr(self.ui, 'mediaPreviewVL') and self.ui.mediaPreviewVL is not None:
                layout = self.ui.mediaPreviewVL
                index = layout.indexOf(old_label)

                if index != -1:
                    stretch = layout.stretch(index)
                    alignment = layout.alignment()
                    old_stylesheet = old_label.styleSheet()  # Capture Style Sheet

                    new_label = SmartOverlayLabel(old_label.parentWidget())
                    new_label.setObjectName(old_label.objectName())
                    new_label.setMinimumSize(old_label.minimumSize())
                    new_label.setMaximumSize(old_label.maximumSize())
                    new_label.setSizePolicy(old_label.sizePolicy())
                    new_label.setStyleSheet(old_stylesheet)  # Apply Style Sheet

                    layout.removeWidget(old_label)
                    layout.insertWidget(index, new_label, stretch=stretch, alignment=alignment)

                    self.ui.mediaSearchPreviewLBL = new_label
                    old_label.deleteLater()
            else:
                logger.error("Could not find the 'mediaPreviewVL' layout container at runtime.")

        # Overlay text color default
        self._overlay_color = QColor(Qt.GlobalColor.white)
        self.ui.mediaSearchtOverlayColorPB.setStyleSheet(utilities.style_sheet(self._overlay_color))

        # Playback current track playback state
        self.current_track_index = -1
        self.playback_queue = []
        self.is_queue_mode = False  # The gatekeeper flag, signals if a queue or single track is playing.

        # Sound Pallette Setup
        self.sfx_buttons = [] # empty array
        _volume = self.ui.soundFXVolumeHS.value()/self.ui.soundFXVolumeHS.maximum() # Use the ui default as a guide

        # Stop all Panic Button
        self.ui.sfxStopAllPB.clicked.connect(self.stop_all_sfx)

        # Don't assume the buttons are in the same order in the grid as they are numbered
        # Look for each button by its object name. The number of buttons can be derived
        # from the grid
        for button in range(self.ui.soundFXGrid.count()):
            sfx_button = self.ui.findChild(QPushButton, "soundFXPB" +str(button+1))
            _soundFX = SoundFX(sfx_button, self.media_file_database)
            _soundFX.set_fx_volume(_volume)
            self.sfx_buttons.append(_soundFX)

        # Use standard icons
        self.ui.soundPlayPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.soundPausePB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.soundStopPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaStop))
        self.ui.soundFadePB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaVolumeMuted))
        self.ui.soundMoveUpPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))
        self.ui.soundMoveDownPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))
        self.ui.soundAddToListPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        self.ui.soundRemoveFromListPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton))

        # Sound Pallettes
        self.palletteSelect = self.ui.soundPalettesCB
        self.load_sound_pallettes()

        # Debounce timer for live search input, this will help with responsiveness during partial lookups.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(75)  # 75ms delay
        self._search_timer.timeout.connect(self._exec_sound_search)

        self.connect_slots()

    # Set up audio visual connections
    def connect_slots(self):
        # Image Search Connections
        self.ui.mediaSearchResultsLV.selectionModel().currentChanged.connect(
            lambda current, previous: self.preview_selected_media(current)
        )
        self.ui.setMediaLibraryPB.clicked.connect(self.set_media_library)

        # Media live search
        self.ui.mediaSearchTagsLE.textChanged.connect(self.search_media)
        self.ui.allMediaTagsCB.toggled.connect(self.search_media)

        # 3. Enter key fires media instantly (or drops focus down to list)
        self.ui.mediaSearchTagsLE.returnPressed.connect(self.fire_top_result_or_focus)

        # Sound live search
        self.ui.soundSearchTagsLE.textChanged.connect(self.search_sounds)
        self.ui.allsoundTagsCB.toggled.connect(self.search_sounds)
        self.ui.soundSearchSFXCB.toggled.connect(self.search_sounds)
        self.ui.soundSearchSFXCB.toggled.connect(self.toggle_sfx_controls) # disables pause and fade for SFX mode

        self.ui.searchToMainShowPB.clicked.connect(self.search_to_main_show)
        self.ui.searchToAuxShowPB.clicked.connect(self.search_to_aux_show)

        # Image Overlay Actions
        self.ui.mediaSearchOverlayLE.textChanged.connect(self.show_overlay_text)
        self.ui.mediaSearchtOverlayColorPB.clicked.connect(self.pick_overlay_text_color)
        self.ui.mediaSearchtOverlayColorSLD.valueChanged.connect(self.scale_overlay_text)
        self.ui.mediaSearchtOverlayClearPB.clicked.connect(self.clear_image)
        self.ui.mediaSearchtOverlayFB.currentFontChanged.connect(self.style_overlay_text)

        # Sound Search Connections
        self.ui.soundSearchTagsLE.returnPressed.connect(self.search_sounds)
        self.ui.setSoundLibraryPB.clicked.connect(self.set_sound_library)

        self.ui.soundSearchResultsLV.doubleClicked.connect(self.sound_play)
        self.ui.soundQueueLW.itemDoubleClicked.connect(self.sound_play)
        self.ui.soundPlayPB.clicked.connect(self.sound_play)
        self.ui.soundPausePB.clicked.connect(self.music_pause)
        self.ui.soundStopPB.clicked.connect(self.music_stop)
        self.ui.soundFadePB.clicked.connect(self.music_fade)

        self.ui.loadSoundQueuePB.clicked.connect(self.load_sound_queue)
        self.ui.saveSoundQueuePB.clicked.connect(self.save_sound_queue)
        self.ui.saveSoundFXPallettePB.clicked.connect(self.save_soundFX_pallette)
        self.ui.clearSoundQueuePB.clicked.connect(self.clear_sound_queue)
        self.ui.soundFXVolumeHS.valueChanged.connect(self.set_fx_volume)

        self.ui.soundMoveUpPB.clicked.connect(self.sound_move_up)
        self.ui.soundMoveDownPB.clicked.connect(self.sound_move_down)
        self.ui.soundAddToListPB.clicked.connect(self.sound_add_to_list)
        self.ui.soundRemoveFromListPB.clicked.connect(self.sound_remove_from_list)

        # Playlist controls
        self.ui.playlistPlayPB.clicked.connect(self.handle_play_list_request)

        # Mini Player Controls
        self.ui.playPlayerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.playPlayerPB.clicked.connect(self.music_play)

        self.ui.pausePlayerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.pausePlayerPB.clicked.connect(self.music_pause)

        self.ui.stopPlayerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaStop))
        self.ui.stopPlayerPB.clicked.connect(self.music_stop)

        self.ui.loopPlayerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        self.ui.loopPlayerPB.clicked.connect(self.loop_media)

        self.ui.fadePlayerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaVolumeMuted))
        self.ui.fadePlayerPB.clicked.connect(self.music_fade)

        # Connect the media player to retrieve duration after the file is loaded
        self.music_player.positionChanged.connect(self._update_player_progress)
        self.music_player.durationChanged.connect(self._update_player_duration)
        self.music_player.metaDataChanged.connect(self.update_metadata_display)

        # Connect error signal
        self.music_player.errorOccurred.connect(self.music_player_handle_error)

        # Sound Palletes
        self.palletteSelect.currentIndexChanged.connect(self.load_sound_effects)
# #### connections

    # Directory Monitoring Helper & Event Methods

    def _get_all_subdirs(self, root_path: str) -> list[str]:
        """Recursively fetches root path and all nested subdirectories."""
        if not root_path or not QDir(root_path).exists():
            return []

        dirs = [root_path]
        dir_iter = QDirIterator(
            root_path,
            QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot,
            QDirIterator.IteratorFlag.Subdirectories,
        )
        while dir_iter.hasNext():
            dirs.append(dir_iter.next())
        return dirs

    def refresh_directory_watches(self):
        """Registers root directories and all child folders with QFileSystemWatcher."""
        current_paths = self._dir_watcher.directories()
        if current_paths:
            self._dir_watcher.removePaths(current_paths)

        all_paths = []
        all_paths.extend(
            self._get_all_subdirs(self._settings.get_media_directory())
        )
        all_paths.extend(
            self._get_all_subdirs(self._settings.get_sound_directory())
        )

        if all_paths:
            self._dir_watcher.addPaths(all_paths)

    @Slot(str)
    def _on_directory_updated(self, updated_path: str):
        media_root = self._settings.get_media_directory()
        sound_root = self._settings.get_sound_directory()

        if media_root and updated_path.startswith(media_root):
            count = self.media_file_database.index_media(media_root)
            self.ui.mediaFilesCountLBL.setText(str(count))
            # Re-apply current search box text over the updated model
            self.search_media()

        if sound_root and updated_path.startswith(sound_root):
            count = self.media_file_database.index_sounds(sound_root)
            self.ui.soundFilesCountLBL.setText(str(count))
            # Re-apply current search box text over the updated model
            self.search_sounds()

        self.refresh_directory_watches()

    # Media Utilties
    def select_image_file(self):
        selectedFileName = QFileDialog.getOpenFileName(self.ui, "Select Media", self._settings.get_media_directory() , "Media Files "+self.media_file_database.get_media_supported_for_dialog())
        return selectedFileName[0]

    def isImage(self, fileName):
        if len(fileName) > 0:
            if QFileInfo.exists(fileName):
                mediaInfo = QFileInfo(fileName)
                return bytes(mediaInfo.suffix().lower(),"ascii") in  QImageReader.supportedImageFormats()
            else:
                return False
        else:
            return False

    # Checks on various media types
    def isAnimatedGIF(self, file_name):
        if len(file_name) > 0:
            if QFileInfo.exists(file_name):
                mediaInfo = QFileInfo(file_name)
                return bytes(mediaInfo.suffix().lower(),"ascii") in QMovie.supportedFormats()
            else:
                return False
        else:
            return False

    def isVideo(self, file_name):
        if len(file_name) > 0:
            if QFileInfo.exists(file_name):
                mediaInfo = QFileInfo(file_name)
                return mediaInfo.suffix().lower() in  self._supported_video_types
            else:
                return False
        else:
            return False

    # Query Qt Multimedia for supported video file extensions
    def _initialize_supported_video_formats(self):
        media_format = QMediaFormat()
        self._supported_video_types = []
        self._video_extensions = set()

        # Get all supported file formats for decoding (containers)
        supported_formats = media_format.supportedFileFormats(QMediaFormat.ConversionMode.Decode)

        for file_format in supported_formats:
            media_format.setFileFormat(file_format)
            mime_type = media_format.mimeType() # This returns a QMimeType object

            # Check if the MIME type is categorized as video (e.g., 'video/mp4')
            if mime_type.name().startswith("video/"):
                # Get all associated extensions for this video type
                for suffix in mime_type.suffixes():
                    self._video_extensions.add(f"*.{suffix}")
                    self._supported_video_types.append(suffix)

        # Fallback: Some systems don't report containers correctly through QMediaFormat
        # but the MIME database knows them. If the list is still thin,
        # we can ensure common ones are present.
        if not self._video_extensions:
            logger.warning("QMediaFormat reported no video types; using common fallbacks.")
            self._supported_video_types = ["mp4", "mov", "mkv", "avi", "wmv", "webm"]
            self._video_extensions.update(["*.mp4", "*.mov", "*.mkv", "*.avi", "*.wmv", "*.webm"])

        logger.info(f"Supported video formats: {sorted(self._video_extensions)}")

    # Combines Image, and Video formats into a single cached list for QDir filtering.
    def _initialize_supported_slide_formats(self):
        # Image formats from QImageReader
        img_ext = {f"*.{fmt.data().decode().lower()}" for fmt in QImageReader.supportedImageFormats()}

        # Combine into a unique set to remove overlaps (like .gif or .m4a) as a list so it's ready for QDir.entryInfoList
        self.all_supported_slide_formats = img_ext | self._video_extensions

    # Return all the supported image, gif-like and video files types Qt supports
    def get_all_supported_slide_types(self):
        return self.all_supported_slide_formats

    # Reset the tree view of media files
    def reset_media_view(self, directory):
        self.image_tree_view = self.ui.slideShowFilesTreeView
        self.image_tree_view.setModel(self.media_model)
        self.image_tree_view.setRootIndex(self.media_model.index(directory))
        for i in range(1, self.media_model.columnCount()):
            self.image_tree_view.header().hideSection(i)
        self.image_tree_view.setHeaderHidden(True)

    # Used when a a specific asset is need such as a logo
    def find_media(self, tags):
        found_files = self.media_file_database.search_media(tags, True)

        if len(found_files) > 0:
            found_file = found_files[0]
            found_file_info = QFileInfo(found_file)
            file = found_file_info.absoluteFilePath()

            return file
        else:
            logging.warning("Find Media: file matching {tags} not found")

    # Helper function that loads a file name for OSC and from a UI selection
    def read_queue(self,fileName):

        file = QFile(fileName)
        if not file.open(QIODevice.ReadOnly):
            logger.error(f"Music Player Error: {fileName} does not exist")
            return

        info = QFileInfo(fileName)
        self.ui.soundFileNameLBL.setText(info.completeBaseName())

        raw_data = file.readAll()
        file.close()

        # Parse to Python Dictionary
        doc = QJsonDocument.fromJson(raw_data)
        if doc.isNull():
            logger.error(f"Invalid JSON format for music queue {fileName}.")
            return

        # toVariant() converts the JSON directly to a Python dict or list
        sound_data = doc.toVariant()

        if isinstance(sound_data, dict):
            self.ui.soundQueueLW.clear()

            # We sort the keys (sound0, sound1, etc.) to ensure the
            # queue loads in the correct numerical order.
            for key in sorted(sound_data.keys()):
                path = sound_data[key]
                if path:
                    file_info = QFileInfo(path)

                    # Create standard item with the filename as the text
                    item = QListWidgetItem(file_info.fileName(), self.ui.soundQueueLW)

                    # STORE the data: Attach the QFileInfo object to the item
                    item.setData(Qt.UserRole, file_info)

                    # STYLE the item: Set the font size
                    font = item.font()
                    font.setPointSize(12)
                    item.setFont(font)

    # Media Management Slots
    @Slot()
    def search_media(self):
        """Refreshes proxy filter bound to the QListView UI."""
        query = self.ui.mediaSearchTagsLE.text()
        match_all = self.ui.allMediaTagsCB.isChecked()

        # Re-evaluate proxy filter over the updated source model
        self.media_proxy.invalidate()
        self.media_proxy.set_filter(query, match_all)

    # Music Player Controls
    @Slot()
    def music_play(self):
        if self.music_player.playbackState() == QMediaPlayer.PausedState:
            self.music_player.play()
            return

        self.music_player.setPosition(0)
        self.music_player.play()

    @Slot()
    def music_pause(self):
        if self.music_player.playbackState() == QMediaPlayer.PausedState:
            self.music_player.play()
            return

        if self.music_player.isPlaying():
            self.music_player.pause()

    @Slot()
    def music_stop(self):
        if self.ui.soundSearchSFXCB.isChecked():
            self.stop_all_sfx()
        else:
            self.music_player.stop()

    def music_player_handle_error(self, error, error_string):
        # Log the error
        logger.error(f"Music Player Error: {error} - {error_string}")

    # Stops any active fade animation and restores volume to the current UI slider level.
    def reset_fade_and_restore_volume(self):
        if self._fade_animation.state() == QVariantAnimation.State.Running:
            self._fade_animation.stop()

        # Restore target volume from UI slider
        target_vol = self.ui.soundVolumeSL.value() / max(1, self.ui.soundVolumeSL.maximum())
        self.music_audio.setVolume(target_vol)

    # Disables Pause and Fade buttons when SFX mode is active.
    @Slot(bool)
    def toggle_sfx_controls(self, sfx_enabled: bool):
        controls_enabled = not sfx_enabled
        self.ui.soundPausePB.setEnabled(controls_enabled)
        self.ui.soundFadePB.setEnabled(controls_enabled)

    # Playlist controls

    # Decides whether to play a single selection or start the playlist.
    # If a specific item is selected and we aren't already playing, play that.
    # Otherwise, start the 'Play All' sequence.
    @Slot()
    def handle_play_list_request(self):
        self.is_queue_mode = True
        # Check if Shuffle (Random Play) is enabled
        if self.ui.shuffleCB.isChecked():
            self.shuffle_playlist_widget()

        # Build the logic queue from the current state of the list widget
        self.playback_queue = [self.ui.soundQueueLW.item(i).data(Qt.UserRole).absoluteFilePath()
                              for i in range(self.ui.soundQueueLW.count())]

        # Start from the first track
        self.current_track_index = 0
        self.play_current_index()

    # Physically randomizes the QListWidget using only Qt components.
    def shuffle_playlist_widget(self):
        items = []

        # 1. Pull all items out of the widget
        while self.ui.soundQueueLW.count() > 0:
            items.append(self.ui.soundQueueLW.takeItem(0))

        # 2. Use our Qt-based helper to shuffle the list of QListWidgetItems
        QtListShuffler.shuffle(items)

        # 3. Re-insert the shuffled items back into the UI
        for item in items:
            self.ui.soundQueueLW.addItem(item)

    #Automatically plays next track when one ends.
    @Slot(int)
    def _on_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.is_queue_mode == True:
            self.current_track_index += 1
            self.play_current_index()

    # Uses the music player for background music.
    def play_current_index(self):
        if 0 <= self.current_track_index < len(self.playback_queue):
            song_path = self.playback_queue[self.current_track_index]
            self.ui.soundQueueLW.setCurrentRow(self.current_track_index)

            # Stop active fade and restore volume
            self.reset_fade_and_restore_volume()

            self.music_player.setSource(QUrl.fromLocalFile(song_path))
            self.music_player.play()
        else:
            logging.debug("Playlist finished")
            if self.ui.loopPlayerPB.isChecked():
                self.start_playlist_playback()

    # Responds to an OSC command to play a playlist
    @Slot(float, str)
    def onOSCServerPlaylistAction(self, play_list):
        # Zero length tag list will stop play
        if len(play_list) == 0:
            self.music_player.stop()
            return

        config_dir = QDir(self._settings.get_config_dir())
        full_path = config_dir.filePath(play_list)

        self.read_queue(full_path)
        self.handle_play_list_request()

    # Responds to an OSC command to show media on a monitor
    @Slot(str, str)
    def onOSCServerMediaAction(self, monitor, tags):

        # Define the set of valid monitor targets
        VALID_MONITORS = {"aux", "main", "both"}

        # Check for valid monitor string
        if monitor not in VALID_MONITORS:
            logging.warning(f"OSC Show Media: Invalid monitor target '{monitor}'. Must be one of {VALID_MONITORS}.")
            return # Stop execution if the monitor is invalid

        # Check for missing tags
        if len(tags) == 0:
            logging.warning("OSC Show Media: missing search tags")
            return

        found_files = self.media_file_database.search_media(tags, True)

        if len(found_files) > 0:
            found_file = found_files[0]
            found_file_info = QFileInfo(found_file)
            file = found_file_info.absoluteFilePath()

            # The monitor checks for emitting the signal remain the same
            if monitor == "main" or monitor == "both":
                self.mainMediaShow.emit(file)

            if monitor == "aux" or monitor == "both":
                self.auxMediaShow.emit(file)

        else:
            logging.warning(f"OSC Play Media: file matching {tags} not found for {monitor}")

    # Allow the location of the top directory of the media library to be changed. Reindex the database after the change.
    @Slot()
    def set_media_library(self):
        setDir = QFileDialog.getExistingDirectory(self.ui,
                "Select the Media Library location",
                self._settings.get_media_directory(), QFileDialog.ShowDirsOnly)
        if setDir:
            self._settings.set_media_directory(setDir)
            media_count = self.media_file_database.index_media(setDir)
            self.ui.mediaFilesCountLBL.setText(str(media_count))

            # The Media Library is also part of the media model so reset it
            self.reset_media_view(setDir)

            self.refresh_directory_watches() # Re-bind watcher tree

    @Slot(QModelIndex)
    def preview_selected_media(self, index: QModelIndex):
        # 1. Extract the QFileInfo from UserRole
        file_path = index.data(Qt.ItemDataRole.UserRole)
        if not file_path:
            return

        # 2. Display the path. This is also used to drive pushing the asset when anything has changed like the text overlay
        self.ui.mediaFileNameLBL.setText(file_path)

        # 3. Handle Preview Logic
        self.ui.mediaSearchPreviewLBL.set_text_overlay(
            background_path = file_path,
            overlay_text = self.ui.mediaSearchOverlayLE.text(),
            font = self.ui.mediaSearchtOverlayFB.currentFont() ,
            scale = self.ui.mediaSearchtOverlayColorSLD.value(),
            color = self._overlay_color)

    #Triggered when a list item is selected/clicked to preview media.
    @Slot(QListWidgetItem)
    def show_media_preview_main(self, item):
        # 1. Retrieve the QFileInfo object from the UserRole
        file_info = item.data(Qt.UserRole)

        # 2. Ensure the data exists before emitting
        if file_info:
            path = file_info.absoluteFilePath()
            self.mainMediaShow.emit(path)

    @Slot()
    def search_to_main_show(self):
        self.ui.imagePreviewMain.set_text_overlay(
            background_path = self.ui.mediaFileNameLBL.text(),
            overlay_text = self.ui.mediaSearchOverlayLE.text(),
            font = self.ui.mediaSearchtOverlayFB.currentFont() ,
            scale = self.ui.mediaSearchtOverlayColorSLD.value(),
            color = self._overlay_color)

        self.mainDisplay.show_overlay_text(
            background_path = self.ui.mediaFileNameLBL.text(),
            overlay_text = self.ui.mediaSearchOverlayLE.text(),
            font = self.ui.mediaSearchtOverlayFB.currentFont() ,
            scale = self.ui.mediaSearchtOverlayColorSLD.value(),
            textColor = self._overlay_color)

    @Slot()
    def search_to_aux_show(self):
        self.ui.imagePreviewAuxiliary.set_text_overlay(
            background_path = self.ui.mediaFileNameLBL.text(),
            overlay_text = self.ui.mediaSearchOverlayLE.text(),
            font = self.ui.mediaSearchtOverlayFB.currentFont() ,
            scale = self.ui.mediaSearchtOverlayColorSLD.value(),
            color = self._overlay_color)

        self.auxiliaryDisplay.show_overlay_text(
            background_path = self.ui.mediaFileNameLBL.text(),
            overlay_text = self.ui.mediaSearchOverlayLE.text(),
            font = self.ui.mediaSearchtOverlayFB.currentFont() ,
            scale = self.ui.mediaSearchtOverlayColorSLD.value(),
            textColor = self._overlay_color)

    @Slot()
    def search_sounds(self):
        """Restarts debounce timer on UI input."""
        self._search_timer.start()

    def _exec_sound_search(self):
        """Executes actual proxy re-evaluation after input pause."""
        query = self.ui.soundSearchTagsLE.text()
        match_all = self.ui.allsoundTagsCB.isChecked()
        sfx_only = self.ui.soundSearchSFXCB.isChecked()

        self.sound_proxy.set_filter(query, match_all, sfx_only)

    # Respond to the request to change volume
    @Slot(int)
    def set_sound_volume(self, value):
        self.music_audio.setVolume(value/self.ui.soundVolumeSL.maximum())

    @Slot()
    def set_sound_library(self):
        setDir = QFileDialog.getExistingDirectory(self.ui,
                "Select the Sound Library location",
                self._settings.get_sound_directory(), QFileDialog.ShowDirsOnly)
        if setDir:
            self._settings.set_sound_directory(setDir)
            soundsCount = self.media_file_database.index_sounds(setDir)
            self.ui.soundFilesCountLBL.setText(str(soundsCount))
            self.refresh_directory_watches() # Re-bind watcher tree

    # Responds to an OSC command to play an audio file
    @Slot(str)
    def onOSCServerSoundAction(self, tags):
        # Zero length tag list will stop play
        if len(tags) == 0:
            self.music_player.stop()
            return

        foundSounds = self.media_file_database.search_sounds(tags, True)
        if len(foundSounds) > 0:
            sound = foundSounds[0]
            soundFile = QFileInfo(sound)
            file = soundFile.absoluteFilePath()

            # Stop active fade and restore volume
            self.reset_fade_and_restore_volume()

            self.music_player.setSource(QUrl.fromLocalFile(file))
            self.music_player.setPosition(0)
            self.music_player.play()

        else:
            logging.warning(f"OSC Play Sound: sound matching {tags} not found")

    # Responds to an OSC command to play an audio file starting from a specific point in the audio file.
    @Slot(float, str)
    def onOSCServerSeekAction(self, seek_point, tags):
        # Zero length tag list will stop play
        if len(tags) == 0:
            self.music_player.stop()
            return

        foundSounds = self.media_file_database.search_sounds(tags, True)
        if len(foundSounds) > 0:
            sound = foundSounds[0]
            soundFile = QFileInfo(sound)
            file = soundFile.absoluteFilePath()

            # Stop active fade and restore volume
            self.reset_fade_and_restore_volume()

            self.music_player.setSource(QUrl.fromLocalFile(file))
            self.music_player.setPosition(0)
            if self.music_player.isSeekable():
                self.music_player.setPosition(int(seek_point*1000.0))
            else:
                logging.warning("OSC Seek and Play Sound: Audio file does not support seeking")
            self.music_player.play()

        else:
            logging.warning(f"OSC Seek and Play Sound: sound matching {tags} not found")


    # Responds to an OSC command to play a random audio file from the query set
    @Slot(str)
    def onOSCServerStingerAction(self, tags):
        # Zero length tag list will stop play
        if len(tags) == 0:
            self.music_player.stop()
            return

        foundSounds = self.media_file_database.search_sounds(tags, True)
        if len(foundSounds) > 0:

            # Use QRandomGenerator to get a random index from 0 (inclusive) to list_length (exclusive)
            list_length = len(foundSounds)
            random_index = QRandomGenerator.global_().bounded(list_length)
            sound = foundSounds[random_index]

            soundFile = QFileInfo(sound)
            file = soundFile.absoluteFilePath()

            # Stop active fade and restore volume
            self.reset_fade_and_restore_volume()

            self.music_player.setSource(QUrl.fromLocalFile(file))
            self.music_player.setPosition(0)
            self.music_player.play()

        else:
            logging.warning(f"OSC Play Stinger: sound matching {tags} not found")

    # Initiates a fade out of the currently playing sound over the specified time (in seconds).
    @Slot(float)
    def onOSCServerFadeAction(self, fade_time_s: float):
        # 1. Sanity Checks
        if self.music_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            return

        self.is_queue_mode = False # Requesting a fade implies the player should not advance if playing a queue

        # 2. Setup Animation
        fade_duration_ms = max(100, int(fade_time_s * 1000))
        start_vol = self.music_player.audioOutput().volume()

        # Stop any current fade to prevent conflicts
        self._fade_animation.stop()

        self._fade_animation.setDuration(fade_duration_ms)
        self._fade_animation.setStartValue(start_vol)
        self._fade_animation.setEndValue(0.0)

        # 3. Choose a Natural Curve
        # OutQuad or OutCubic sounds better than linear for volume fades
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._fade_animation.start()
        logging.debug(f"OSC Fade started: {start_vol} -> 0.0 over {fade_duration_ms}ms")

    @Slot(object)
    def _handle_fade_step(self, value):
        """Called automatically by the animation on every frame"""
        self.music_player.audioOutput().setVolume(value)

    @Slot()
    def _finalize_music_stop(self):
        """Called when the animation finishes reaching 0.0"""
        self.music_player.stop()
        # Optional: Reset volume to a default for the next track
        vol = self.ui.soundVolumeSL.value() / self.ui.soundVolumeSL.maximum()
        self.music_player.audioOutput().setVolume(vol)
        logging.debug("Music fade complete. Player stopped.")

    # Responds to an OSC command to play an audio file
    @Slot(str)
    def onOSCServerSFXPlayAction(self, tags: str):
        if not tags.strip():
            logging.warning("OSC Play Sound Effect: sound tags missing")
            return

        # Query using the sfx_only flag to simulate the UI checkbox behavior
        found_sounds = self.media_file_database.search_sounds(tags, match_all=True, sfx_only=True)
        if not found_sounds:
            logging.warning(f"OSC Play Sound Effect: SFX sound matching '{tags}' not found")
            return

        file_path = QFileInfo(found_sounds[0]).canonicalFilePath()

        sound = QSoundEffect(self)
        sound.setSource(QUrl.fromLocalFile(file_path))

        max_vol = max(1, self.ui.soundFXVolumeHS.maximum())
        sound.setVolume(self.ui.soundFXVolumeHS.value() / max_vol)

        self.active_sound_effects.append(sound)
        sound.playingChanged.connect(self._handle_soundfx_state_change)
        sound.play()

        logging.debug(f"OSC Play Sound Effect initiated play: {QFileInfo(file_path).fileName()}")

    # Called when the OSC server receives the /sfx/stop_all command.
    @Slot()
    def onOSCServerSFXStopAllAction(self):
        logger.debug("Triggering global stop for all active sound effects.")
        # Stop all soundfx regardless of what triggered them
        self.stop_all_sfx()

    # Triggers deletion of the QSoundEffect object when playback finishes.
    @Slot()
    def _handle_soundfx_state_change(self):
        sfx = self.sender()
        if isinstance(sfx, QSoundEffect) and not sfx.isPlaying():
            if sfx in self.active_sound_effects:
                self.active_sound_effects.remove(sfx)
            sfx.deleteLater()

    # Play a sound which can be triggered form a button or double clicking elements in a list.
    # Handle starting sound effects when in SFX Mode.
    @Slot()
    @Slot(QModelIndex)
    @Slot(QListWidgetItem)
    def sound_play(self, target: QModelIndex | QListWidgetItem | None = None):
        # Resume paused main track if SFX checkbox is NOT active
        if not self.ui.soundSearchSFXCB.isChecked():
            if self.music_player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                self.music_player.play()
                return

        file_path = None

        # 1. From QListWidget (Queue double-click)
        if isinstance(target, QListWidgetItem):
            file_info = target.data(Qt.ItemDataRole.UserRole)
            file_path = file_info.absoluteFilePath() if isinstance(file_info, QFileInfo) else file_info

        # 2. From QListView (Search results double-click)
        elif isinstance(target, QModelIndex) and target.isValid():
            file_path = target.data(Qt.ItemDataRole.UserRole)

        # 3. Fallback for QPushButton click (reads active selection from LV or Queue)
        else:
            idx = self.ui.soundSearchResultsLV.currentIndex()
            if idx.isValid():
                file_path = idx.data(Qt.ItemDataRole.UserRole)
            elif self.ui.soundQueueLW.currentItem():
                item = self.ui.soundQueueLW.currentItem()
                file_info = item.data(Qt.ItemDataRole.UserRole)
                file_path = file_info.absoluteFilePath() if isinstance(file_info, QFileInfo) else file_info

        if not file_path or not QFileInfo.exists(file_path):
            return

        # SFX Mode Branch: Spawns concurrent, overlapping QSoundEffect instance
        if self.ui.soundSearchSFXCB.isChecked():
            sound = QSoundEffect(self)
            sound.setSource(QUrl.fromLocalFile(file_path))

            max_vol = max(1, self.ui.soundFXVolumeHS.maximum())
            sound.setVolume(self.ui.soundFXVolumeHS.value() / max_vol)

            self.active_sound_effects.append(sound)
            sound.playingChanged.connect(self._handle_soundfx_state_change)
            sound.play()

        # Standard Track Mode Branch: Single-source QMediaPlayer
        else:
            self.is_queue_mode = False
            self.reset_fade_and_restore_volume()

            self.music_player.setSource(QUrl.fromLocalFile(file_path))
            self.music_player.setPosition(0)
            self.music_player.play()
            self.ui.soundFileNameLBL.setText(QFileInfo(file_path).completeBaseName())

    @Slot()
    def music_fade(self):
        fade_time = float(self.ui.fadeTimeSB.value())
        self.onOSCServerFadeAction(fade_time)

    # Provide a single loop control for all media player use cases, visable at all time on the mini player
    @Slot()
    def loop_media(self):
        if self.ui.loopPlayerPB.isChecked():
            self.music_player.setLoops(QMediaPlayer.Infinite)
        else:
            self.music_player.setLoops(QMediaPlayer.Once)
            if self.music_player.isPlaying():
                self.music_player.stop()

    @Slot()
    def sound_move_up(self):
        sound_row = self.ui.soundQueueLW.currentRow()
        if sound_row < 0:
            return
        sound = self.ui.soundQueueLW.takeItem(sound_row)
        self.ui.soundQueueLW.insertItem(sound_row-1,sound)
        self.ui.soundQueueLW.setCurrentRow(sound_row-1)

    @Slot()
    def sound_move_down(self):
        sound_row = self.ui.soundQueueLW.currentRow()
        if sound_row < 0:
            return
        sound = self.ui.soundQueueLW.takeItem(sound_row)
        self.ui.soundQueueLW.insertItem(sound_row+1,sound)
        self.ui.soundQueueLW.setCurrentRow(sound_row+1)

    @Slot()
    def sound_add_to_list(self):
        current_index = self.ui.soundSearchResultsLV.selectionModel().currentIndex()
        if not current_index.isValid():
            return

        # Extract path string from model and normalize to QFileInfo
        file_path = current_index.data(Qt.UserRole)
        if not file_path:
            return

        file_info = QFileInfo(file_path)

        # Construct and style item for the queue (QListWidget)
        item = QListWidgetItem(file_info.fileName(), self.ui.soundQueueLW)
        item.setData(Qt.UserRole, file_info)

        font = item.font()
        font.setPointSize(12)
        item.setFont(font)

    @Slot()
    def sound_remove_from_list(self):
        current_row = self.ui.soundQueueLW.currentRow()
        if current_row != -1:
            # Using _ signals to the linter that the return value is intentionally unreferenced
            # and scheduled for garbage collection.
            _ = self.ui.soundQueueLW.takeItem(current_row)

    @Slot()
    def load_sound_queue(self):
        # 1. UI Confirmation
        if self.ui.soundQueueLW.count() > 0:
            reply = QMessageBox.question(
                self.ui, 'Replace Sounds',
                'Are you sure you want to replace the current queue?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # 2. Get File Path
        fileName, _ = QFileDialog.getOpenFileName(
            self.ui, "Load Sound Queue",
            self._settings.get_config_dir(),
            "Sound Queue Files (*.sfx *.sdq)"
        )

        if not fileName:
            return

        self.read_queue(fileName)

    @Slot()
    def save_sound_queue(self):
        fileName, _ = QFileDialog.getSaveFileName(
            self.ui, "Save Sound Queue",
            self._settings.get_config_dir(),
            "Sound Queue Files(*.sdq)"
        )

        if not fileName:
            return

        # 1. Build a standard Python dictionary
        sound_data = {}
        for i in range(self.ui.soundQueueLW.count()):
            item = self.ui.soundQueueLW.item(i)
            file_info = item.data(Qt.UserRole)
            sound_data[f"sound{i}"] = file_info.absoluteFilePath()

        # 2. Convert Python dict directly to QJsonDocument
        doc = QJsonDocument.fromVariant(sound_data)

        # 3. Safe Save
        save_file = QSaveFile(fileName)
        if save_file.open(QIODevice.WriteOnly):
            save_file.write(doc.toJson(QJsonDocument.JsonFormat.Indented))
            save_file.commit()

    @Slot()
    def save_soundFX_pallette(self):
        # 1. Get path from user
        fileName, _ = QFileDialog.getSaveFileName(
            self.ui, "Save Sound Palette",
            self._settings.get_config_dir(),
            "Sound Palette Files (*.sfx)"
        )

        if not fileName:
            return

        # 2. Build a native Python dictionary using comprehension
        # This maps "sound0": "/path/to/file.wav", etc.
        sound_data = {
            f"sound{i}": self.ui.soundQueueLW.item(i).data(Qt.UserRole).absoluteFilePath()
            for i in range(self.ui.soundQueueLW.count())
        }

        # 3. Convert dict to QJsonDocument via fromVariant
        doc = QJsonDocument.fromVariant(sound_data)

        # 4. Atomic Save using QSaveFile
        save_file = QSaveFile(fileName)
        if save_file.open(QIODevice.WriteOnly):
            # Write indented bytes (UTF-8)
            save_file.write(doc.toJson(QJsonDocument.JsonFormat.Indented))

            if save_file.commit():
                logger.debug(f"Successfully saved palette: {fileName}")
            else:
                logger.error(f"Failed to commit sound pallette: {fileName}")
        else:
            logger.error(f"Could not save sound pallette: {fileName}: {save_file.errorString()}")

        # 5. Refresh the UI dropdown
        self.load_sound_pallettes()

    @Slot()
    def clear_sound_queue(self):
        reply = QMessageBox.question(self.ui, 'Clear Sounds', 'Are you sure you want clear all sounds?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.soundQueueLW.clear()

    # Sound Palletes
    @Slot()
    def load_sound_pallettes(self):
        self.palletteSelect.clear()
        palletteIter = QDirIterator(self._settings.get_config_dir(),{"*.sfx"})
        while palletteIter.hasNext():
            palletteFileInfo = palletteIter.nextFileInfo()
            palletteFileName = palletteFileInfo.completeBaseName()
            self.palletteSelect.addItem(palletteFileName, palletteFileInfo)

        if self.palletteSelect.count() > 0:
            self.load_sound_effects(0)

    @Slot(int)
    def load_sound_effects(self, index):
        """
        Loads a sound palette (JSON) and maps paths to the SFX button grid.
        """
        button_idx = 0
        total_buttons = len(self.sfx_buttons)

        # 1. Validation: Only proceed if there is a valid selection
        if self.palletteSelect.count() > 0 and index >= 0:
            palletteFileInfo = self.palletteSelect.itemData(index)

            # 2. Open and Read using QFile
            file = QFile(palletteFileInfo.absoluteFilePath())
            if file.open(QIODevice.ReadOnly):
                raw_data = file.readAll()
                file.close()

                # 3. Parse JSON to a native Python dictionary
                doc = QJsonDocument.fromJson(raw_data)
                sound_data = doc.toVariant() # Returns a native Python dict

                if isinstance(sound_data, dict):
                    # 4. Sort keys to ensure sound0, sound1... sound10 order
                    # Python dicts are ordered, but sorted() guarantees the grid mapping
                    for key in sorted(sound_data.keys(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)):
                        if button_idx < total_buttons:
                            path = sound_data[key]
                            file_info = QFileInfo(path)

                            # 5. Load if it's a valid WAV file, otherwise disable
                            if file_info.exists():
                                self.sfx_buttons[button_idx].loadSoundEffect(file_info)
                            else:
                                self.sfx_buttons[button_idx].disable()

                            button_idx += 1

        # 6. Safety: Disable any remaining buttons in the grid not defined in the JSON
        for i in range(button_idx, total_buttons):
            self.sfx_buttons[i].disable()

    @Slot(int)
    def set_fx_volume(self, value):
        sliderMax = self.ui.soundFXVolumeHS.maximum()
        for sound in self.sfx_buttons:
            sound.set_fx_volume(value/sliderMax)

    # Fades out all sounds currently playing in the palette and any OSC triggered soundfx
    @Slot()
    def stop_all_sfx(self):
        for sfx in self.sfx_buttons:
            sfx.fadeOut(duration=500) # Faster fade for panic situations

        # Destroy sounds create by SFX Mode on the music search or via OSC. Copy list to safely iterate while items clear
        for sfx in list(self.active_sound_effects):
            sfx.stop()
            sfx.deleteLater()

        self.active_sound_effects.clear()

    # Mini Music Player On the Main Control area monitors the currrently play song
    # Calculates time remaining and updates the progress bar.
    # param position: The current playback position in milliseconds.
    @Slot(int)
    def _update_player_duration(self, duration: int):
        self.ui.musicPlayerProgress.setRange(0, duration)

    @Slot(int)
    def _update_player_progress(self, position: int):
        self.ui.musicPlayerProgress.setValue(position)

        duration = self.music_player.duration()
        remaining_ms = max(0, duration - position)

        seconds = (remaining_ms // 1000) % 60
        minutes = (remaining_ms // (1000 * 60)) % 60

        # Format as negative remaining time (e.g., -01:45)
        time_str = f"{minutes:02d}:{seconds:02d}"
        self.ui.musicPlayerProgress.setFormat(time_str)

    # Reads standard metadata (Title, Artist) from QMediaPlayer and updates the UI labels.
    # Uses file name as a fallback if metadata is missing.
    # Assuming you are using PySide6 (Qt 6)

    # Reads metadata from the QMediaPlayer and updates the Title and Artist labels."""
    @Slot()
    def update_metadata_display(self):
        # Get the dedicated metadata object from the player first.
        # The metaData(key) method must be called on this object, not the player itself.
        metadata_object = self.music_player.metaData()

        # Get Title
        title = metadata_object.stringValue(QMediaMetaData.Key.Title)

        if not title:
            # Fallback: Use the file name without extension
            url = self.music_player.source()
            if not url.isEmpty():
                file_name = QFileInfo(url.url()).fileName()
                title = QFileInfo(file_name).baseName()
            else:
                title = "Unknown Title"

        self.ui.mediaTitleLBL.setText(title)

        # Get Artist
        artist = metadata_object.stringValue(QMediaMetaData.Key.ContributingArtist)

        if not artist:
            # Priority 2: Check for AlbumArtist tag
            artist = metadata_object.stringValue(QMediaMetaData.AlbumArtist)

        if not artist:
            # Priority 3: Check for Author tag
            artist = metadata_object.stringValue(QMediaMetaData.Author)

        if not artist:
            # Final Fallback
            artist = "Unknown Artist"

        self.ui.artistNameLBL.setText(artist)

        logging.debug(f"Media Metadata Updated: Title='{title}', Artist='{artist}'")

    # Image text Overlay functions
    @Slot()
    def pick_overlay_text_color(self):
        color_selected = QColorDialog.getColor(parent=self.ui, title='Pick the overlay text color')
        self._settings.save_custom_colors()
        if color_selected is not None:
            self._overlay_color = color_selected
            self.ui.mediaSearchtOverlayColorPB.setStyleSheet(utilities.style_sheet(self._overlay_color))
            self.ui.mediaSearchPreviewLBL.set_text_overlay(
                background_path = self.ui.mediaFileNameLBL.text(),
                overlay_text = self.ui.mediaSearchOverlayLE.text(),
                font = self.ui.mediaSearchtOverlayFB.currentFont(),
                scale = self.ui.mediaSearchtOverlayColorSLD.value(),
                color = self._overlay_color)

    @Slot(str)
    def show_overlay_text(self, overlay_text):
        self.ui.mediaSearchPreviewLBL.set_text_overlay(
            background_path = self.ui.mediaFileNameLBL.text(),
            overlay_text = overlay_text,
            font = self.ui.mediaSearchtOverlayFB.currentFont(),
            scale = self.ui.mediaSearchtOverlayColorSLD.value(),
            color = self._overlay_color)

    @Slot(str)
    def scale_overlay_text(self, value):
        self.ui.mediaSearchPreviewLBL.set_text_overlay(
            background_path = self.ui.mediaFileNameLBL.text(),
            overlay_text = self.ui.mediaSearchOverlayLE.text(),
            font = self.ui.mediaSearchtOverlayFB.currentFont(),
            scale = value,
            color = self._overlay_color)

    @Slot(str)
    def style_overlay_text(self, font):
        self.ui.mediaSearchPreviewLBL.set_text_overlay(
            background_path = self.ui.mediaFileNameLBL.text(),
            overlay_text = self.ui.mediaSearchOverlayLE.text(),
            font = font,
            scale = self.ui.mediaSearchtOverlayColorSLD.value(),
            color = self._overlay_color)

    @Slot(str)
    def clear_image(self, value):
        self.ui.mediaSearchOverlayLE.clear()
        self.ui.mediaFileNameLBL.clear()
        self.ui.mediaSearchPreviewLBL.blackout()
        self.ui.mediaSearchResultsLV.clearSelection()
        self.ui.mediaSearchResultsLV.setCurrentIndex(QModelIndex())

    # Model based slots
    @Slot(str)
    def on_search_text_changed(self, text: str):
        self.sound_proxy.set_filter(text, match_all=self.allsoundTagsCB.isChecked())

    @Slot()
    def _on_media_search_changed(self):
        query = self.ui.mediaSearchTagsLE.text()
        match_all = self.ui.allMediaTagsCB.isChecked()
        self.media_proxy.set_filter(query, match_all)

    @Slot()
    def fire_top_result_or_focus(self, view_type: str = "media"):
        """Focuses the list view or fires the top result on Enter press."""
        # Match the actual QListView widget names from Qt Designer
        if view_type == "media":
            view = self.ui.mediaSearchResultsLV
        else:
            view = self.ui.soundSearchResultsLV

        model = view.model()
        if model and model.rowCount() > 0:
            # Select and set focus to the first item in the filtered view
            first_index = model.index(0, 0)
            view.setCurrentIndex(first_index)
            view.setFocus()

    @Slot()
    def _on_sound_search_changed(self):
        query = self.ui.soundSearchTagsLE.text()
        match_all = self.ui.allMediaTagsCB.isChecked()
        self.sound_proxy.set_filter(query, match_all)

# In-place Fisher-Yates shuffle using QRandomGenerator. Works on any Python list or mutable sequence.
class QtListShuffler:
    @staticmethod
    def shuffle(items_list):
        n = len(items_list)
        # Use the high-quality global generator
        rng = QRandomGenerator.global_()

        for i in range(n - 1, 0, -1):
            # Pick a random index j such that 0 <= j <= i
            # bounded(high) returns a value in [0, high)
            j = rng.bounded(i + 1)

            # Swap elements
            items_list[i], items_list[j] = items_list[j], items_list[i]
