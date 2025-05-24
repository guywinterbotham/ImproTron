import json
import logging

from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QImageReader, QPixmap, QMovie
from PySide6.QtWidgets import (QColorDialog, QFileDialog, QFileSystemModel, QMessageBox, QWidget,
                                QApplication, QPushButton, QDoubleSpinBox, QStyle, QListWidgetItem, QSizePolicy)

from PySide6.QtCore import (Slot, Signal, Qt, QTimer, QItemSelection, QFileInfo, QDir,
                                QFile, QIODevice, QEvent, QUrl, QRandomGenerator, QSize, QThread)
from PySide6.QtMultimedia import (QCamera, QCameraDevice, QMediaCaptureSession, QMediaDevices, QMediaPlayer, QAudioOutput)
from PySide6.QtNetwork import QNetworkAccessManager

from PySide6.QtMultimediaWidgets import QVideoWidget

from settings import Settings
from Improtronics import ImproTron, SlideWidget, HotButtonHandler, SlideLoaderThread

from games_feature import GamesFeature
from text_feature import TextFeature
from media_features import MediaFeatures
from thingz_feature import ThingzFeature
from monitor_preview import MonitorPreview
# from lighting_feature import LightingFeature # Future DMX integration
import utilities
import ImproTronIcons
from TouchPortal import TouchPortal

logger = logging.getLogger(__name__)

