# media_features.py
# This Python file uses the following encoding: utf-8
from PySide6.QtCore import QObject, Slot, Signal, QFileInfo, QDirIterator, QUrl
from PySide6.QtGui import QImageReader, QPixmap, QMovie
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QStyle, QPushButton
from PySide6.QtMultimedia import QMediaPlayer
from Improtronics import SoundFX, SlideWidget
from MediaFileDatabase import MediaFileDatabase
import utilities
import json

# Module to encapsulate image and media search along with the media database management
class media_features(QObject):
    mainMediaShow = Signal(str)    # Custom signal that decouples the media display from controlboard
    auxMediaShow  = Signal(str)    # Custom signal that decouples the media display from controlboard

    def __init__(self, ui, settings, media_player):
        super(media_features,self).__init__()

        self.ui = ui
        self._settings = settings
        self.media_player = media_player

        # QMovies for displaying GIF previews. Avoids memory leaks by keeping them around
        self.search_preview_movie = QMovie()
        self.search_preview_movie.setSpeed(100)

        # In memory database configuration
        self.media_file_database = MediaFileDatabase()

        # Initial Image Indexing
        media_count = self.media_file_database.index_media(self._settings.getMediaDir())
        self.ui.mediaFilesCountLBL.setText(str(media_count))

        # Initial Sound Indexing
        sound_count = self.media_file_database.index_sounds(self._settings.getSoundDir())
        self.ui.soundFilesCountLBL.setText(str(sound_count))

        # Sound Pallette Setup
        self.sfx_buttons = [] #empty array
        self.sound_fx_number = 25      #number of soundeffects for a pallette

        _volume = self.ui.soundFXVolumeHS.value()/self.ui.soundFXVolumeHS.maximum()
        for button in range(self.sound_fx_number):
            sfx_button = self.ui.findChild(QPushButton, "soundFXPB" +str(button+1))
            _soundFX = SoundFX(sfx_button)
            _soundFX.set_fx_volume(_volume)
            self.sfx_buttons.append(_soundFX)

        # Use standard icons
        self.ui.soundPlayPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.soundPausePB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.soundStopPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaStop))
        self.ui.soundLoopPB.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        self.ui.soundMoveUpPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))
        self.ui.soundMoveDownPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))
        self.ui.soundAddToListPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        self.ui.soundRemoveFromListPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowBack))

        # Sound Pallettes
        self.palletteSelect = self.ui.soundPalettesCB
        self.load_sound_pallettes()

        self.connect_slots()

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
        self.ui.soundLoopPB.clicked.connect(self.sound_loop)


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
# #### connections

    # Media Utilties
    def selectImageFile(self):
        selectedFileName = QFileDialog.getOpenFileName(self.ui, "Select Media", self._settings.getMediaDir() , "Media Files "+self.media_file_database.get_media_supported_for_dialog())
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
            reply = QMessageBox.information(self.ui, 'No Search Results', 'No media with those tags found.')

    @Slot()
    def set_media_library(self):
        setDir = QFileDialog.getExistingDirectory(self.ui,
                "Select the Media Library location",
                self._settings.getMediaDir(), QFileDialog.ShowDirsOnly)
        if setDir:
            self._settings.setMediaDir(setDir)
            media_count = self.media_file_database.index_media(setDir)
            self.ui.mediaFilesCountLBL.setText(str(media_count))

            # The Media Library is also part of the Media mediaModel so reset it
            self.image_tree_view = self.ui.slideShowFilesTreeView
            self.image_tree_view.setModel(self.mediaModel)
            self.image_tree_view.setRootIndex(self.mediaModel.index(setDir))
            for i in range(1, self.mediaModel.columnCount()):
                self.image_tree_view.header().hideSection(i)
            self.image_tree_view.setHeaderHidden(True)

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
                self._settings.getSoundDir(), QFileDialog.ShowDirsOnly)
        if setDir:
            self._settings.setSoundDir(setDir)
            soundsCount = self.media_file_database.index_sounds(setDir)
            self.ui.soundFilesCountLBL.setText(str(soundsCount))

    @Slot()
    def sound_play(self):
        if self.media_player.playbackState() == QMediaPlayer.PausedState:
            self.media_player.play()
            return

        if self.ui.soundSearchResultsLW.currentItem() != None:
            self.media_player.setSource(QUrl.fromLocalFile(self.ui.soundSearchResultsLW.currentItem().imagePath()))
            self.media_player.setPosition(0)
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

    @Slot()
    def sound_loop(self):
        if self.ui.soundLoopPB.isChecked():
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
                                self._settings.getConfigDir(),
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
                                   self._settings.getConfigDir(),
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
                                   self._settings.getConfigDir(),
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
        palletteIter = QDirIterator(self._settings.getConfigDir(),{"*.sfx"})
        while palletteIter.hasNext():
            palletteFileInfo = palletteIter.nextFileInfo()
            palletteFileName = palletteFileInfo.completeBaseName()
            self.palletteSelect.addItem(palletteFileName, palletteFileInfo)

    @Slot(int)
    def load_sound_effects(self, index):
        # During initialization, a negative index is sent. Use that as a trigger
        # to diable all buttons in the case no files exist
        buttonNumber = 0
        if index >= 0 :
            palletteFileInfo = self.palletteSelect.itemData(index)
            with open(palletteFileInfo.absoluteFilePath(), 'r') as json_file:
                soundButton_data = json.load(json_file)

            # Loop through all the buttons to either set them based on the file
            # or clear and disable
            for sound in soundButton_data.items():
                if buttonNumber < self.sound_fx_number:
                    if QFileInfo.exists(sound[1]): # The file still exists
                        file = QFileInfo(sound[1])
                        if file.suffix() == "wav": # Only wav files are supported for sound effect
                            self.sfx_buttons[buttonNumber].loadSoundEffect(file)
                        else:
                            self.sfx_buttons[buttonNumber].disable()
                    else:
                        self.sfx_buttons[buttonNumber].disable()

                buttonNumber += 1

        for disabledButton in range(buttonNumber, self.sound_fx_number):
            self.sfx_buttons[disabledButton].disable()

    @Slot(int)
    def set_fx_volume(self, value):
        sliderMax = self.ui.soundFXVolumeHS.maximum()
        for sound in self.sfx_buttons:
            sound.set_fx_volume(value/sliderMax)
