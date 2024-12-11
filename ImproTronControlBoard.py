# This Python file uses the following encoding: utf-8
import json
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import (QImageReader, QPixmap, QMovie, QColor, QGuiApplication, QImage, QStandardItemModel,
                                QStandardItem, QFont, QFontMetrics)
from PySide6.QtWidgets import (QColorDialog, QFileDialog, QFileSystemModel, QMessageBox, QWidget,
                                QApplication, QPushButton, QDoubleSpinBox, QStyle, QListWidgetItem, QSizePolicy)
from PySide6.QtCore import (QObject, QStandardPaths, Slot, Signal, Qt, QTimer, QItemSelection, QFileInfo, QDir,
                                QFile, QIODevice, QEvent, QUrl, QDirIterator, QRandomGenerator,
                                QPoint, QRegularExpression, QSize, QModelIndex, QThread)
from PySide6.QtMultimedia import (QAudioInput, QCamera, QCameraDevice,
                                    QImageCapture, QMediaCaptureSession,
                                    QMediaDevices, QMediaMetaData,
                                    QMediaRecorder, QMediaPlayer, QAudioOutput)
from PySide6.QtNetwork import QTcpSocket

from PySide6.QtMultimediaWidgets import QVideoWidget

from Settings import Settings
from Improtronics import ImproTron, SlideWidget, HotButton, SlideLoaderThread

from games_feature import GamesFeature
from text_feature import TextFeature
from media_features import MediaFeatures
from thingz_feature import ThingzFeature
import utilities
from TouchPortal import TouchPortal
import ImproTronIcons

