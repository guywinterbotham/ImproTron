# media_features.py
import logging
from PySide6.QtCore import (Qt, QObject, Slot, Signal, QFileInfo, QDirIterator, QUrl, QRandomGenerator, QVariantAnimation,
                                QEasingCurve, QFile, QJsonDocument, QSaveFile, QIODevice, QDir)
from PySide6.QtGui import QImageReader, QPixmap, QMovie
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QStyle, QPushButton, QListWidgetItem
from PySide6.QtMultimedia import QMediaPlayer, QSoundEffect, QAudioOutput, QMediaMetaData, QMediaFormat
from Improtronics import SoundFX
from MediaFileDatabase import MediaFileDatabase

logger = logging.getLogger(__name__)

# Module to encapsulate image and media search along with the media database management
class MediaFeatures(QObject):
    mainMediaShow = Signal(str)    # Custom signal that decouples the media display from controlboard
    auxMediaShow  = Signal(str)    # Custom signal that decouples the media display from controlboard
    stopAllSFX    = Signal()       # Custom signal that signals all sound to stop

    def __init__(self, ui, settings, media_model):
        super(MediaFeatures, self).__init__()

        self.ui = ui
        self.active_sound_effects = []
        self._settings = settings
        self.media_model = media_model

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
        self.fade_anim = QVariantAnimation(self)
        self.fade_anim.valueChanged.connect(self._handle_fade_step)
        self.fade_anim.finished.connect(self._finalize_music_stop)

        # QMovies for displaying GIF previews. Avoids memory leaks by keeping them around
        self.search_preview_movie = QMovie()
        self.search_preview_movie.setSpeed(100)

        # Playback current track playback state
        self.current_track_index = -1
        self.playback_queue = []
        self.is_queue_mode = False  # The gatekeeper flag, signals if a queue or single track is playing.

        # In memory database configuration
        self.media_file_database = MediaFileDatabase()

        # Initial Image Indexing
        media_count = self.media_file_database.index_media(self._settings.get_media_directory())
        self.ui.mediaFilesCountLBL.setText(str(media_count))

        # Initial Sound Indexing
        sound_count = self.media_file_database.index_sounds(self._settings.get_sound_directory())
        self.ui.soundFilesCountLBL.setText(str(sound_count))

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
        self.ui.soundRemoveFromListPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowBack))

        # Sound Pallettes
        self.palletteSelect = self.ui.soundPalettesCB
        self.load_sound_pallettes()

        self.connect_slots()

    # Set up audio visual connections
    def connect_slots(self):
        # Image Search Connections
        self.ui.searchMediaPB.clicked.connect(self.search_media)
        self.ui.mediaSearchTagsLE.returnPressed.connect(self.search_media)
        self.ui.mediaSearchResultsLW.itemClicked.connect(self.preview_selected_media)
        self.ui.setMediaLibraryPB.clicked.connect(self.set_media_library)

        self.ui.mediaSearchResultsLW.itemDoubleClicked.connect(self.show_media_preview_main)
        self.ui.searchToMainShowPB.clicked.connect(self.search_to_main_show)
        self.ui.searchToAuxShowPB.clicked.connect(self.search_to_aux_show)

        # Sound Search Connections
        self.ui.searchSoundsPB.clicked.connect(self.search_sounds)
        self.ui.soundSearchTagsLE.returnPressed.connect(self.search_sounds)
        self.ui.setSoundLibraryPB.clicked.connect(self.set_sound_library)

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
        self.music_player.positionChanged.connect(self.update_time_remaining)
        self.music_player.metaDataChanged.connect(self.update_metadata_display)

        # Connect error signal
        self.music_player.errorOccurred.connect(self.music_player_handle_error)

        # Sound Palletes
        self.palletteSelect.currentIndexChanged.connect(self.load_sound_effects)