class ImproTronControlBoard(QWidget):
    slideLoadSignal = Signal(str)
    def __init__(self, parent=None):
        super(ImproTronControlBoard,self).__init__()
        self._settings = Settings()
        logger.info("Settings loaded.")

        loader = QUiLoader()
        self.ui = loader.load("ImproTronControlPanel.ui")
        logger.info("UI loaded.")

        # Model/View/Controller model for images
        self.mediaModel = QFileSystemModel()
        self.mediaModel.setRootPath(self._settings.get_media_directory())

        # MediaPlayer and audio setup for movies, webcams, and sound
        self.mediaPlayer = QMediaPlayer()
        self.audioOutput = QAudioOutput()
        self.mediaPlayer.setAudioOutput(self.audioOutput)
        logger.info("Media player and audio output initialized.")
        self.audioOutput.setVolume(self.ui.soundVolumeSL.value()/self.ui.soundVolumeSL.maximum())
        self.m_devices = QMediaDevices()
        self.m_devices.videoInputsChanged.connect(self.updateCameras)
        self.updateCameras()
        self.last_media_duration = 0 # used to over come a problem in slides with a single video

        self.m_captureSession = QMediaCaptureSession()
        self.setCamera(QMediaDevices.defaultVideoInput())
        logger.info("Default camera set up.")

        # Connect error signal
        self.mediaPlayer.errorOccurred.connect(self.mediaplayer_handle_error)

        # QMovies for displaying GIF previews. Avoids memory leaks by keeping them around
        self.mainPreviewMovie = QMovie()
        self.mainPreviewMovie.setSpeed(100)
        self.auxPreviewMovie = QMovie()
        self.auxPreviewMovie.setSpeed(100)

        # Create Screens and relocate. Main done second so it is on top
        self.mainDisplay = ImproTron("Main")
        self.auxiliaryDisplay = ImproTron("Auxiliary")

        self.auxiliaryDisplay.restore()
        self.auxiliaryDisplay.set_location(self._settings.get_aux_location())
        self.auxiliaryDisplay.maximize()

        self.mainDisplay.restore()
        self.mainDisplay.set_location(self._settings.get_main_location())
        self.mainDisplay.maximize()
        logger.info("Main and Auxiliary displays initialized and configured.")

        # Create a shared QNetworkAccessManager
        self.shared_network_manager = QNetworkAccessManager()

        # Replace the main image preview with a DragDropLabel
        self.main_preview = MonitorPreview(self.ui.imagePreviewMain, self.ui.imagePreviewMainHL, self.mainDisplay, self.ui.stretchMainCB.isChecked(), self.shared_network_manager, parent=self.ui.imagePreviewMain.parent())
        self.ui.imagePreviewMain = self.main_preview
        self.ui.loadImageMainPB.clicked.connect(self.getImageFileMain)
        self.ui.pasteImageMainPB.clicked.connect(self.main_preview.paste_image)
        self.ui.blackoutMainPB.clicked.connect(self.main_preview.blackout)
        self.ui.stretchMainCB.checkStateChanged.connect(self.main_preview.previewStretch)

        # Replace the auxilliary image preview with a DragDropLabel
        self.aux_preview = MonitorPreview(self.ui.imagePreviewAuxiliary, self.ui.imagePreviewAuxiliaryHL, self.auxiliaryDisplay, self.ui.stretchMainCB.isChecked(), self.shared_network_manager, parent=self.ui.imagePreviewAuxiliary.parent())
        self.ui.imagePreviewAuxiliary = self.aux_preview
        self.ui.loadImageAuxiliaryPB.clicked.connect(self.getImageFileAuxiliary)
        self.ui.pasteImageAuxiliaryPB.clicked.connect(self.aux_preview.paste_image)
        self.ui.blackoutAuxPB.clicked.connect(self.aux_preview.blackout)
        self.ui.stretchAuxCB.checkStateChanged.connect(self.aux_preview.previewStretch)
        logger.info("Main and Auxiliary preview handlers initialized.")

        self.ui.blackoutBothPB.clicked.connect(self.blackout_both)

        # Instantiate Features
        self.games_feature = GamesFeature(self.ui, self._settings, self.mainDisplay, self.auxiliaryDisplay)
        self.text_feature = TextFeature(self.ui, self._settings, self.mainDisplay, self.auxiliaryDisplay)
        self.thingz_feature = ThingzFeature(self.ui, self._settings, self.mainDisplay, self.auxiliaryDisplay)
        self.media_features = MediaFeatures(self.ui, self._settings, self.mediaModel, self.mediaPlayer)
        self.media_features.reset_media_view(self._settings.get_media_directory())

        # Disable the DMX Feature which is under design and development
        #self.lighting_feature = LightingFeature(self.ui, self._settings, "127.0.0.1", 7700) # Future DMX integration
        index = self.ui.featureTabs.indexOf(self.ui.lightingTab)
        if index != -1:
            self.ui.featureTabs.removeTab(index)

        logger.info("Core feature modules (Games, Text, Thingz, Media) initialized.")

        # Custom Signals allows the media feature to leave screen control encapulated in the control panel
        self.media_features.mainMediaShow.connect(self.showMediaOnMain)
        self.media_features.auxMediaShow.connect(self.showMediaOnAux)

        # Camera Configuration
        # Wire camera controls
        self.ui.cameraStartPB.clicked.connect(self.startCamera)
        self.ui.cameraStopPB.clicked.connect(self.stopCamera)

        # Fetch and configure camera devices
        self.ui.camerasLW.itemClicked.connect(self.updateCameraDevice)

        # Connect the media player to retrieve duration after the file is loaded
        self.mediaPlayer.durationChanged.connect(self.updateDuration)

        # Set up volume control
        self.ui.soundVolumeSL.valueChanged.connect(self.set_sound_volume)

        # Recall Team names and colors then connect Score related signals to slots
        self.ui.teamNameLeft.textChanged.connect(self.showLeftTeam)
        self.ui.teamNameRight.textChanged.connect(self.showRightTeam)
        self.ui.colorRightPB.clicked.connect(self.pickRightTeamColor)
        self.ui.colorLeftPB.clicked.connect(self.pickLeftTeamColor)
        self.ui.showScoresMainPB.clicked.connect(self.showScoresMain)
        self.ui.showScoresBothPB.clicked.connect(self.showScoresBoth)
        self.ui.showScoresAuxiliaryPB.clicked.connect(self.showScoresAuxiliary)

        self.setLeftTeamColors(self._settings.get_left_team_color())
        self.setRightTeamColors(self._settings.get_right_team_color())
        self.ui.teamNameLeft.setText(self._settings.get_left_team_name())
        self.ui.teamNameRight.setText(self._settings.get_right_team_name())

        # Quick Add Buttons for score updates.
        self.ui.add50PB.clicked.connect(self.quickAdd50) # Add 5 to Left team
        self.ui.add32PB.clicked.connect(self.quickAdd32) # Add 3 to Left, 2 to Right
        self.ui.add23PB.clicked.connect(self.quickAdd23) # Add 2 to Left, 3 to Right
        self.ui.add05PB.clicked.connect(self.quickAdd05) # Add 5 to Right team

        # Countdown timer controls
        self.ui.startTimerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.startTimerPB.clicked.connect(self.startTimer)

        self.ui.resetTimerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.ui.resetTimerPB.clicked.connect(self.resetTimer)

        self.ui.pauseTimerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.pauseTimerPB.clicked.connect(self.pauseTimerPB)

        self.ui.timerVisibleMainCB.stateChanged.connect(self.timerVisibleMain)

        # Slide Show Management
        # Selection changes will trigger a slot
        selectionModel = self.ui.slideShowFilesTreeView.selectionModel()
        selectionModel.selectionChanged.connect(self.imageSelectedfromDir)

        # Connect Slide Show Management
        self.ui.searchtoSlideShowPB.clicked.connect(self.searchtoSlideShow) # On Image search but part of this feature
        self.ui.slideListLW.itemClicked.connect(self.previewSelectedSlide)
        self.ui.slideListLW.itemDoubleClicked.connect(self.showSlideMain)
        self.ui.addSlidePB.clicked.connect(self.addSlidetoList)
        self.ui.slideShowSecondSB.valueChanged.connect(self.slideShowSecondChanged)

        self.ui.slideMoveUpPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))
        self.ui.slideMoveUpPB.clicked.connect(self.slideMoveUp)

        self.ui.slideMoveDownPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))
        self.ui.slideMoveDownPB.clicked.connect(self.slideMoveDown)

        self.ui.removeSlidePB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton))
        self.ui.removeSlidePB.clicked.connect(self.removeSlidefromList)

        self.ui.clearSlideShowPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogDiscardButton))
        self.ui.clearSlideShowPB.clicked.connect(self.clearSlideShow)

        self.ui.loadSlideShowPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.ui.loadSlideShowPB.clicked.connect(self.loadSlideShow)

        self.ui.saveSlideShowPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.ui.saveSlideShowPB.clicked.connect(self.saveSlideShow)

        self.ui.showSlideMainPB.clicked.connect(self.showSlideMain)
        self.ui.showSlideAuxiliaryPB.clicked.connect(self.showSlideAuxiliary)
        self.ui.showSlideBothPB.clicked.connect(self.showSlideBoth)

        # Slideshow Timer wiring
        self.slideShowTimer = QTimer()
        self.ui.slideShowSecondSB.setValue(self._settings.get_slideshow_delay())
        self.paused = False
        self. currentSlide = 0
        self.slideShowTimer.timeout.connect(self.nextSlide)

        # Async thread set up
        self.slideLoaderThread = SlideLoaderThread()

        self.slideLoadSignal.connect(self.slideLoaderThread.loadSlide)

        self.thread = QThread()
        self.slideLoaderThread.moveToThread(self.thread)
        self.thread.start()

        # Slide controls connections
        self.ui.slideShowSkipPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.ui.slideShowSkipPB.clicked.connect(self.slideShowSkip)

        self.ui.slideShowRestartPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.ui.slideShowRestartPB.clicked.connect(self.slideShowRestart)

        self.ui.slideShowForwardPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaSeekForward))
        self.ui.slideShowForwardPB.clicked.connect(self.slideShowForward)

        self.ui.slideShowRewindPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaSeekBackward))
        self.ui.slideShowRewindPB.clicked.connect(self.slideShowBack)

        self.ui.slideShowPlayPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.slideShowPlayPB.clicked.connect(self.slideShowPlay)

        self.ui.slideShowPausePB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.slideShowPausePB.clicked.connect(self.slideShowPause)

        self.ui.slideShowStopPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaStop))
        self.ui.slideShowStopPB.clicked.connect(self.slideShowStop)

        # Promo Slides - replaces the slide show with a direct load from a preset directory
        self.ui.startPromosPB.clicked.connect(self.startPromosSlideShow)
        self.promosMode = False # determines whether the slide list is resampled from the promo dir each cycle

        # Whammy seconds settings
        self.ui.secsPerWhamCB.addItems(['0.5', '1.0', '1.5', '2.0'])
        self.ui.whammyPB.clicked.connect(self.startWhamming)
        self.whammyTimer = QTimer()
        self.whammyRandomizer = QRandomGenerator()
        self.whams = 0
        self.whammyTimer.timeout.connect(self.nextWham)

        # Video Player Wiring

        # The Video Widget is not support by the designer so it is created here
        # using code from the generated UI
        self.mediaViewerVW = QVideoWidget(self.ui.videoTab)
        self.mediaViewerVW.setObjectName(u"mediaViewerVW")
        sizePolicy11 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy11.setHorizontalStretch(1)
        sizePolicy11.setVerticalStretch(1)
        sizePolicy11.setHeightForWidth(self.mediaViewerVW.sizePolicy().hasHeightForWidth())
        self.mediaViewerVW.setSizePolicy(sizePolicy11)
        self.mediaViewerVW.setMinimumSize(QSize(430, 290))
        self.ui.videoPreviewVL.addWidget(self.mediaViewerVW)

        self.ui.videoPlayPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.videoPlayPB.clicked.connect(self.videoPlay)

        self.ui.videoPausePB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.videoPausePB.clicked.connect(self.videoPause)

        self.ui.videoStopPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaStop))
        self.ui.videoStopPB.clicked.connect(self.videoStop)

        self.ui.videoLoopPB.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        self.ui.videoLoopPB.clicked.connect(self.videoLoop)

        self.ui.loadVideoPB.clicked.connect(self.getVideoFile)

        # Touch Portal Connect
        self.touchPortalClient = TouchPortal('127.0.0.1', 12136)
        logger.info("TouchPortal client initialized.")
        self.ui.touchPortalConCB. checkStateChanged.connect(self.connectTouchPortal)
        tpFlag = self._settings.get_touch_portal_connect()
        self.ui.touchPortalConCB.setChecked(tpFlag)

        # Connect the Touch Portal custom signals to a slot
        self.touchPortalClient.buttonAction.connect(self.onTouchPortalButtonAction)
        self.touchPortalClient.spinBoxAction.connect(self.onTouchPortalSpinBoxAction)
        self.touchPortalClient.mediaAction.connect(self.onTouchPortalMediaAction)
        self.touchPortalClient.soundAction.connect(self.onTouchPortalSoundAction)

        # Preferences
        self.ui.aboutPB.clicked.connect(self.about)
        self.ui.improtronUnlockPB.clicked.connect(self.improtronUnlock)
        self.ui.startupImagePB.clicked.connect(self.startupImage)
        self.ui.promosDirPB.clicked.connect(self.selectPromosDirectory)

        # Display the default images if they exist
        self.showMediaOnMain(self._settings.get_startup_image())
        self.showMediaOnAux(self._settings.get_startup_image())
        # Force the default feature tab on start up to the Text Display
        self.ui.featureTabs.setCurrentWidget(self.ui.textDisplayTab)

        # Then override with the promos if the promo directory has been set up
        _promosDirectory = self._settings.get_promos_directory()
        if len(_promosDirectory) >0:
            self.ui.featureTabs.setCurrentWidget(self.ui.slideShowTab)
            self.startPromosSlideShow()

            # Force the default feature tab on start up to the Slide Show to make it quicker to stop for the show.
            self.ui.featureTabs.setCurrentWidget(self.ui.slideShowTab)

        # Hot Buttons Wiring
        self.hot_buttons = [] #empty array

        for button in range(self.ui.hotButtonHL.count()):
            hotButton = HotButtonHandler(button+1, self.ui, self.media_features)
            self.hot_buttons.append(hotButton)

            # Custom Signals allows the HotButtonHandler to leave screen control encapulated in the control panel
            hotButton.mainMediaShow.connect(self.showMediaOnMain)
            hotButton.auxMediaShow.connect(self.showMediaOnAux)
        logger.info("Hot buttons initialized.")


        # Load the last saved hotbutton file
        lastHotButtons = self._settings.get_last_hot_button_file()
        if len(lastHotButtons) > 0:
            with open(lastHotButtons, 'r') as json_file:
                button_data = json.load(json_file)

            for button in range(self.ui.hotButtonHL.count()):
                self.hot_buttons[button].load(button_data)

        # Set a slot for the clear, load and save buttons
        self.ui.hotButtonClearPB.clicked.connect(self.clearHotButtonsClicked)
        self.ui.hotButtonLoadPB.clicked.connect(self.loadHotButtonsClicked)
        self.ui.hotButtonSavePB.clicked.connect(self.saveHotButtonsClicked)


        # YouTube Player support
        self.ui.loadYouTubePB.clicked.connect(self.load_youtube)
        self.ui.pauseYouTubePB.clicked.connect(self.pause_youtube)
        #self.ui.muteYouTubePB.clicked.connect(self.mute_youtube) Currently doesn't work
        self.ui.playYouTubePB.clicked.connect(self.play_youtube)

        # Set up an event filter to handle the orderly shutdown of the app.
        self.ui.installEventFilter(self)

        # Set up the chrome of the control board
        self.ui.setWindowFlags(
            Qt.Window |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint |
            Qt.WindowTitleHint
            )
        logger.info("ImproTronControlBoard initialization complete.")

        # Let the fun begin!
        self.ui.show()