class ImproTronControlBoard(QWidget):
    slideLoadSignal = Signal(str)
    def __init__(self, parent=None):
        super(ImproTronControlBoard,self).__init__()
        self._settings = Settings()

        loader = QUiLoader()
        self.ui = loader.load("ImproTronControlPanel.ui")

        # MediaPlayer and audio setup for movies, webcams, and sound
        self.mediaPlayer = QMediaPlayer()
        self.audioOutput = QAudioOutput()
        self.mediaPlayer.setAudioOutput(self.audioOutput)
        self.audioOutput.setVolume(self.ui.soundVolumeSL.value()/self.ui.soundVolumeSL.maximum())
        self.m_devices = QMediaDevices()
        self.m_devices.videoInputsChanged.connect(self.updateCameras)
        self.updateCameras()
        self.videoFile = None

        self.m_captureSession = QMediaCaptureSession()
        self.setCamera(QMediaDevices.defaultVideoInput())

        # QMovies for displaying GIF previews. Avoids memory leaks by keeping them around
        self.mainPreviewMovie = QMovie()
        self.mainPreviewMovie.setSpeed(100)
        self.auxPreviewMovie = QMovie()
        self.auxPreviewMovie.setSpeed(100)

        # Create Screens and relocate. Main done second so it is on top
        self.mainDisplay = ImproTron("Main")
        self.auxiliaryDisplay = ImproTron("Auxiliary")

        self.auxiliaryDisplay.restore()
        self.auxiliaryDisplay.setLocation(self._settings.getAuxLocation())
        self.auxiliaryDisplay.maximize()

        self.mainDisplay.restore()
        self.mainDisplay.setLocation(self._settings.getMainLocation())
        self.mainDisplay.maximize()

        # Instantiate Features
        self.games_feature = GamesFeature(self.ui, self._settings, self.mainDisplay, self.auxiliaryDisplay)
        self.text_feature = TextFeature(self.ui, self._settings, self.mainDisplay, self.auxiliaryDisplay)
        self.thingz_feature = ThingzFeature(self.ui, self._settings, self.mainDisplay, self.auxiliaryDisplay)
        self.media_features = MediaFeatures(self.ui, self._settings, self.mediaPlayer)

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

        self.setLeftTeamColors(self._settings.getLeftTeamColor())
        self.setRightTeamColors(self._settings.getRightTeamColor())
        self.ui.teamNameLeft.setText(self._settings.getLeftTeamName())
        self.ui.teamNameRight.setText(self._settings.getRightTeamName())

        # Quick Add Buttons for score updates.
        self.ui.add50PB.clicked.connect(self.quickAdd50) # Add 5 to Left team
        self.ui.add32PB.clicked.connect(self.quickAdd32) # Add 3 to Left, 2 to Right
        self.ui.add23PB.clicked.connect(self.quickAdd23) # Add 2 to Left, 3 to Right
        self.ui.add05PB.clicked.connect(self.quickAdd05) # Add 5 to Right team

        # Image load, paste and blackout
        self.ui.loadImageMainPB.clicked.connect(self.getImageFileMain)
        self.ui.loadImageAuxiliaryPB.clicked.connect(self.getImageFileAuxiliary)
        self.ui.pasteImageMainPB.clicked.connect(self.pasteImageMain)
        self.ui.pasteImageAuxiliaryPB.clicked.connect(self.pasteImageAuxiliary)
        self.ui.blackoutMainPB.clicked.connect(self.blackout_main)
        self.ui.blackoutAuxPB.clicked.connect(self.blackout_aux)
        self.ui.blackoutBothPB.clicked.connect(self.blackout_both)

        # Countdown timer controls
        self.ui.startTimerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.startTimerPB.clicked.connect(self.startTimer)

        self.ui.resetTimerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.ui.resetTimerPB.clicked.connect(self.resetTimer)

        self.ui.pauseTimerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.pauseTimerPB.clicked.connect(self.pauseTimerPB)

        self.ui.timerVisibleMainCB.stateChanged.connect(self.timerVisibleMain)

        # Slide Show Management
        self.mediaModel = QFileSystemModel()
        self.mediaModel.setRootPath(self._settings.getMediaDir())

        self.imageTreeView = self.ui.slideShowFilesTreeView
        self.imageTreeView.setModel(self.mediaModel)
        self.imageTreeView.setRootIndex(self.mediaModel.index(self._settings.getMediaDir()))
        for i in range(1, self.mediaModel.columnCount()):
            self.imageTreeView.header().hideSection(i)
        self.imageTreeView.setHeaderHidden(True)

        # Selection changes will trigger a slot
        selectionModel = self.imageTreeView.selectionModel()
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
        self.ui.slideShowSecondSB.setValue(self._settings.getSlideshowDelay())
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
        self.ui.touchPortalConCB. checkStateChanged.connect(self.connectTouchPortal)
        tpFlag = self._settings.getTouchPortalConnect()
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
        self.showMediaOnMain(self._settings.getStartupImage())
        self.showMediaOnAux(self._settings.getStartupImage())
        # Force the default feature tab on start up to the Text Display
        self.ui.featureTabs.setCurrentWidget(self.ui.textDisplayTab)

        # Then override with the promos if the promo directory has been set up
        _promosDirectory = self._settings.getPromosDirectory()
        if len(_promosDirectory) >0:
            self.ui.featureTabs.setCurrentWidget(self.ui.slideShowTab)
            self.startPromosSlideShow()

            # Force the default feature tab on start up to the Slide Show to make it quicker to stop for the show.
            self.ui.featureTabs.setCurrentWidget(self.ui.slideShowTab)


            # Hot Buttons Wiring
            self.hot_buttons = [] #empty array
            self.hotButtonNumber = 10      #number of hotbuttons

            for button in range(self.hotButtonNumber):
                self.hot_buttons.append(HotButton(button+1, self))

            # Load the last saved hotbutton file
            lastHotButtons = self._settings.getLastHotButtonFile()
            if lastHotButtons != None:
                with open(lastHotButtons, 'r') as json_file:
                    button_data = json.load(json_file)

                for button in range(self.hotButtonNumber):
                    self.hot_buttons[button].load(button_data)

            # Set a slot for the clear, load and save buttons
            self.ui.hotButtonClearPB.clicked.connect(self.clearHotButtonsClicked)
            self.ui.hotButtonLoadPB.clicked.connect(self.loadHotButtonsClicked)
            self.ui.hotButtonSavePB.clicked.connect(self.saveHotButtonsClicked)

        # Set up an event filter to handle the orderly shutdown of the app.
        self.ui.installEventFilter(self)

        # Set up the chrome of the control board
        self.ui.setWindowFlags(
            Qt.Window |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint |
            Qt.WindowTitleHint
            )

        # Let the fun begin!
        self.ui.show()
