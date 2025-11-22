# media_features.py
import json
import logging
from PySide6.QtCore import QObject, Slot, Signal, QFileInfo, QDirIterator, QUrl, QRandomGenerator, QTimer
from PySide6.QtGui import QImageReader, QPixmap, QMovie
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QStyle, QPushButton
from PySide6.QtMultimedia import QMediaPlayer, QSoundEffect
from Improtronics import SoundFX, SlideWidget
from MediaFileDatabase import MediaFileDatabase

logger = logging.getLogger(__name__)

# Module to encapsulate image and media search along with the media database management
class MediaFeatures(QObject):
    mainMediaShow = Signal(str)    # Custom signal that decouples the media display from controlboard
    auxMediaShow  = Signal(str)    # Custom signal that decouples the media display from controlboard
    stopAllSFX    = Signal()    # Custom signal that signals all sound to stop

    def __init__(self, ui, settings, media_model, media_player):
        super(MediaFeatures, self).__init__()

        self.ui = ui
        self.active_sound_effects = []
        self._settings = settings
        self.media_model = media_model
        self.media_player = media_player

        # Variables for fade control
        self.fade_timer = QTimer(self)
        self.fade_step_duration_ms = 50.0       # How often the timer fires (50ms)
        self.volume_per_step = 0.0              # Calculated when fade starts
        self.original_volume = 1.0            # Store original volume for step calculation

        # QMovies for displaying GIF previews. Avoids memory leaks by keeping them around
        self.search_preview_movie = QMovie()
        self.search_preview_movie.setSpeed(100)

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

        # Don't assume the buttons are in the same order in the grid as they are numbered
        # Look for each button by its object name. The number of buttons can be derived
        # from the grid though
        for button in range(self.ui.soundFXGrid.count()):
            sfx_button = self.ui.findChild(QPushButton, "soundFXPB" +str(button+1))
            _soundFX = SoundFX(sfx_button)
            _soundFX.set_fx_volume(_volume)
            self.sfx_buttons.append(_soundFX)

        # Use standard icons
        self.ui.soundPlayPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.soundPausePB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.soundStopPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaStop))
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
        self.ui.soundPausePB.clicked.connect(self.sound_pause)
        self.ui.soundStopPB.clicked.connect(self.sound_stop)

        self.ui.loadSoundQueuePB.clicked.connect(self.load_sound_queue)
        self.ui.saveSoundQueuePB.clicked.connect(self.save_sound_queue)
        self.ui.saveSoundFXPallettePB.clicked.connect(self.save_soundFX_pallette)
        self.ui.clearSoundQueuePB.clicked.connect(self.clear_sound_queue)
        self.ui.soundFXVolumeHS.valueChanged.connect(self.set_fx_volume)

        self.ui.soundMoveUpPB.clicked.connect(self.sound_move_up)
        self.ui.soundMoveDownPB.clicked.connect(self.sound_move_down)
        self.ui.soundAddToListPB.clicked.connect(self.sound_add_to_list)
        self.ui.soundRemoveFromListPB.clicked.connect(self.sound_remove_from_list)

        # Sound Palletes
        self.palletteSelect.currentIndexChanged.connect(self.load_sound_effects)

        # Connect the timer's timeout signal to the fade handler
        self.fade_timer.timeout.connect(self._handle_fade_step)
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

    # Reset the tree view of media files
    def reset_media_view(self, directory):
        self.image_tree_view = self.ui.slideShowFilesTreeView
        self.image_tree_view.setModel(self.media_model)
        self.image_tree_view.setRootIndex(self.media_model.index(directory))
        for i in range(1, self.media_model.columnCount()):
            self.image_tree_view.header().hideSection(i)
        self.image_tree_view.setHeaderHidden(True)

    # Media Management Slots
    @Slot()
    def search_media(self):
        self.ui.mediaSearchResultsLW.clear()
        self.ui.mediaSearchPreviewLBL.clear()
        self.ui.mediaFileNameLBL.clear()
        foundMedia = self.media_file_database.search_media(self.ui.mediaSearchTagsLE.text(), self.ui.allMediaTagsCB.isChecked())
        if len(foundMedia) > 0:
            for media in foundMedia:
                SlideWidget(QFileInfo(media), self.ui.mediaSearchResultsLW)
        else:
            QMessageBox.information(self.ui, 'No Search Results', 'No media with those tags found.')

    # Responds to an OSC command to show media on a monitor
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

    @Slot(SlideWidget)
    def preview_selected_media(self, slide):
        media_info = slide.fileInfo()
        self.ui.mediaFileNameLBL.setText(slide.imagePath())
        self.search_preview_movie.stop()
        if media_info.suffix().lower() == 'gif':
            self.search_preview_movie.setFileName(slide.imagePath())
            if self.search_preview_movie.isValid():
                self.search_preview_movie.setScaledSize(self.ui.mediaSearchPreviewLBL.size())
                self.ui.mediaSearchPreviewLBL.setMovie(self.search_preview_movie)
                self.search_preview_movie.start()
        else:
            reader = QImageReader(slide.imagePath())
            reader.setAutoTransform(True)
            newImage = reader.read()
            if newImage.isNull():
                logger.warning(f"Media search preview: Failed to read image {slide.imagePath()}. QImageReader error: {reader.errorString()}")
                self.ui.mediaSearchPreviewLBL.clear() # Clear the preview label
                self.ui.mediaFileNameLBL.clear() # Clear the filename label
                return
            # This 'if newImage:' is now redundant due to the isNull check above, but kept for safety / original structure.
            # Realistically, if newImage is Null, the return above would have exited.
            if newImage: 
                if self.ui.stretchMainCB.isChecked():
                    self.ui.mediaSearchPreviewLBL.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.mediaSearchPreviewLBL.size())))
                else:
                    self.ui.mediaSearchPreviewLBL.setPixmap(QPixmap.fromImage(newImage.scaledToHeight(self.ui.mediaSearchPreviewLBL.size().height())))

    @Slot(SlideWidget)
    def show_media_preview_main(self, slide):
        self.mainMediaShow.emit(slide.imagePath())

    @Slot()
    def search_to_main_show(self):
        if self.ui.mediaSearchResultsLW.currentItem() != None:
            slide = self.ui.mediaSearchResultsLW.currentItem()
            self.mainMediaShow.emit(slide.imagePath())

    @Slot()
    def search_to_aux_show(self):
        if self.ui.mediaSearchResultsLW.currentItem() != None:
            slide = self.ui.mediaSearchResultsLW.currentItem()
            self.auxMediaShow.emit(slide.imagePath())

    # Sound Search Slots
    @Slot()
    def search_sounds(self):
        self.ui.soundSearchResultsLW.clear()
        foundSounds = self.media_file_database.search_sounds(self.ui.soundSearchTagsLE.text(), self.ui.allsoundTagsCB.isChecked())
        if len(foundSounds) > 0:
            for sound in foundSounds:
                SlideWidget(QFileInfo(sound), self.ui.soundSearchResultsLW)
        else:
            QMessageBox.information(self.ui, 'No Search Results', 'No sounds with those tags found.')


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
    @Slot(float, str)
    def onOSCServerSoundAction(self, tags):
        # Zero length tag list will stop play
        if len(tags) == 0:
            self.media_player.stop()
            return

        foundSounds = self.media_file_database.search_sounds(tags, True)
        if len(foundSounds) > 0:
            sound = foundSounds[0]
            soundFile = QFileInfo(sound)
            file = soundFile.absoluteFilePath()
            self.media_player.setSource(QUrl.fromLocalFile(file))
            self.media_player.setPosition(0)
            self.media_player.audioOutput().setVolume(1)
            self.media_player.play()

        else:
            logging.warning(f"OSC Play Sound: sound matching {tags} not found")

    # Responds to an OSC command to play an audio file
    @Slot(float, str)
    def onOSCServerSeekAction(self, seek_point, tags):
        # Zero length tag list will stop play
        if len(tags) == 0:
            self.media_player.stop()
            return

        foundSounds = self.media_file_database.search_sounds(tags, True)
        if len(foundSounds) > 0:
            sound = foundSounds[0]
            soundFile = QFileInfo(sound)
            file = soundFile.absoluteFilePath()
            self.media_player.setSource(QUrl.fromLocalFile(file))
            self.media_player.setPosition(0)
            if self.media_player.isSeekable():
                self.media_player.setPosition(int(seek_point*1000.0))
            else:
                logging.warning(f"OSC Seek and Play Sound: Audio file does not support seeking")
            self.media_player.audioOutput().setVolume(1)
            self.media_player.play()

        else:
            logging.warning(f"OSC Play Sound: sound matching {tags} not found")


    # Responds to an OSC command to play a random audio file from the query set
    @Slot(str)
    def onOSCServerStingerAction(self, tags):
        # Zero length tag list will stop play
        if len(tags) == 0:
            self.media_player.stop()
            return

        foundSounds = self.media_file_database.search_sounds(tags, True)
        if len(foundSounds) > 0:

            # Use QRandomGenerator to get a random index from 0 (inclusive) to list_length (exclusive)
            list_length = len(foundSounds)
            random_index = QRandomGenerator.global_().bounded(list_length)
            sound = foundSounds[random_index]

            soundFile = QFileInfo(sound)
            file = soundFile.absoluteFilePath()
            self.media_player.setSource(QUrl.fromLocalFile(file))
            self.media_player.setPosition(0)
            self.media_player.audioOutput().setVolume(1)
            self.media_player.play()

        else:
            logging.warning(f"OSC Play Sound: sound matching {tags} not found")

    # Initiates a fade out of the currently playing sound over the specified time (in seconds).
    @Slot(float) # The OSC command provides a single float argument (fade time in seconds)
    def onOSCServerFadeAction(self, fade_time_s: float):

        # Ensure a sound is actually playing
        if self.media_player.playbackState() != QMediaPlayer.PlayingState:
            logging.info("OSC Server Fade requested, but QMediaPlayer is not playing.")
            return

        # Ensure fade time is positive and convert to milliseconds
        fade_duration_ms = max(100, int(fade_time_s * 1000)) # Use a minimum of 100ms

        # Store current state and calculate the fade step
        self.original_volume = self.media_player.audioOutput().volume()

        if self.original_volume <= 0:
            logging.info("Volume already at zero. Stopping playback.")
            self.media_player.stop()
            return

        # Calculate the number of steps required
        num_steps = fade_duration_ms / self.fade_step_duration_ms

        # Avoid division by zero if fade_duration_ms is somehow smaller than fade_step_duration_ms
        if num_steps < 1:
            num_steps = 1

        # Calculate how much volume to reduce per step
        self.volume_per_step = self.original_volume / num_steps

        logging.debug(f"Starting fade from {self.original_volume} over {fade_duration_ms}ms ({fade_time_s}s).")

        # Start the timer
        self.fade_timer.start(self.fade_step_duration_ms)

    # Executes one step of the volume fade-out.
    @Slot()
    def _handle_fade_step(self):
        current_volume = self.media_player.audioOutput().volume()

        if current_volume <= self.volume_per_step:
            # Reached the end: set to zero, stop player, and stop timer
            self.media_player.audioOutput().setVolume(0.0)
            self.media_player.stop()
            self.fade_timer.stop()
            logging.debug("Fade complete and playback stopped.")

        else:
            # Decrease volume and continue
            new_volume = current_volume - self.volume_per_step
            self.media_player.audioOutput().setVolume(new_volume)

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

            # Add to the list to prevent premature GC while loading
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
        # Emit the signal, which triggers the .stop() method on ALL connected QSoundEffect objects
        self.stopAllSFX.emit()

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
        if self.media_player.playbackState() == QMediaPlayer.PausedState:
            self.media_player.play()
            return

        if self.ui.soundSearchResultsLW.currentItem() != None:
            self.media_player.setSource(QUrl.fromLocalFile(self.ui.soundSearchResultsLW.currentItem().imagePath()))
            self.media_player.setPosition(0)
            self.media_player.audioOutput().setVolume(self.ui.soundVolumeSL.value()/self.ui.soundVolumeSL.maximum())
            self.media_player.play()

    @Slot()
    def sound_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PausedState:
            self.media_player.play()
            return

        if self.media_player.isPlaying():
            self.media_player.pause()

    @Slot()
    def sound_stop(self):
        self.media_player.stop()

    # Provide a single loop control for all media player use cases, visable at all time on the mini player
    @Slot()
    def loop_media(self):
        if self.ui.loopPlayerPB.isChecked():
            self.media_player.setLoops(QMediaPlayer.Infinite)
        else:
            self.media_player.setLoops(QMediaPlayer.Once)
            if self.media_player.isPlaying():
                self.media_player.stop()

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
        if self.ui.soundQueueLW.count() > 0:
            reply = QMessageBox.question(self.ui, 'Replace Sounds', 'Are you sure you want replace the current queue?',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.ui.soundQueueLW.clear()

        fileName = QFileDialog.getOpenFileName(self.ui, "Load Sound Queue",
                                self._settings.get_config_dir(),
                                "Sound Queue Files(*.sfx *.sdq)")

        # Read the JSON data from the file
        if len(fileName[0]) > 0:
            with open(fileName[0], 'r') as json_file:
                sound_data = json.load(json_file)

            for sound in sound_data.items():
                file = QFileInfo(sound[1])
                SlideWidget(file, self.ui.soundQueueLW)

    @Slot()
    def save_sound_queue(self):
        fileName = QFileDialog.getSaveFileName(self.ui, "Save Sound Queue",
                                   self._settings.get_config_dir(),
                                   "Sound Queue Files(*.sdq)")

        if len(fileName[0]) > 0:
            sound_data = {}
            for sound in range(self.ui.soundQueueLW.count()):
                soundName = "sound"+str(sound)
                sound_data[soundName] = self.ui.soundQueueLW.item(sound).imagePath()

            # Write the JSON string to a file
            with open(fileName[0], 'w', encoding='utf8') as json_file:
                json.dump(sound_data, json_file, indent=2)

    @Slot()
    def save_soundFX_pallette(self):
        fileName = QFileDialog.getSaveFileName(self.ui, "Save Sound Queue",
                                   self._settings.get_config_dir(),
                                   "Sound Queue Files(*.sfx)")

        if len(fileName[0]) > 0:
            sound_data = {}
            for sound in range(self.ui.soundQueueLW.count()):
                soundName = "sound"+str(sound)
                sound_data[soundName] = self.ui.soundQueueLW.item(sound).imagePath()

            # Write the JSON string to a file
            with open(fileName[0], 'w', encoding='utf8') as json_file:
                json.dump(sound_data, json_file, indent=2)

        # Trigger a refresh of the combo box of Palletes
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
        # During initialization, a negative index is sent. Use that as a trigger
        # to diable all buttons in the case no files exist

        buttonNumber = 0
        if self.palletteSelect.count() > 0 and index >= 0 :
            palletteFileInfo = self.palletteSelect.itemData(index)
            with open(palletteFileInfo.absoluteFilePath(), 'r') as json_file:
                soundButton_data = json.load(json_file)

            # Loop through all the buttons to either set them based on the file
            # or clear and disable
            for sound in soundButton_data.items():
                if buttonNumber < self.ui.soundFXGrid.count():
                    if QFileInfo.exists(sound[1]): # The file still exists
                        file = QFileInfo(sound[1])
                        if file.suffix() == "wav": # Only wav files are supported for sound effect
                            self.sfx_buttons[buttonNumber].loadSoundEffect(file)
                        else:
                            self.sfx_buttons[buttonNumber].disable()
                    else:
                        self.sfx_buttons[buttonNumber].disable()

                buttonNumber += 1

        for disabledButton in range(buttonNumber, self.ui.soundFXGrid.count()):
            self.sfx_buttons[disabledButton].disable()

    @Slot(int)
    def set_fx_volume(self, value):
        sliderMax = self.ui.soundFXVolumeHS.maximum()
        for sound in self.sfx_buttons:
            sound.set_fx_volume(value/sliderMax)