# ################################################################################################
# ####################### Slots and more
    def eventFilter(self, obj, event):
        if obj is self.ui and event.type() == QEvent.Close:
            self.shutdown()
            event.ignore()
            return True
        return super(ImproTronControlBoard, self).eventFilter(obj, event)

    def shutdown(self):
        logging.info("ImproTron shutting down")
        self.mainDisplay.shutdown()
        self.auxiliaryDisplay.shutdown()
        self._settings.save()
        self.touchPortalClient.disconnectTouchPortal()
        self.thread.quit()
        self.ui.removeEventFilter(self)
        self.deleteLater()
        QApplication.quit()

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
                return mediaInfo.suffix().lower() in  ['mp4', 'm4v', 'mp4v', 'wmv']
            else:
                return False
        else:
            return False

    # Note: This is both a local call but a slot for images emitted from the media features
    @Slot(str)
    def showMediaOnMain(self, file_name):
        if len(file_name) <= 0:
            return

        if not QFile(file_name).exists():
            logger.warn(f"Mising Media File on Main: {file_name}")
            return

        self.mainPreviewMovie.stop()
        if self.isAnimatedGIF(file_name):
            self.mainPreviewMovie.setFileName(file_name)
            if not self.mainPreviewMovie.isValid():
                logger.error(f"Main display: Failed to load GIF {file_name}. Error: {self.mainPreviewMovie.errorString()}")
                return # Stop further processing for this invalid GIF
            if self.mainPreviewMovie.isValid():
                self.mainPreviewMovie.setScaledSize(self.main_preview.size())
                self.main_preview.setMovie(self.mainPreviewMovie)
                self.mainPreviewMovie.start()
                self.mainDisplay.showMovie(file_name)
        elif self.media_features.isImage(file_name):
            reader = QImageReader(file_name)
            reader.setAutoTransform(True)
            newImage = reader.read()
            if newImage.isNull():
                logger.error(f"Main display: Failed to read image {file_name}. QImageReader error: {reader.errorString()}")
                return # Stop further processing
            self.main_preview.load_image(newImage)
        else:
            logging.warning(f"Unsupported media for main: {file_name}")

    # Note: This is both a local call but a slot for images emitted from the media features
    @Slot(str)
    def showMediaOnAux(self, file_name):
        if len(file_name) <= 0:
            return

        if not QFile(file_name).exists():
            logger.warn(f"Mising Media File on Aux: {file_name}")
            return

        self.auxPreviewMovie.stop()
        if self.isAnimatedGIF(file_name):
            self.auxPreviewMovie.setFileName(file_name)
            if not self.auxPreviewMovie.isValid():
                logger.error(f"Aux display: Failed to load GIF {file_name}. Error: {self.auxPreviewMovie.errorString()}")
                return
            if self.auxPreviewMovie.isValid():
                self.auxPreviewMovie.setScaledSize(self.aux_preview.size())
                self.aux_preview.setMovie(self.auxPreviewMovie)
                self.auxPreviewMovie.start()
                self.auxiliaryDisplay.showMovie(file_name)
        elif self.media_features.isImage(file_name):
            reader = QImageReader(file_name)
            reader.setAutoTransform(True)
            newImage = reader.read()
            if newImage.isNull():
                logger.error(f"Aux display: Failed to read image {file_name}. QImageReader error: {reader.errorString()}")
                return
            self.aux_preview.load_image(newImage)
        else:
            logging.warning(f"Unsupported media for aux: {file_name}")

    def setLeftTeamColors(self, colorSelected):
        style = utilities.style_sheet(colorSelected)

        self.ui.teamNameLeft.setStyleSheet(style)
        self.ui.leftThingTeamRB.setStyleSheet(style)
        self.mainDisplay.colorizeLeftScore(style)
        self.auxiliaryDisplay.colorizeLeftScore(style)

    def setRightTeamColors(self, colorSelected):
        style = utilities.style_sheet(colorSelected)

        self.ui.teamNameRight.setStyleSheet(style)
        self.ui.rightThingTeamRB.setStyleSheet(style)
        self.mainDisplay.colorizeRightScore(style)
        self.auxiliaryDisplay.colorizeRightScore(style)

    @Slot()
    def pickLeftTeamColor(self):
        colorSelected = QColorDialog.getColor(self._settings.get_left_team_color(), self.ui,title = 'Pick Left Team Color')
        if colorSelected.isValid():
            self._settings.set_left_team_color(colorSelected)
            self.setLeftTeamColors(colorSelected)

    @Slot()
    def pickRightTeamColor(self):
        colorSelected = QColorDialog.getColor(self._settings.get_right_team_color(), self.ui,title = 'Pick Right Team Color')
        if colorSelected.isValid():
            self._settings.set_right_team_color(colorSelected)
            self.setRightTeamColors(colorSelected)

    @Slot()
    def blackout_both(self):
        self.main_preview.blackout()
        self.aux_preview.blackout()

    @Slot()
    def getImageFileMain(self):
        self.showMediaOnMain(self.media_features.select_image_file())

    @Slot()
    def getImageFileAuxiliary(self):
        self.showMediaOnAux(self.media_features.select_image_file())

    @Slot()
    def getVideoFile(self):
        file_name = QFileDialog.getOpenFileName(self.ui, "Select Video", self._settings.get_video_directory() , "Video Files (*.mp4 *.m4v *.mp4v *.wmv)")

        # If no file was seelcted then ignore the choice
        if len(file_name[0]) > 0:
            if self.isVideo(file_name[0]):
                self.mediaPlayer.setSource(QUrl(file_name[0]))
            else:
                logging.warning(f"Unsupported Video File selected: {file_name[0]}")

    @Slot()
    def showScoresMain(self):
        self.mainDisplay.updateScores(self.ui.teamScoreLeft.value(),self.ui.teamScoreRight.value())
        utilities.capture_window(self.mainDisplay, self.main_preview)

    @Slot()
    def showScoresAuxiliary(self):
        self.auxiliaryDisplay.updateScores(self.ui.teamScoreLeft.value(),self.ui.teamScoreRight.value())
        utilities.capture_window(self.auxiliaryDisplay, self.aux_preview)

    @Slot()
    def showScoresBoth(self):
        self.showScoresMain()
        self.showScoresAuxiliary()

    # Quick add buttons to update the score and immediate show on the Main Moitor
    @Slot()
    def quickAdd50(self):
        self.ui.teamScoreLeft.setValue(self.ui.teamScoreLeft.value()+5)
        self.showScoresBoth()

    @Slot()
    def quickAdd05(self):
        self.ui.teamScoreRight.setValue(self.ui.teamScoreRight.value()+5)
        self.showScoresBoth()

    @Slot()
    def quickAdd32(self):
        self.ui.teamScoreLeft.setValue(self.ui.teamScoreLeft.value()+3)
        self.ui.teamScoreRight.setValue(self.ui.teamScoreRight.value()+2)
        self.showScoresBoth()

    @Slot()
    def quickAdd23(self):
        self.ui.teamScoreLeft.setValue(self.ui.teamScoreLeft.value()+2)
        self.ui.teamScoreRight.setValue(self.ui.teamScoreRight.value()+3)
        self.showScoresBoth()

    @Slot(str)
    def showLeftTeam(self, teamName):
        self.mainDisplay.showLeftTeam(teamName)
        self.auxiliaryDisplay.showLeftTeam(teamName)
        self.ui.leftThingTeamRB.setText(teamName)
        self._settings.set_left_team_name(teamName)

    @Slot(str)
    def showRightTeam(self, teamName):
        self.mainDisplay.showRightTeam(teamName)
        self.auxiliaryDisplay.showRightTeam(teamName)
        self.ui.rightThingTeamRB.setText(teamName)
        self._settings.set_right_team_name(teamName)

    # Unlock the Improtron Displays so they can be moved. Lock them to maximize
    # on th screen they subsequently reside on.
    def improtronUnlock(self):
        if self.ui.improtronUnlockPB.isChecked():
            self.auxiliaryDisplay.restore()
            self.mainDisplay.restore()
        else:
            self._settings.set_aux_location(self.auxiliaryDisplay.get_location())
            self._settings.set_main_location(self.mainDisplay.get_location())
            self._settings.save()

            # Order matters so the main displays on top
            self.auxiliaryDisplay.maximize()
            self.mainDisplay.maximize()

    # Slideshow Management
    @Slot(int)
    def slideShowSecondChanged(self, value):
        self._settings.set_slideshow_delay(value)

    @Slot(QItemSelection, QItemSelection)
    def imageSelectedfromDir(self, new_selection, old_selection):
        # get the text of the selected item
        index = self.ui.slideShowFilesTreeView.selectionModel().currentIndex()
        if not self.mediaModel.isDir(index):
            imageFileInfo = self.mediaModel.fileInfo(index)
            reader = QImageReader(imageFileInfo.absoluteFilePath())
            reader.setAutoTransform(True)
            newImage = reader.read()
            if newImage.isNull():
                logger.warning(f"Slide preview: Failed to read image {imageFileInfo.absoluteFilePath()}. QImageReader error: {reader.errorString()}")
                # self.ui.slidePreviewLBL.clear() # Optionally clear preview
                return 

            # Scale to match the preview
            self.ui.slidePreviewLBL.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.slidePreviewLBL.size())))

    @Slot(SlideWidget)
    def previewSelectedSlide(self, slide):
        reader = QImageReader(slide.imagePath())
        reader.setAutoTransform(True)
        newImage = reader.read()
        if newImage.isNull():
            logger.warning(f"Slide preview (from list): Failed to read image {slide.imagePath()}. QImageReader error: {reader.errorString()}")
            # self.ui.slidePreviewLBL.clear() # Optionally clear preview
            return

        # Scale to match the preview
        self.ui.slidePreviewLBL.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.slidePreviewLBL.size())))


    @Slot()
    def addSlidetoList(self):
        # get the text of the selected item
        index = self.ui.slideShowFilesTreeView.selectionModel().currentIndex()
        if not self.mediaModel.isDir(index):
            SlideWidget(self.mediaModel.fileInfo(index), self.ui.slideListLW)

    @Slot()
    def slideMoveUp(self):
        slideRow = self.ui.slideListLW.currentRow()
        if slideRow < 0:
            return
        thing = self.ui.slideListLW.takeItem(slideRow)
        self.ui.slideListLW.insertItem(slideRow-1,thing)
        self.ui.slideListLW.setCurrentRow(slideRow-1)

    @Slot()
    def slideMoveDown(self):
        slideRow = self.ui.slideListLW.currentRow()
        if slideRow < 0:
            return
        thing = self.ui.slideListLW.takeItem(slideRow)
        self.ui.slideListLW.insertItem(slideRow+1,thing)
        self.ui.slideListLW.setCurrentRow(slideRow+1)

    @Slot()
    def removeSlidefromList(self):
        self.ui.slidePreviewLBL.clear()
        self.ui.slideListLW.takeItem(self.ui.slideListLW.row(self.ui.slideListLW.currentItem()))

    def loadSlides(self, file_name):
        # Read the JSON data from the file
        if len(file_name) > 0:
            with open(file_name, 'r') as json_file:
                slideshow_data = json.load(json_file)

            for slide in slideshow_data.items():
                file = QFileInfo(slide[1])
                SlideWidget(file, self.ui.slideListLW)

    @Slot()
    def loadSlideShow(self):
        if self.ui.slideListLW.count() > 0:
            reply = QMessageBox.question(self.ui, 'Replace Slides', 'Are you sure you want replace the current slides?',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.ui.slideListLW.clear()

        file_name = QFileDialog.getOpenFileName(self.ui, "Load Slideshow",
                                    self._settings.get_config_dir(),
                                    "Slide Shows (*.ssh)")

        self.loadSlides(file_name[0])

    @Slot()
    def saveSlideShow(self):
        file_name = QFileDialog.getSaveFileName(self.ui, "Save Slide Show",
                                   self._settings.get_config_dir(),
                                   "Slide Shows (*.ssh)")
        if len(file_name[0]) > 0:
            slide_data = {}
            for slide in range(self.ui.slideListLW.count()):
                slideName = "slide"+str(slide)
                slide_data[slideName] = self.ui.slideListLW.item(slide).imagePath()

            # Write the JSON string to a file
            with open(file_name[0], 'w', encoding='utf8') as json_file:
                json.dump(slide_data, json_file, indent=2)
                json_file.close()

    @Slot()
    def clearSlideShow(self):
        reply = QMessageBox.question(self.ui, 'Clear Slides', 'Are you sure you want clear all slides?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.slideListLW.clear()

    # Promos specific behaviour
    def loadPromosSlides(self):
        _promosDirectory = self._settings.get_promos_directory()
        if len(_promosDirectory) > 0:
            self.ui.slideListLW.clear()
            for file_info in QDir(_promosDirectory).entryInfoList("*.jpg *.png", QDir.Files, QDir.Name):
                SlideWidget(file_info, self.ui.slideListLW)

    @Slot()
    def startPromosSlideShow(self):
        self.promosMode = True
        self.loadPromosSlides()
        self.slideShowPlay()

    @Slot()
    def showSlideMain(self):
        if self.ui.copytoAuxCB.isChecked(): # Duplicate to Aux if Duplicate preference set
            self.showSlideBoth()
        else:
            if self.ui.slideListLW.currentItem() != None:
                self.showMediaOnMain(self.ui.slideListLW.currentItem().imagePath())

    @Slot()
    def showSlideAuxiliary(self):
        if self.ui.slideListLW.currentItem() != None:
            self.showMediaOnAux(self.ui.slideListLW.currentItem().imagePath())

    @Slot()
    def showSlideBoth(self):
        if self.ui.slideListLW.currentItem() != None:
            self.showMediaOnMain(self.ui.slideListLW.currentItem().imagePath())
            self.showMediaOnAux(self.ui.slideListLW.currentItem().imagePath())

    # Slots for handling the Slide Show Player
    @Slot()
    def nextSlide(self):
        # Force the media player to stop just in case there is video play back occuring
        self.mediaPlayer.stop()

        # Have a default timeout. This will get overridden for videos.
        self.slideShowTimer.setInterval(self._settings.get_slideshow_delay()*1000)

        # Resample the promos directory once the current cycle is done
        if self.promosMode and self.currentSlide == 0:
            self.loadPromosSlides()

        # Progress the slide show if there are now slides to show in the list
        slideCount = self.ui.slideListLW.count()
        if slideCount > 0:
            self.currentSlide = self.currentSlide % slideCount
            self.ui.slideListLW.setCurrentRow(self.currentSlide)

            # Determine the file type so as to correcty set the timeout to the default or video length
            file_name = self.ui.slideListLW.currentItem().imagePath()
            if self.isAnimatedGIF(file_name) or self.media_features.isImage(file_name):
                self.showSlideMain()
            elif self.isVideo(file_name):
                self.mediaPlayer.setSource(QUrl(file_name))
                self.mediaPlayer.setVideoOutput(self.mainDisplay.showVideo())
                self.mediaPlayer.setPosition(0)

                # This is an attempt to handle a situation where a slide show has one video
                # The media player loads the same video with the same length and so never triggers
                # an event to change the duration for the slide show.
                if self.last_media_duration > 0:
                    self.slideShowTimer.setInterval(self.last_media_duration)

                self.mediaPlayer.play()

            else:
                logging.warning(f"Unsupported Media Type: {file_name}")

            self.currentSlide += 1 # Move onto the next slide

        else:
            self.currentSlide = 0
            logging.warning(f"Missing Slides: {self.currentSlide}")

    @Slot()
    def slideShowRestart(self):
        slideCount = self.ui.slideListLW.count()
        if slideCount > 0:
            self.currentSlide = 0
            self.ui.slideListLW.setCurrentRow(self.currentSlide)
            self.showSlideMain()

    @Slot()
    def slideShowBack(self):
        slideCount = self.ui.slideListLW.count()
        if slideCount > 1:
            self.currentSlide -= 1
            self.ui.slideListLW.setCurrentRow(self.currentSlide)
            self.showSlideMain()
        else:
            self.currentSlide = 1

    @Slot()
    def slideShowPlay(self):
        if not self.paused:
            self.currentSlide = 0
        self.paused = False

        self.ui.slideListLW.setCurrentRow(self.currentSlide)
        self.mainDisplay.blackout() # removes and text colors

        # A short delay to allow the timer to tigger and the the length to be determined by the media type to be shown
        self.slideShowTimer.setInterval(1000)
        self.slideShowTimer.start()

    @Slot()
    def slideShowPause(self):
        self.slideShowTimer.stop()
        if self.mediaPlayer.isPlaying():
            self.mediaPlayer.pause()
        self.paused = True

    @Slot()
    def slideShowStop(self):
        self.slideShowTimer.stop()
        if self.mediaPlayer.isPlaying():
            self.mediaPlayer.stop()
        self.paused = False
        self.promosMode = False # Cancel the promo behavior on a stop
        self.currentSlide = 0

    @Slot()
    def slideShowForward(self):
        self.nextSlide()

    @Slot()
    def slideShowSkip(self):
        slideCount = self.ui.slideListLW.count()
        if slideCount > 0:
            self.currentSlide = slideCount-1
            self.ui.slideListLW.setCurrentRow(self.currentSlide)
            self.showSlideMain()

    # Countdown timer controls
    @Slot()
    def startTimer(self):
        self.mainDisplay.timerStart(self.ui.countDownTimer.time(), self.ui.timeRedTimer.time())

    @Slot()
    def resetTimer(self):
        self.mainDisplay.timerReset(self.ui.countDownTimer.time(), self.ui.timeRedTimer.time())

    @Slot()
    def pauseTimerPB(self):
        self.mainDisplay.timerPause()

    @Slot()
    def timerVisibleMain(self):
        self.mainDisplay.timerVisible(self.ui.timerVisibleMainCB.isChecked())

    # Whammy Controlers
    @Slot()
    def startWhamming(self):
        slideCount = self.ui.slideListLW.count()

        if slideCount == 0:
            return

        whammyDelay = int(float(self.ui.secsPerWhamCB.currentText())*1000)
        self.whammyTimer.setInterval(whammyDelay)
        self.whams = self.ui.whammysSB.value()

        self.ui.slideListLW.setCurrentRow(self.whammyRandomizer.bounded(0, slideCount))
        self.slideLoadSignal.emit(self.ui.slideListLW.currentItem().imagePath())
        self.whammyTimer.start()

    @Slot()
    def nextWham(self):
        image = self.slideLoaderThread.getSlide()
        if image:
            if self.ui.stretchMainCB.isChecked():
                self.main_preview.setPixmap(QPixmap.fromImage(image.scaled(self.main_preview.size())))
            else:
                self.main_preview.setPixmap(QPixmap.fromImage(image.scaledToHeight(self.main_preview.size().height())))

            self.mainDisplay.showSlide(image, self.ui.stretchMainCB.isChecked())


        self.whams -= 1
        if self.whams <= 0:
            self.whammyTimer.stop()
            return

        randomSlide = self.whammyRandomizer.bounded(0, self.ui.slideListLW.count())
        self.ui.slideListLW.setCurrentRow(randomSlide)
        self.slideLoadSignal.emit(self.ui.slideListLW.currentItem().imagePath())

    @Slot() # Relocate to Slide show as it involves SlideWidgets
    def searchtoSlideShow(self):
        if self.ui.mediaSearchResultsLW.currentItem() != None:
            SlideWidget(QFileInfo(self.ui.mediaSearchResultsLW.currentItem().imagePath()), self.ui.slideListLW)

    @Slot()
    def soundMoveUp(self):
        soundRow = self.ui.soundQueueLW.currentRow()
        if soundRow < 0:
            return
        sound = self.ui.soundQueueLW.takeItem(soundRow)
        self.ui.soundQueueLW.insertItem(soundRow-1,sound)
        self.ui.soundQueueLW.setCurrentRow(soundRow-1)

    # Video Player Controler
    def videoPlay(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PausedState:
            self.mediaPlayer.play()
            return

        self.m_captureSession.setVideoOutput(None) #Disable the camera

        if self.ui.videoOnMainRB.isChecked():
            self.mediaPlayer.setVideoOutput(self.mainDisplay.showVideo())
        elif self.ui.videoOnAuxRB.isChecked():
            self.mediaPlayer.setVideoOutput(self.auxiliaryDisplay.showVideo())
        else:
            self.mediaPlayer.setVideoOutput(self.mediaViewerVW)

        self.mediaPlayer.setPosition(0)
        self.mediaPlayer.play()

    @Slot()
    def videoPause(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PausedState:
            self.mediaPlayer.play()
            return

        if self.mediaPlayer.isPlaying():
            self.mediaPlayer.pause()

    @Slot()
    def videoStop(self):
        self.mediaPlayer.stop()

    @Slot()
    def videoLoop(self):
        if self.ui.videoLoopPB.isChecked():
            self.mediaPlayer.setLoops(QMediaPlayer.Infinite)
        else:
            self.mediaPlayer.setLoops(QMediaPlayer.Once)
            if self.mediaPlayer.isPlaying():
                self.mediaPlayer.stop()

    def mediaplayer_handle_error(self, error, error_string):
        # Log the error
        logger.error(f"Media Player Error: {error} - {error_string}")

    # Slide Timer interval setting for videos: QMediaPlayer does not have the duration available on load
    # but does so when playing commences. If the slide timer is active this slot changes the interval to match
    @Slot(int)
    def updateDuration(self, duration):
        self.last_media_duration = duration + 100 # Add a little buffer
        if self.slideShowTimer.isActive():
            logger.info(f"Changing Video Length {duration}")
            self.slideShowTimer.setInterval(self.last_media_duration) # Add a little buffer

    # Preferences and Hot Buttons configuration settings
    @Slot()
    def clearHotButtonsClicked(self):
        for button in range(self.ui.hotButtonHL.count()):
            self.hot_buttons[button].clear()

    @Slot()
    def loadHotButtonsClicked(self):
        file_name = QFileDialog.getOpenFileName(self.ui, "Load Hot Buttons",
                    self._settings.get_config_dir(),
                    "Hot Buttons (*.hbt)")

        # Read the JSON data from the file
        if len(file_name[0]) > 0:

            # Remember the last loaded hotbutton file for when the app is started
            self._settings.set_last_hot_button_file(file_name[0])

            with open(file_name[0], 'r') as json_file:
                button_data = json.load(json_file)

            for button in range(self.ui.hotButtonHL.count()):
                self.hot_buttons[button].load(button_data)

    @Slot()
    def saveHotButtonsClicked(self):
        file_name = QFileDialog.getSaveFileName(self.ui, "Save Hot Buttons",
                    self._settings.get_config_dir(),
                    "Hot Buttons (*.hbt)")

        if len(file_name[0]) > 0:
            button_data = {}
            for button in range(self.ui.hotButtonHL.count()):
                self.hot_buttons[button].save(button_data)

            # Write the JSON string to a file. Since Button names could have special characters, encode
            with open(file_name[0], 'w', encoding='utf8') as json_file:
                json.dump(button_data, json_file, indent=2)
                json_file.close()

    @Slot()
    def selectPromosDirectory(self):
        setDir = QFileDialog.getExistingDirectory(self.ui,
                "Select the Promos Directory",
                self._settings.get_promos_directory(), QFileDialog.ShowDirsOnly)

        # If the user cancels then the filename will be blank and that is what will be stored as a flag to
        # not play any startup slides
        self._settings.set_promos_directory(setDir)

    @Slot()
    def startupImage(self):
        self._settings.set_startup_image(self.media_features.select_image_file())

    @Slot()
    def about(self):
        file = QFile(":/icons/about")
        if file.exists():
            if not file.open(QIODevice.ReadOnly | QIODevice.Text):
                return
            text = ""

            while not file.atEnd():
                text += file.readLine()

            QMessageBox.about(self.ui, "About ImproTron", text)

    # Camera Slots
    @Slot(QCameraDevice)
    def setCamera(self, cameraDevice):

        self.m_camera = QCamera(cameraDevice)
        self.m_captureSession.setCamera(self.m_camera)

        self.m_camera.activeChanged.connect(self.updateCameraActive)
        self.m_camera.errorOccurred.connect(self.displayCameraError)

        self.m_camera.stop()
        self.updateCameraActive(self.m_camera.isActive())

    @Slot()
    def startCamera(self):

        self.mediaPlayer.setVideoOutput(None)

        if self.ui.videoOnMainRB.isChecked():
            self.m_captureSession.setVideoOutput(self.mainDisplay.showCamera())
        elif self.ui.videoOnAuxRB.isChecked():
            self.m_captureSession.setVideoOutput(self.auxiliaryDisplay.showCamera())
        else:
            self.m_captureSession.setVideoOutput(self.mediaViewerVW)

        self.m_camera.start()

    @Slot()
    def stopCamera(self):
        self.m_camera.stop()
        if self.ui.videoOnMainRB.isChecked():
            self.mainDisplay.blackout()
        elif self.ui.videoOnAuxRB.isChecked():
            self.auxiliaryDisplay.blackout()

    @Slot(bool)
    def updateCameraActive(self, active):
        if active:
            self.ui.cameraStartPB.setEnabled(False)
            self.ui.cameraStopPB.setEnabled(True)
        else:
            self.ui.cameraStartPB.setEnabled(True)
            self.ui.cameraStopPB.setEnabled(False)

    @Slot(bool)
    def disableCameraControls(self):
        self.ui.cameraStartPB.setEnabled(False)
        self.ui.cameraStopPB.setEnabled(False)

    @Slot()
    def displayCameraError(self):
        if self.m_camera.error() != QCamera.NoError:
            QMessageBox.warning(self, "Camera Error",
                                self.m_camera.errorString())
            logger.warn(f"Camera Error {self.m_camera.errorString()}")

    @Slot(QListWidgetItem)
    def updateCameraDevice(self, camera):
        self.setCamera(camera.data(Qt.UserRole))

    @Slot()
    def updateCameras(self):
        self.ui.camerasLW.clear()

        available_cameras = self.m_devices.videoInputs()

        for cameraDevice in available_cameras:
            videoDeviceItem = QListWidgetItem(cameraDevice.description(),
                                          self.ui.camerasLW)
            videoDeviceItem.setData(Qt.UserRole, cameraDevice)
            if cameraDevice == self.m_devices.defaultVideoInput():
                videoDeviceItem.setSelected(True)

    # Respond to the request to change volume
    @Slot(int)
    def set_sound_volume(self, value):
        self.audioOutput.setVolume(value/self.ui.soundVolumeSL.maximum())

    # Touch Portal message handlers
    @Slot()
    def connectTouchPortal(self):
        self._settings.set_touch_portal_connect(self.ui.touchPortalConCB.isChecked()) # Remember for the next session
        if self.ui.touchPortalConCB.isChecked():
            self.touchPortalClient.connectTouchPortal()
        else:
            self.touchPortalClient.disconnectTouchPortal()

    # Handle a request to click a button
    @Slot(str)
    def onTouchPortalButtonAction(self, buttonID):
        button = utilities.findWidget(self.ui, QPushButton, buttonID)
        if button != None:
            button.click()
        else:
            logging.warning(f"QPushButton: {buttonID} not found")

    # Handle a request to increment or reset a QSpinbox like that used for scoring
    @Slot(str, int)
    def onTouchPortalSpinBoxAction(self, buttonID, changeValue):
        spinBox = utilities.findWidget(self.ui, QDoubleSpinBox, buttonID)
        if spinBox != None:
            if changeValue == 0:
                spinBox.setValue(0.0)
            else:
                spinBox.setValue(spinBox.value() + changeValue) # change can be positive or negative
        else:
            logging.warning(f"QDoubleSpinBox: {buttonID} not found")

    # Handle a request to display an image or animation
    @Slot(str, str)
    def onTouchPortalMediaAction(self, file, monitor):
        if monitor == "Main" or monitor == "Both":
            self.showMediaOnMain(file)

        if monitor == "Aux" or monitor == "Both":
            self.showMediaOnAux(file)

    # Handle a request to display an image or animation
    @Slot(str)
    def onTouchPortalSoundAction(self, file):
        if QFileInfo.exists(file):
            self.mediaPlayer.setSource(QUrl.fromLocalFile(file))
            self.mediaPlayer.setPosition(0)
            self.mediaPlayer.play()

    # YouTube Player support
    @Slot()
    def load_youtube(self):
        video_url = self.ui.youTubeLinkLE.text()
        try:
            # Extract VIDEO_ID from YouTube URL
            if "youtu.be" in video_url:
                video_id = video_url.split("/")[-1]
            elif "youtube.com/watch?v=" in video_url:
                video_id = video_url.split("v=")[-1].split("&")[0]
            else:
                video_id = video_url  # Assume it's already a VIDEO_ID

            # Build embed URL
            embed_url = f"https://www.youtube.com/embed/{video_id}?enablejsapi=1"
            if self.ui.videoOnMainRB.isChecked():
                self.mainDisplay.load_youtube(embed_url)
                self.main_preview.clear()
                self.main_preview.setStyleSheet("background:black; color:black")
            elif self.ui.videoOnAuxRB.isChecked():
                self.auxiliaryDisplay.load_youtube(embed_url)
                self.aux_preview.clear()
                self.aux_preview.setStyleSheet("background:black; color:black")
            else:
                QMessageBox.warning(self.ui, 'Preview', 'Youtube preview not supported.')

        except Exception:
            # Show an error message
            logging.warn(f"Unable to load video: {video_url}")

    @Slot()
    def play_youtube(self):
        if self.ui.videoOnMainRB.isChecked():
            self.mainDisplay.play_youtube()
        elif self.ui.videoOnAuxRB.isChecked():
            self.auxiliaryDisplay.play_youtube()
        else:
            QMessageBox.warning(self.ui, 'Preview', 'Youtube preview not supported.')

    @Slot()
    def mute_youtube(self):
        if self.ui.videoOnMainRB.isChecked():
            self.mainDisplay.mute_youtube()
        elif self.ui.videoOnAuxRB.isChecked():
            self.auxiliaryDisplay.mute_youtube()
        else:
            QMessageBox.warning(self.ui, 'Preview', 'Youtube preview not supported.')

    @Slot()
    def pause_youtube(self):
        if self.ui.videoOnMainRB.isChecked():
            self.mainDisplay.pause_youtube()
        elif self.ui.videoOnAuxRB.isChecked():
            self.auxiliaryDisplay.pause_youtube()
        else:
            QMessageBox.warning(self.ui, 'Preview', 'Youtube preview not supported.')