# #### connections

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

    # Used when a a specifc asset is need such as a logo
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
        # 1. Clear current results and preview labels
        self.ui.mediaSearchResultsLW.clear()
        self.ui.mediaSearchPreviewLBL.clear()
        self.ui.mediaFileNameLBL.clear()

        # 2. Query the database
        foundMedia = self.media_file_database.search_media(
            self.ui.mediaSearchTagsLE.text(),
            self.ui.allMediaTagsCB.isChecked()
        )

        if len(foundMedia) > 0:
            for media_path in foundMedia:
                file_info = QFileInfo(media_path)

                # 3. Create a standard QListWidgetItem
                # Displays the filename (e.g., "intro_video.mp4")
                item = QListWidgetItem(file_info.fileName(), self.ui.mediaSearchResultsLW)

                # 4. Store the QFileInfo in UserRole for the previewer to use
                item.setData(Qt.UserRole, file_info)

                # 5. Apply the standard UI font styling
                font = item.font()
                font.setPointSize(12)
                item.setFont(font)
        else:
            QMessageBox.information(self.ui, 'No Search Results', 'No media with those tags found.')

    # Music Player Controls
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
        self.music_player.stop()

    def music_player_handle_error(self, error, error_string):
        # Log the error
        logger.error(f"Music Player Error: {error} - {error_string}")

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

            self.music_player.setSource(QUrl.fromLocalFile(song_path))
            # Match the UI volume
            vol = self.ui.soundVolumeSL.value() / self.ui.soundVolumeSL.maximum()
            self.music_audio.setVolume(vol)
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

    @Slot(QListWidgetItem)
    def preview_selected_media(self, item):
        # 1. Extract the QFileInfo from UserRole
        media_info = item.data(Qt.UserRole)
        if not media_info:
            return

        # 2. Get the absolute path for convenience
        file_path = media_info.absoluteFilePath()
        self.ui.mediaFileNameLBL.setText(file_path)

        # 3. Handle Preview Logic
        self.search_preview_movie.stop()

        if media_info.suffix().lower() == 'gif':
            self.search_preview_movie.setFileName(file_path)
            if self.search_preview_movie.isValid():
                # Scale the movie to fit the preview label
                self.search_preview_movie.setScaledSize(self.ui.mediaSearchPreviewLBL.size())
                self.ui.mediaSearchPreviewLBL.setMovie(self.search_preview_movie)
                self.search_preview_movie.start()
        else:
            # Use QImageReader for static images
            reader = QImageReader(file_path)
            reader.setAutoTransform(True)
            newImage = reader.read()

            if newImage.isNull():
                logger.warning(f"Media search preview: Failed to read image {file_path}. QImageReader error: {reader.errorString()}")
                self.ui.mediaSearchPreviewLBL.clear()
                self.ui.mediaFileNameLBL.clear()
                return

            # 4. Scaling and Display
            if self.ui.stretchMainCB.isChecked():
                # Stretch to fill the label
                scaled_pixmap = QPixmap.fromImage(newImage.scaled(self.ui.mediaSearchPreviewLBL.size(),
                                                                  Qt.IgnoreAspectRatio,
                                                                  Qt.SmoothTransformation))
                self.ui.mediaSearchPreviewLBL.setPixmap(scaled_pixmap)
            else:
                # Scale maintaining aspect ratio
                scaled_pixmap = QPixmap.fromImage(newImage.scaled(self.ui.mediaSearchPreviewLBL.size(),
                                                                  Qt.KeepAspectRatio,
                                                                  Qt.SmoothTransformation))
                self.ui.mediaSearchPreviewLBL.setPixmap(scaled_pixmap)


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
        if self.ui.mediaSearchResultsLW.currentItem() != None:
            slide = self.ui.mediaSearchResultsLW.currentItem()
            # Get the QFileInfo object from the UserRole
            file_info = slide.data(Qt.UserRole)

            if file_info:
                # Emit the absolute path string
                self.mainMediaShow.emit(file_info.absoluteFilePath())
    @Slot()
    def search_to_aux_show(self):
        if self.ui.mediaSearchResultsLW.currentItem() != None:
            slide = self.ui.mediaSearchResultsLW.currentItem()
            # Get the QFileInfo object from the UserRole
            file_info = slide.data(Qt.UserRole)

            if file_info:
                # Emit the absolute path string
                self.auxMediaShow.emit(file_info.absoluteFilePath())
    # Sound Search Slots
    @Slot()
    def search_sounds(self):
        self.ui.soundSearchResultsLW.clear()
        foundSounds = self.media_file_database.search_sounds(self.ui.soundSearchTagsLE.text(), self.ui.allsoundTagsCB.isChecked())
        if len(foundSounds) > 0:
            for sound in foundSounds:
                        file_info = QFileInfo(sound)

                        # 1. Create a standard QListWidgetItem
                        # We display the filename to the user
                        item = QListWidgetItem(file_info.fileName(), self.ui.soundSearchResultsLW)

                        # 2. Store the QFileInfo in the UserRole
                        item.setData(Qt.UserRole, file_info)

                        # 3. Apply your consistent styling (12pt font)
                        font = item.font()
                        font.setPointSize(12)
                        item.setFont(font)
        else:
            QMessageBox.information(self.ui, 'No Search Results', 'No sounds with those tags found.')

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
            self.music_player.setSource(QUrl.fromLocalFile(file))
            self.music_player.setPosition(0)
            self.music_player.audioOutput().setVolume(1)
            self.music_player.play()

        else:
            logging.warning(f"OSC Play Sound: sound matching {tags} not found")

    # Responds to an OSC command to play an audio file
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
            self.music_player.setSource(QUrl.fromLocalFile(file))
            self.music_player.setPosition(0)
            if self.music_player.isSeekable():
                self.music_player.setPosition(int(seek_point*1000.0))
            else:
                logging.warning("OSC Seek and Play Sound: Audio file does not support seeking")
            self.music_player.audioOutput().setVolume(1)
            self.music_player.play()

        else:
            logging.warning(f"OSC Play Sound: sound matching {tags} not found")


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
            self.music_player.setSource(QUrl.fromLocalFile(file))
            self.music_player.setPosition(0)
            self.music_player.audioOutput().setVolume(1)
            self.music_player.play()

        else:
            logging.warning(f"OSC Play Sound: sound matching {tags} not found")

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
        self.fade_anim.stop()

        self.fade_anim.setDuration(fade_duration_ms)
        self.fade_anim.setStartValue(start_vol)
        self.fade_anim.setEndValue(0.0)

        # 3. Choose a Natural Curve
        # OutQuad or OutCubic sounds better than linear for volume fades
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.fade_anim.start()
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
    def onOSCServerSFXPlayAction(self, tags):
        # Zero length tag list will stop play
        if len(tags) == 0:
            self.stopAllSFX.emit()
            return

        wav_tags = "wav " + tags

        foundSounds = self.media_file_database.search_sounds(wav_tags, True)
        if len(foundSounds) > 0:
            found_sound = foundSounds[0]
            soundFile = QFileInfo(found_sound)

            # Use canonicalFilePath() for better file resolution stability
            file = soundFile.canonicalFilePath()

            # Instantiate and parent correctly
            sound = QSoundEffect(self)
            sound.setSource(QUrl.fromLocalFile(file))

            # Add to the list to prevent premature garbage collection while loading
            self.active_sound_effects.append(sound)

            # Connect the correct self-destruct signal (playingChanged)
            sound.playingChanged.connect(self._handle_soundfx_state_change)

            # Connect the global stop signal
            self.stopAllSFX.connect(sound.stop)

            # TRUST the load and initiate play
            sound.setVolume(1.0)
            sound.play()
            logging.debug("OSC Play Sound Effect initiated play.")

        else:
            logging.warning(f"OSC Play Sound Effect: sound matching {tags} not found")

    # Called when the OSC server receives the /sfx/stop_all command.
    @Slot()
    def onOSCServerSFXStopAllAction(self):
        logger.debug("Triggering global stop for all active sound effects.")
        # Stop all soundfx regardless of what triggered them
        self.stop_all_sfx()

    # Triggers deletion of the QSoundEffect object when playback finishes.
    @Slot()
    def _handle_soundfx_state_change(self):
        # Get the QSoundEffect object that emitted the signal
        sound = self.sender()

        if sound and isinstance(sound, QSoundEffect) and not sound.isPlaying():

            if sound in self.active_sound_effects:
                self.active_sound_effects.remove(sound)
                logging.debug("Sound effect removed from active_sound_effects list.")

            # 2. Then, safely destroy the object
            sound.deleteLater()
            logger.debug("QSoundEffect object deleted after playing.")
        else:
            logger.debug("SoundFX sound sender was empty or not a QSoundEffect")

    @Slot()
    def sound_play(self):
        if self.music_player.playbackState() == QMediaPlayer.PausedState:
            self.music_player.play()
            return

        self.is_queue_mode = False
        if self.ui.soundSearchResultsLW.currentItem() != None:
            current = self.ui.soundSearchResultsLW.currentItem()
            if current:
                file_info = current.data(Qt.UserRole)
                if file_info:
                    path = file_info.absoluteFilePath()
                    self.music_player.setSource(QUrl.fromLocalFile(path))
                    self.music_player.setPosition(0)
                    self.music_player.audioOutput().setVolume(self.ui.soundVolumeSL.value()/self.ui.soundVolumeSL.maximum())
                    self.music_player.play()

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
        if self.ui.soundSearchResultsLW.currentItem() != None:
            sound = self.ui.soundSearchResultsLW.takeItem(self.ui.soundSearchResultsLW.currentRow())
            self.ui.soundQueueLW.addItem(sound)

    @Slot()
    def sound_remove_from_list(self):
        if self.ui.soundQueueLW.currentItem() != None:
            sound = self.ui.soundQueueLW.takeItem(self.ui.soundQueueLW.currentRow())
            self.ui.soundSearchResultsLW.addItem(sound)

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

        self.stopAllSFX.emit()

    # Mini Music Player On the Main Control area monitors the currrently play song
    #Calculates time remaining and updates the timeRemainingLBL.
    #param position_ms: The current playback position in milliseconds.
    @Slot(int)
    def update_time_remaining(self, position_ms: int):

        # Get total duration (in milliseconds)
        duration_ms = self.music_player.duration()

        if duration_ms <= 0 or not self.music_player.isPlaying():
            # Cannot calculate time remaining if duration is unknown
            self.ui.timeRemainingLBL.setText("--:--")
            return

        # Calculate remaining time
        remaining_ms = duration_ms - position_ms

        # Ensure remaining time is not negative
        if remaining_ms < 0:
            remaining_ms = 0

        # Convert milliseconds to MM:SS format using Qt functionality

        # Total seconds remaining
        total_seconds = remaining_ms // 1000

        minutes = total_seconds // 60
        seconds = total_seconds % 60

        # Use f-string formatting to ensure two digits (00:00)
        time_str = f"{minutes:02d}:{seconds:02d}"

        self.ui.timeRemainingLBL.setText(time_str)

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