# ################################################################################################
# ####################### Slots and more

    def eventFilter(self, obj, event):
        if obj is self.ui and event.type() == QEvent.Close:
            self._settings.save()
            self.shutdown()
            event.ignore()
            return True
        return super(ImproTronControlBoard, self).eventFilter(obj, event)

    def shutdown(self):
        # Delete feature obejcts to hopefully avoid the app staying open if they trigger a crash
        del self.games_feature
        del self.text_feature
        del self.thingz_feature
        del self.media_features

        self.touchPortalClient.disconnectTouchPortal()
        self.thread.quit()
        self.ui.removeEventFilter(self)
        QApplication.quit()

    # Utility encapsulating the ui code to find widgets by name
    def findWidget(self, type, widgetName):
        return self.ui.findChild(type, widgetName)


    def selectVideoFile(self):
        selectedFileName = QFileDialog.getOpenFileName(self.ui, "Select Video", self._settings.getVideoDir() , "Video Files (*.mp4 *.m4v *.mp4v *.wmv)")

        return selectedFileName[0]

    # Checks on various media types
    def isAnimatedGIF(self, fileName):
        if len(fileName) > 0:
            if QFileInfo.exists(fileName):
                mediaInfo = QFileInfo(fileName)
                return bytes(mediaInfo.suffix().lower(),"ascii") in QMovie.supportedFormats()
            else:
                return False
        else:
            return False

    def isVideo(self, fileName):
        if len(fileName) > 0:
            if QFileInfo.exists(fileName):
                mediaInfo = QFileInfo(fileName)
                return mediaInfo.suffix().lower() in  ['mp4', 'm4v', 'mp4v', 'wmv']
            else:
                return False
        else:
            return False

    # Note: This is both a local call but a slot for images emitted from the media features
    @Slot(str)
    def showMediaOnMain(self, fileName):
        self.mainPreviewMovie.stop()
        if self.isAnimatedGIF(fileName):
            self.mainPreviewMovie.setFileName(fileName)
            if self.mainPreviewMovie.isValid():
                self.mainPreviewMovie.setScaledSize(self.ui.imagePreviewMain.size())
                self.ui.imagePreviewMain.setMovie(self.mainPreviewMovie)
                self.mainPreviewMovie.start()
                self.mainDisplay.showMovie(fileName)
        elif self.media_features.isImage(fileName):
            reader = QImageReader(fileName)
            reader.setAutoTransform(True)
            newImage = reader.read()
            if newImage:
                if self.ui.stretchMainCB.isChecked():
                    self.ui.imagePreviewMain.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.imagePreviewMain.size())))
                else:
                    self.ui.imagePreviewMain.setPixmap(QPixmap.fromImage(newImage.scaledToHeight(self.ui.imagePreviewMain.size().height())))

            self.mainDisplay.showImage(fileName, self.ui.stretchMainCB.isChecked())
        else:
            print("Unsupported media for main:", fileName)

    # Note: This is both a local call but a slot for images emitted from the media features
    @Slot(str)
    def showMediaOnAux(self, fileName):
        self.auxPreviewMovie.stop()
        if self.isAnimatedGIF(fileName):
            self.auxPreviewMovie.setFileName(fileName)
            if self.auxPreviewMovie.isValid():
                self.auxPreviewMovie.setScaledSize(self.ui.imagePreviewAuxiliary.size())
                self.ui.imagePreviewAuxiliary.setMovie(self.auxPreviewMovie)
                self.auxPreviewMovie.start()
                self.auxiliaryDisplay.showMovie(fileName)
        elif self.media_features.isImage(fileName):
            reader = QImageReader(fileName)
            reader.setAutoTransform(True)
            newImage = reader.read()
            if newImage:
                if self.ui.stretchAuxCB.isChecked():
                    self.ui.imagePreviewAuxiliary.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.imagePreviewAuxiliary.size())))
                else:
                    self.ui.imagePreviewAuxiliary.setPixmap(QPixmap.fromImage(newImage.scaledToHeight(self.ui.imagePreviewAuxiliary.size().height())))

                self.auxiliaryDisplay.showImage(fileName, self.ui.stretchAuxCB.isChecked())
        else:
            print("Unsupported media on aux:", fileName)

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
        colorSelected = QColorDialog.getColor(self._settings.getLeftTeamColor(), self.ui,title = 'Pick Left Team Color')
        if colorSelected.isValid():
            self._settings.setLeftTeamColor(colorSelected)
            self.setLeftTeamColors(colorSelected)

    @Slot()
    def pickRightTeamColor(self):
        colorSelected = QColorDialog.getColor(self._settings.getRightTeamColor(), self.ui,title = 'Pick Right Team Color')
        if colorSelected.isValid():
            self._settings.setRightTeamColor(colorSelected)
            self.setRightTeamColors(colorSelected)

    @Slot()
    def blackout_both(self):
        self.blackout_main()
        self.blackout_aux()

    @Slot()
    def blackout_main(self):
        self.ui.imagePreviewMain.clear()
        self.ui.imagePreviewMain.setStyleSheet("background:black; color:black")
        self.mainDisplay.blackout()

    @Slot()
    def blackout_aux(self):
        self.ui.imagePreviewAuxiliary.clear()
        self.ui.imagePreviewAuxiliary.setStyleSheet("background:black; color:black")
        self.auxiliaryDisplay.blackout()

    @Slot()
    def pasteImageMain(self):
        pixmap = QGuiApplication.clipboard().pixmap()
        if pixmap != None:
            if self.ui.stretchMainCB.isChecked():
                self.ui.imagePreviewMain.setPixmap(pixmap.scaled(self.ui.imagePreviewMain.size()))
            else:
                self.ui.imagePreviewMain.setPixmap(pixmap.scaledToHeight(self.ui.imagePreviewMain.size().height()))

            self.mainDisplay.pasteImage(self.ui.stretchMainCB.isChecked())

    @Slot()
    def pasteImageAuxiliary(self):
        pixmap = QGuiApplication.clipboard().pixmap()
        if pixmap != None:
            if self.ui.stretchAuxCB.isChecked():
                self.ui.imagePreviewAuxiliary.setPixmap(pixmap.scaled(self.ui.imagePreviewAuxiliary.size()))
            else:
                self.ui.imagePreviewAuxiliary.setPixmap(pixmap.scaledToHeight(self.ui.imagePreviewAuxiliary.size().height()))

            self.auxiliaryDisplay.pasteImage(self.ui.stretchAuxCB.isChecked())

    @Slot()
    def getImageFileMain(self):
        self.showMediaOnMain(self.media_features.selectImageFile())

    @Slot()
    def getImageFileAuxiliary(self):
        self.showMediaOnAux(self.media_features.selectImageFile())

    @Slot()
    def getVideoFile(self):
        self.videoFile = self.selectVideoFile()
        if self.isVideo(self.videoFile):
            self.mediaPlayer.setSource(QUrl(self.videoFile))
        else:
            print("Unsupported Video File selected:",self.videoFile)

    @Slot()
    def showScoresMain(self):
        self.mainDisplay.updateScores(self.ui.teamScoreLeft.value(),self.ui.teamScoreRight.value())

    @Slot()
    def showScoresAuxiliary(self):
        self.auxiliaryDisplay.updateScores(self.ui.teamScoreLeft.value(),self.ui.teamScoreRight.value())

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
        self._settings.setLeftTeamName(teamName)

    @Slot(str)
    def showRightTeam(self, teamName):
        self.mainDisplay.showRightTeam(teamName)
        self.auxiliaryDisplay.showRightTeam(teamName)
        self.ui.rightThingTeamRB.setText(teamName)
        self._settings.setRightTeamName(teamName)

    # Unlock the Improtron Displays so they can be moved. Lock them to maximize
    # on th screen they subsequently reside on.
    def improtronUnlock(self):
        if self.ui.improtronUnlockPB.isChecked():
            self.auxiliaryDisplay.restore()
            self.mainDisplay.restore()
        else:
            self._settings.setAuxLocation(self.auxiliaryDisplay.getLocation())
            self._settings.setMainLocation(self.mainDisplay.getLocation())
            self._settings.save()

            # Order matters so the main displays on top
            self.auxiliaryDisplay.maximize()
            self.mainDisplay.maximize()

    # Slideshow Management
    @Slot(int)
    def slideShowSecondChanged(self, value):
        self._settings.setSlideshowDelay(value)

    @Slot(QItemSelection, QItemSelection)
    def imageSelectedfromDir(self, new_selection, old_selection):
        # get the text of the selected item
        index = self.imageTreeView.selectionModel().currentIndex()
        if not self.mediaModel.isDir(index):
            imageFileInfo = self.mediaModel.fileInfo(index)
            reader = QImageReader(imageFileInfo.absoluteFilePath())
            reader.setAutoTransform(True)
            newImage = reader.read()

            # Scale to match the preview
            self.ui.slidePreviewLBL.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.slidePreviewLBL.size())))

    @Slot(SlideWidget)
    def previewSelectedSlide(self, slide):
        reader = QImageReader(slide.imagePath())
        reader.setAutoTransform(True)
        newImage = reader.read()

        # Scale to match the preview
        self.ui.slidePreviewLBL.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.slidePreviewLBL.size())))


    @Slot()
    def addSlidetoList(self):
        # get the text of the selected item
        index = self.imageTreeView.selectionModel().currentIndex()
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

    def loadSlides(self, fileName):
        # Read the JSON data from the file
        if len(fileName) > 0:
            with open(fileName, 'r') as json_file:
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

        fileName = QFileDialog.getOpenFileName(self.ui, "Load Slideshow",
                                    self._settings.getConfigDir(),
                                    "Slide Shows (*.ssh)")

        self.loadSlides(fileName[0])

    @Slot()
    def saveSlideShow(self):
        fileName = QFileDialog.getSaveFileName(self.ui, "Save Slide Show",
                                   self._settings.getConfigDir(),
                                   "Slide Shows (*.ssh)")
        if len(fileName[0]) > 0:
            slide_data = {}
            for slide in range(self.ui.slideListLW.count()):
                slideName = "slide"+str(slide)
                slide_data[slideName] = self.ui.slideListLW.item(slide).imagePath()

            # Write the JSON string to a file
            with open(fileName[0], 'w', encoding='utf8') as json_file:
                json.dump(slide_data, json_file, indent=2)

    @Slot()
    def clearSlideShow(self):
        reply = QMessageBox.question(self.ui, 'Clear Slides', 'Are you sure you want clear all slides?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.slideListLW.clear()

    # Promos specific behaviour
    def loadPromosSlides(self):
        _promosDirectory = self._settings.getPromosDirectory()
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
        self.slideShowTimer.setInterval(self._settings.getSlideshowDelay()*1000)

        # Resample the promos directory once the current cycle is done
        if self.promosMode and self.currentSlide == 0:
            self.loadPromosSlides()

        # Progress the slide show if there are now slides to show in the list
        slideCount = self.ui.slideListLW.count()
        if slideCount > 0:
            self.currentSlide = self.currentSlide % slideCount
            self.ui.slideListLW.setCurrentRow(self.currentSlide)

            # Determine the file type so as to correcty set the timeout to the default or video length
            fileName = self.ui.slideListLW.currentItem().imagePath()
            if self.isAnimatedGIF(fileName) or self.media_features.isImage(fileName):
                self.showSlideMain()
            elif self.isVideo(fileName):
                self.slideShowTimer.setInterval(1000)
                self.mediaPlayer.setSource(QUrl(fileName))
                self.mediaPlayer.setVideoOutput(self.mainDisplay.showVideo())
                self.mediaPlayer.setPosition(0)
                self.mediaPlayer.play()

            else:
                print("Unsupported Media Type:",fileName)

            self.currentSlide += 1 # Move onto the next slide

        else:
            self.currentSlide = 0
            print("Missing Slides:",self.currentSlide)

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

        #self.slideShowTimer.setInterval(self._settings.getSlideshowDelay()*1000)
        # A short delay to allow th timer to tigger and the the length to be drtmied by the media type to be shown
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
                self.ui.imagePreviewMain.setPixmap(QPixmap.fromImage(image.scaled(self.ui.imagePreviewMain.size())))
            else:
                self.ui.imagePreviewMain.setPixmap(QPixmap.fromImage(image.scaledToHeight(self.ui.imagePreviewMain.size().height())))

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

    # Slide Timer interval setting for videos: QMediaPlayer does not have the duration available on load
    # but does so when playing commences. If the slide timer is active this slot changes the interval to match
    @Slot(int)
    def updateDuration(self, duration):
        if self.slideShowTimer.isActive():
            self.slideShowTimer.setInterval(duration + 100) # Add a little buffer

    # Preferences and Hot Buttons configuration settings
    @Slot()
    def clearHotButtonsClicked(self):
        for button in range(self.hotButtonNumber):
            self.hot_buttons[button].clear()

    @Slot()
    def loadHotButtonsClicked(self):
        fileName = QFileDialog.getOpenFileName(self.ui, "Load Hot Buttons",
                    self._settings.getConfigDir(),
                    "Hot Buttons (*.hbt)")

        # Read the JSON data from the file
        if len(fileName[0]) > 0:

            # Remember the last loaded hotbutton file for when the app is started
            self._settings.setLastHotButtonFile(fileName[0])

            with open(fileName[0], 'r') as json_file:
                button_data = json.load(json_file)

            for button in range(self.hotButtonNumber):
                self.hot_buttons[button].load(button_data)

    @Slot()
    def saveHotButtonsClicked(self):
        fileName = QFileDialog.getSaveFileName(self.ui, "Save Hot Buttons",
                    self._settings.getConfigDir(),
                    "Hot Buttons (*.hbt)")

        if len(fileName[0]) > 0:
            button_data = {}
            for button in range(self.hotButtonNumber):
                self.hot_buttons[button].save(button_data)

            # Write the JSON string to a file. Since Button names could have special characters, encode
            with open(fileName[0], 'w', encoding='utf8') as json_file:
                json.dump(button_data, json_file, indent=2)

    @Slot()
    def selectPromosDirectory(self):
        setDir = QFileDialog.getExistingDirectory(self.ui,
                "Select the Promos Directory",
                self._settings.getPromosDirectory(), QFileDialog.ShowDirsOnly)

        # If the user cancels then the filename will be blank and that is what will be stored as a flag to
        # not play any startup slides
        self._settings.setPromosDirectory(setDir)

    @Slot()
    def startupImage(self):
        self._settings.setStartupImage(self.media_features.selectImageFile())

    @Slot()
    def about(self):
        file = QFile(":/icons/about")

        if file.exists():
            if not file.open(QIODevice.ReadOnly | QIODevice.Text):
                return
            text = ""

            while not file.atEnd():
                text += file.readLine()

            msgBox = QMessageBox()
            msgBox.setText(text)
            msgBox.setWindowTitle("About ImproTron")
            msgBox.exec()

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
            self.ui.cameraSettingsPB.setEnabled(True)
        else:
            self.ui.cameraStartPB.setEnabled(True)
            self.ui.cameraStopPB.setEnabled(False)
            self.ui.cameraSettingsPB.setEnabled(False)

    @Slot(bool)
    def disableCameraControls(self):
        self.ui.cameraStartPB.setEnabled(False)
        self.ui.cameraStopPB.setEnabled(False)
        self.ui.cameraSettingsPB.setEnabled(False)

    @Slot()
    def displayCameraError(self):
        if self.m_camera.error() != QCamera.NoError:
            QMessageBox.warning(self, "Camera Error",
                                self.m_camera.errorString())

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
        self._settings.setTouchPortalConnect(self.ui.touchPortalConCB.isChecked()) # Remember for the next session
        if self.ui.touchPortalConCB.isChecked():
            self.touchPortalClient.connectTouchPortal()
        else:
            self.touchPortalClient.disconnectTouchPortal()

    # Handle a request to click a button
    @Slot(str)
    def onTouchPortalButtonAction(self, buttonID):
        button = self.findWidget(QPushButton, buttonID)
        if button != None:
            button.click()
        else:
            print(f"QPushButton: {buttonID} not found")

    # Handle a request to increment or reset a QSpinbox like that used for scoring
    @Slot(str, int)
    def onTouchPortalSpinBoxAction(self, buttonID, changeValue):
        spinBox = self.findWidget(QDoubleSpinBox, buttonID)
        if spinBox != None:
            if changeValue == 0:
                spinBox.setValue(0.0)
            else:
                spinBox.setValue(spinBox.value() + changeValue) # change can be positive or negative
        else:
            print(f"QDoubleSpinBox: {buttonID} not found")

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
