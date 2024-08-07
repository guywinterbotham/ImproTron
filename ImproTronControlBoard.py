# This Python file uses the following encoding: utf-8
import json
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QImageReader, QPixmap, QMovie, QColor, QGuiApplication, QImage
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
from Improtronics import ImproTron, ThingzWidget, SlideWidget, SoundFX, HotButton, SlideLoaderThread

from MediaFileDatabase import MediaFileDatabase
from TouchPortal import TouchPortal
import ImproTronIcons

class ImproTronControlBoard(QWidget):
    slideLoadSignal = Signal(str)
    def __init__(self, parent=None):
        super(ImproTronControlBoard,self).__init__()
        self._settings = Settings()

        self.mainDisplay = ImproTron("Main")
        self.auxiliaryDisplay = ImproTron("Auxiliary")

        loader = QUiLoader()
        self.ui = loader.load("ImproTronControlPanel.ui")

        # Relocate the Screens
        self.auxiliaryDisplay.restore()
        self.auxiliaryDisplay.setLocation(self._settings.getAuxLocation())
        self.auxiliaryDisplay.maximize()

        self.mainDisplay.restore()
        self.mainDisplay.setLocation(self._settings.getMainLocation())
        self.mainDisplay.maximize()

        # QMovies for displaying GIF previews. Avoids memory leaks by keeping them around
        self.mainPreviewMovie = QMovie()
        self.mainPreviewMovie.setSpeed(100)
        self.auxPreviewMovie = QMovie()
        self.auxPreviewMovie.setSpeed(100)
        self.searchPreviewMovie = QMovie()
        self.searchPreviewMovie.setSpeed(100)

        # Camera Configuration
        # Wire camera controls
        self.ui.cameraStartPB.clicked.connect(self.startCamera)
        self.ui.cameraStopPB.clicked.connect(self.stopCamera)

        # Fetch and configure camera devices
        self.ui.camerasLW.itemClicked.connect(self.updateCameraDevice)

        self.mediaPlayer = QMediaPlayer()

        self.videoFile = None

        self.audioOutput = QAudioOutput()
        self.mediaPlayer.setAudioOutput(self.audioOutput)
        self.audioOutput.setVolume(self.ui.soundVolumeSL.value()/self.ui.soundVolumeSL.maximum())
        self.m_devices = QMediaDevices()
        self.m_devices.videoInputsChanged.connect(self.updateCameras)
        self.updateCameras()

        self.m_captureSession = QMediaCaptureSession()
        self.setCamera(QMediaDevices.defaultVideoInput())

        # In memory database configuration
        self.mediaFileDatabase = MediaFileDatabase()
        mediaCount = self.mediaFileDatabase.indexMedia(self._settings.getMediaDir())
        self.ui.mediaFilesCountLBL.setText(str(mediaCount))

        self.mediaModel = QFileSystemModel()
        self.mediaModel.setRootPath(self._settings.getMediaDir())

        # Sound Setup
        soundCount = self.mediaFileDatabase.indexSounds(self._settings.getSoundDir())
        self.ui.soundFilesCountLBL.setText(str(soundCount))

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

        # Connect info (text and images) message updates
        self.ui.showLeftTextMainPB.clicked.connect(self.showLeftTextMain)
        self.ui.showLeftTextAuxiliaryPB.clicked.connect(self.showLeftTextAuxiliary)
        self.ui.showLeftTextBothPB.clicked.connect(self.showLeftTextBoth)
        self.ui.showRightTextMainPB.clicked.connect(self.showRightTextMain)
        self.ui.showRightTextAuxiliaryPB.clicked.connect(self.showRightTextAuxiliary)
        self.ui.showRightTextBothPB.clicked.connect(self.showRightTextBoth)

        self.ui.clearLeftTextPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowLeft))
        self.ui.clearLeftTextPB.clicked.connect(self.clearLeftText)
        self.ui.clearRightTextPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        self.ui.clearRightTextPB.clicked.connect(self.clearRightText)

        self.ui.loadTextboxLeftPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowLeft))
        self.ui.loadTextboxLeftPB.clicked.connect(self.loadTextboxLeft)
        self.ui.loadTextboxRightPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        self.ui.loadTextboxRightPB.clicked.connect(self.loadTextboxRight)

        self.ui.loadImageMainPB.clicked.connect(self.getImageFileMain)
        self.ui.loadImageAuxiliaryPB.clicked.connect(self.getImageFileAuxiliary)
        self.ui.pasteImageMainPB.clicked.connect(self.pasteImageMain)
        self.ui.pasteImageAuxiliaryPB.clicked.connect(self.pasteImageAuxiliary)

        # Ininialize preset color boxes from dialog custom colors.
        self.setPresetColors()
        self.ui.leftColorPreset1.clicked.connect(self.useLeftColorPreset1)
        self.ui.leftColorPreset2.clicked.connect(self.useLeftColorPreset2)
        self.ui.leftColorPreset3.clicked.connect(self.useLeftColorPreset3)
        self.ui.leftColorPreset4.clicked.connect(self.useLeftColorPreset4)
        self.ui.leftColorPreset5.clicked.connect(self.useLeftColorPreset5)
        self.ui.leftColorPreset6.clicked.connect(self.useLeftColorPreset6)
        self.ui.leftColorPreset7.clicked.connect(self.useLeftColorPreset7)
        self.ui.leftColorPreset8.clicked.connect(self.useLeftColorPreset8)

        self.ui.rightColorPreset1.clicked.connect(self.useRightColorPreset1)
        self.ui.rightColorPreset2.clicked.connect(self.useRightColorPreset2)
        self.ui.rightColorPreset3.clicked.connect(self.useRightColorPreset3)
        self.ui.rightColorPreset4.clicked.connect(self.useRightColorPreset4)
        self.ui.rightColorPreset5.clicked.connect(self.useRightColorPreset5)
        self.ui.rightColorPreset6.clicked.connect(self.useRightColorPreset6)
        self.ui.rightColorPreset7.clicked.connect(self.useRightColorPreset7)
        self.ui.rightColorPreset8.clicked.connect(self.useRightColorPreset8)

        # Connect Show Text Config elements
        self.ui.rightTextColorPB.clicked.connect(self.pickRightTextColor)
        self.ui.leftTextColorPB.clicked.connect(self.pickLeftTextColor)
        self.ui.blackoutMainPB.clicked.connect(self.blackoutMain)
        self.ui.blackoutAuxPB.clicked.connect(self.blackoutAux)
        self.ui.blackoutBothPB.clicked.connect(self.blackoutBoth)

        # Countdown timer controls
        self.ui.startTimerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.startTimerPB.clicked.connect(self.startTimer)

        self.ui.resetTimerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.ui.resetTimerPB.clicked.connect(self.resetTimer)

        self.ui.pauseTimerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.pauseTimerPB.clicked.connect(self.pauseTimerPB)

        self.ui.timerVisibleMainCB.stateChanged.connect(self.timerVisibleMain)

        # Connect Thingz Management
        self.ui.thingzListLW.itemClicked.connect(self.showSelectedThing)
        self.ui.thingzListLW.itemChanged.connect(self.titleEdited)

        self.ui.addThingPB.clicked.connect(self.addThingtoList)
        self.ui.toggleTeamPB.clicked.connect(self.toggleTeam)

        self.ui.thingNameTxt.returnPressed.connect(self.addThingtoList)

        self.ui.removeThingPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton))
        self.ui.removeThingPB.clicked.connect(self.removeThingfromList)

        self.ui.clearThingzPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogDiscardButton))
        self.ui.clearThingzPB.clicked.connect(self.clearThingzList)

        self.ui.thingzMoveUpPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))
        self.ui.thingzMoveUpPB.clicked.connect(self.thingzMoveUp)

        self.ui.thingzMoveDownPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))
        self.ui.thingzMoveDownPB.clicked.connect(self.thingzMoveDown)

        self.ui.thingTextEdit.textChanged.connect(self.updateThingsText)
        self.ui.showThingMainPB.clicked.connect(self.showThingMain)
        self.ui.showThingAuxiliaryPB.clicked.connect(self.showThingAuxiliary)
        self.ui.showThingBothPB.clicked.connect(self.showThingBoth)
        self.ui.showThingzMainPB.clicked.connect(self.showThingzListMain)
        self.ui.showThingzAuxiliaryPB.clicked.connect(self.showThingzListAuxiliary)
        self.ui.showThingzBothPB.clicked.connect(self.showThingzListBoth)

        # Slide Show Management
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

        # Image Search Connections
        self.ui.searchMediaPB.clicked.connect(self.searchMedia)
        self.ui.mediaSearchTagsLE.returnPressed.connect(self.searchMedia)
        self.ui.mediaSearchResultsLW.itemClicked.connect(self.previewSelectedMedia)
        self.ui.setMediaLibraryPB.clicked.connect(self.setMediaLibrary)

        self.ui.mediaSearchResultsLW.itemDoubleClicked.connect(self.showMediaPreviewMain)
        self.ui.searchToMainShowPB.clicked.connect(self.searchToMainShow)
        self.ui.searchToAuxShowPB.clicked.connect(self.searchToAuxShow)
        self.ui.searchtoSlideShowPB.clicked.connect(self.searchtoSlideShow)

        # Sound Search Connections
        self.ui.searchSoundsPB.clicked.connect(self.searchSounds)
        self.ui.soundSearchTagsLE.returnPressed.connect(self.searchSounds)
        self.ui.setSoundLibraryPB.clicked.connect(self.setSoundLibrary)

        self.ui.soundPlayPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.ui.soundPlayPB.clicked.connect(self.soundPlay)

        self.ui.soundPausePB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPause))
        self.ui.soundPausePB.clicked.connect(self.soundPause)

        self.ui.soundStopPB.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaStop))
        self.ui.soundStopPB.clicked.connect(self.soundStop)

        self.ui.soundLoopPB.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        self.ui.soundLoopPB.clicked.connect(self.soundLoop)

        self.ui.soundVolumeSL.valueChanged.connect(self.setSoundVolume)
        #self.mediaPlayer.errorOccurred.connect(self.playerError)

        self.ui.loadSoundQueuePB.clicked.connect(self.loadSoundQueue)
        self.ui.saveSoundQueuePB.clicked.connect(self.saveSoundQueue)
        self.ui.saveSoundFXPallettePB.clicked.connect(self.saveSoundFXPallette)
        self.ui.clearSoundQueuePB.clicked.connect(self.clearSoundQueue)
        self.ui.soundFXVolumeHS.valueChanged.connect(self.setFXVolume)

        self.ui.soundMoveUpPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))
        self.ui.soundMoveUpPB.clicked.connect(self.soundMoveUp)

        self.ui.soundMoveDownPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))
        self.ui.soundMoveDownPB.clicked.connect(self.soundMoveDown)

        self.ui.soundAddToListPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        self.ui.soundAddToListPB.clicked.connect(self.soundAddToList)

        self.ui.soundRemoveFromListPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowBack))
        self.ui.soundRemoveFromListPB.clicked.connect(self.soundRemoveFromList)

        # Sound Pallette Wiring
        self.sfx_buttons = [] #empty array
        self.soundFXNumber = 25      #number of soundeffects for a pallette

        _volume = self.ui.soundFXVolumeHS.value()/self.ui.soundFXVolumeHS.maximum()
        for button in range(self.soundFXNumber):
            sfx_button = self.ui.findChild(QPushButton, "soundFXPB" +str(button+1))
            _soundFX = SoundFX(sfx_button)
            _soundFX.setFXVolume(_volume)
            self.sfx_buttons.append(_soundFX)

        # Set a slot for the clear, load and save buttons
        self.palletteSelect = self.ui.soundPalettesCB
        self.palletteSelect.currentIndexChanged.connect(self.loadSoundEffects)

        self.loadSoundPallettes()

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
        self.touchPortalClient.disconnectTouchPortal()
        self.thread.quit()
        self.ui.removeEventFilter(self)
        QApplication.quit()

    # Utility encapsulating the ui code to find widgets by name
    def findWidget(self, type, widgetName):
        return self.ui.findChild(type, widgetName)

    # Populate the preset color buttons with the presets defined in the color dialog
    def setPresetColors(self):
        leftPresets = QRegularExpression('leftColorPreset')
        rightPresets = QRegularExpression('rightColorPreset')

        # Use the index provided by the QColorDialog. Cap at the max number of buttons
        maxColorPresets = QColorDialog.customCount()

        colorIndex = 0
        for colorButton in self.ui.textDisplayTab.findChildren(QPushButton, leftPresets):
            if colorIndex < maxColorPresets:
                colorButton.setStyleSheet(self.styleSheet(QColorDialog.customColor(colorIndex)))

            colorIndex += 1

        colorIndex = 0
        for colorButton in self.ui.textDisplayTab.findChildren(QPushButton, rightPresets):
            if colorIndex < maxColorPresets:
                colorButton.setStyleSheet(self.styleSheet(QColorDialog.customColor(colorIndex)))

            colorIndex += 1


    def selectImageFile(self):
        selectedFileName = QFileDialog.getOpenFileName(self.ui, "Select Media", self._settings.getMediaDir() , "Media Files (*.png *.jpg *.bmp *.gif *.webp)")

        return selectedFileName[0]

    def selectVideoFile(self):
        selectedFileName = QFileDialog.getOpenFileName(self.ui, "Select Video", self._settings.getVideoDir() , "Video Files (*.mp4)")

        return selectedFileName[0]

    def showMediaOnMain(self, fileName):
        if len(fileName) > 0:
            if QFileInfo.exists(fileName):

                mediaInfo = QFileInfo(fileName)
                self.mainPreviewMovie.stop()
                if bytes(mediaInfo.suffix().lower(),"ascii") in QMovie.supportedFormats():
                    self.mainPreviewMovie.setFileName(fileName)
                    if self.mainPreviewMovie.isValid():
                        self.mainPreviewMovie.setScaledSize(self.ui.imagePreviewMain.size())
                        self.ui.imagePreviewMain.setMovie(self.mainPreviewMovie)
                        self.mainPreviewMovie.start()
                        self.mainDisplay.showMovie(fileName)
                else:
                    reader = QImageReader(fileName)
                    reader.setAutoTransform(True)
                    newImage = reader.read()
                    if newImage:
                        if self.ui.stretchMainCB.isChecked():
                            self.ui.imagePreviewMain.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.imagePreviewMain.size())))
                        else:
                            self.ui.imagePreviewMain.setPixmap(QPixmap.fromImage(newImage.scaledToHeight(self.ui.imagePreviewMain.size().height())))

                    self.mainDisplay.showImage(fileName, self.ui.stretchMainCB.isChecked())

    def showMediaOnAux(self, fileName):
        if len(fileName) > 0:
            if QFileInfo.exists(fileName):
                mediaInfo = QFileInfo(fileName)
                self.auxPreviewMovie.stop()
                if bytes(mediaInfo.suffix().lower(),"ascii") in QMovie.supportedFormats():
                    self.auxPreviewMovie.setFileName(fileName)
                    if self.auxPreviewMovie.isValid():
                        self.auxPreviewMovie.setScaledSize(self.ui.imagePreviewAuxiliary.size())
                        self.ui.imagePreviewAuxiliary.setMovie(self.auxPreviewMovie)
                        self.auxPreviewMovie.start()
                        self.auxiliaryDisplay.showMovie(fileName)
                else:
                    reader = QImageReader(fileName)
                    reader.setAutoTransform(True)
                    newImage = reader.read()
                    if newImage:
                        if self.ui.stretchAuxCB.isChecked():
                            self.ui.imagePreviewAuxiliary.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.imagePreviewAuxiliary.size())))
                        else:
                            self.ui.imagePreviewAuxiliary.setPixmap(QPixmap.fromImage(newImage.scaledToHeight(self.ui.imagePreviewAuxiliary.size().height())))

                        self.auxiliaryDisplay.showImage(fileName, self.ui.stretchAuxCB.isChecked())

    def getTextFile(self):
        fileName = QFileDialog.getOpenFileName(self.ui, "Open Text File", self._settings.getDocumentDir() , "Text File (*.txt)")
        if len(fileName[0]) > 0:
            fileInfo = QFileInfo(fileName[0])
            self._settings.setDocumentDir(fileInfo.absolutePath())

            file = QFile(fileName[0])
            if not file.open(QIODevice.ReadOnly | QIODevice.Text):
                return
            text = ""
            linecount = 0

            # To avoid reading in large files which couldn't be displayed anyway,
            # limit the lines to something reasonable
            while (linecount < 10) and (not file.atEnd()):
                text += file.readLine()
                linecount += 1
            return text
        else:
            return None

    def styleSheet(self, color):
        style = f"background: rgb({color.red()},{color.green()},{color.blue()}); color:"
        if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
            style += "white"
        else:
            style += "black"

        return style

    def teamFont(self, color):
        if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
            return QColor(Qt.white)

        return QColor(Qt.black)

    def setLeftTeamColors(self, colorSelected):
        style = self.styleSheet(colorSelected)

        self.ui.teamNameLeft.setStyleSheet(style)
        self.ui.leftThingTeamRB.setStyleSheet(style)
        self.mainDisplay.colorizeLeftScore(style)
        self.auxiliaryDisplay.colorizeLeftScore(style)

    def setRightTeamColors(self, colorSelected):
        style = self.styleSheet(colorSelected)

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

    # Text box color mamagement
    def setTextBoxColor(self, coloredButton, colorStyle):
        coloredButton.setStyleSheet(colorStyle)

    # Left side preset colors
    @Slot()
    def useLeftColorPreset1(self):
        style = self.ui.leftColorPreset1.styleSheet()
        self.setTextBoxColor(self.ui.leftTextColorPB, style)

    @Slot()
    def useLeftColorPreset1(self):
        style = self.ui.leftColorPreset1.styleSheet()
        self.setTextBoxColor(self.ui.leftTextColorPB, style)

    @Slot()
    def useLeftColorPreset2(self):
        style = self.ui.leftColorPreset2.styleSheet()
        self.setTextBoxColor(self.ui.leftTextColorPB, style)

    @Slot()
    def useLeftColorPreset3(self):
        style = self.ui.leftColorPreset3.styleSheet()
        self.setTextBoxColor(self.ui.leftTextColorPB, style)

    @Slot()
    def useLeftColorPreset4(self):
        style = self.ui.leftColorPreset4.styleSheet()
        self.setTextBoxColor(self.ui.leftTextColorPB, style)

    @Slot()
    def useLeftColorPreset5(self):
        style = self.ui.leftColorPreset5.styleSheet()
        self.setTextBoxColor(self.ui.leftTextColorPB, style)

    @Slot()
    def useLeftColorPreset6(self):
        style = self.ui.leftColorPreset6.styleSheet()
        self.setTextBoxColor(self.ui.leftTextColorPB, style)

    @Slot()
    def useLeftColorPreset7(self):
        style = self.ui.leftColorPreset7.styleSheet()
        self.setTextBoxColor(self.ui.leftTextColorPB, style)

    @Slot()
    def useLeftColorPreset8(self):
        style = self.ui.leftColorPreset8.styleSheet()
        self.setTextBoxColor(self.ui.leftTextColorPB, style)


    @Slot()
    def pickLeftTextColor(self):
        color_chooser = QColorDialog(self.ui)
        colorSelected = color_chooser.getColor(title = 'Pick Left Text Box Color')

        # Update the presets incase one was changed while picking a color
        self.setPresetColors()

        if colorSelected != None:
            style = self.styleSheet(colorSelected)
            self.setTextBoxColor(self.ui.leftTextColorPB, style)

    # Right side preset colors
    @Slot()
    def useRightColorPreset1(self):
        style = self.ui.rightColorPreset1.styleSheet()
        self.setTextBoxColor(self.ui.rightTextColorPB, style)

    @Slot()
    def useRightColorPreset1(self):
        style = self.ui.rightColorPreset1.styleSheet()
        self.setTextBoxColor(self.ui.rightTextColorPB, style)

    @Slot()
    def useRightColorPreset2(self):
        style = self.ui.rightColorPreset2.styleSheet()
        self.setTextBoxColor(self.ui.rightTextColorPB, style)

    @Slot()
    def useRightColorPreset3(self):
        style = self.ui.rightColorPreset3.styleSheet()
        self.setTextBoxColor(self.ui.rightTextColorPB, style)

    @Slot()
    def useRightColorPreset4(self):
        style = self.ui.rightColorPreset4.styleSheet()
        self.setTextBoxColor(self.ui.rightTextColorPB, style)

    @Slot()
    def useRightColorPreset5(self):
        style = self.ui.rightColorPreset5.styleSheet()
        self.setTextBoxColor(self.ui.rightTextColorPB, style)

    @Slot()
    def useRightColorPreset6(self):
        style = self.ui.rightColorPreset6.styleSheet()
        self.setTextBoxColor(self.ui.rightTextColorPB, style)

    @Slot()
    def useRightColorPreset7(self):
        style = self.ui.rightColorPreset7.styleSheet()
        self.setTextBoxColor(self.ui.rightTextColorPB, style)

    @Slot()
    def useRightColorPreset8(self):
        style = self.ui.rightColorPreset8.styleSheet()
        self.setTextBoxColor(self.ui.rightTextColorPB, style)


    @Slot()
    def pickRightTextColor(self):
        color_chooser = QColorDialog(self.ui)
        colorSelected = color_chooser.getColor(title = 'Pick Right Text Box Color')

        # Update the presets incase one was changed while picking a color
        self.setPresetColors()

        if colorSelected.isValid():
            style = self.styleSheet(colorSelected)
            self.setTextBoxColor(self.ui.rightTextColorPB, style)

    @Slot()
    def blackoutBoth(self):
        self.blackoutMain()
        self.blackoutAux()

    @Slot()
    def blackoutMain(self):
        self.ui.imagePreviewMain.clear()
        self.ui.imagePreviewMain.setStyleSheet("background:black; color:black")
        self.mainDisplay.blackout()

    @Slot()
    def blackoutAux(self):
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
        self.showMediaOnMain(self.selectImageFile())

    @Slot()
    def getImageFileAuxiliary(self):
        self.showMediaOnAux(self.selectImageFile())

    @Slot()
    def getVideoFile(self):
        self.videoFile = self.selectVideoFile()
        if len(self.videoFile) > 0:
            if QFileInfo.exists(self.videoFile):

                mediaInfo = QFileInfo(self.videoFile)
                if mediaInfo.suffix().lower() == 'mp4':
                    self.mediaPlayer.setSource(QUrl(self.videoFile))

    @Slot()
    def loadTextboxLeft(self):
        textToLoad = self.getTextFile()
        if textToLoad != None:
            self.ui.leftTextBox.setText(textToLoad)

    @Slot()
    def loadTextboxRight(self):
        textToLoad = self.getTextFile()
        if textToLoad != None:
            self.ui.rightTextBox.setText(textToLoad)

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

    @Slot()
    def showLeftTextMain(self):
        font = self.ui.fontComboBoxLeft.currentFont()
        font.setPointSize(self.ui.leftFontSize.value())
        self.mainDisplay.showText(self.ui.leftTextBox.toPlainText(), self.ui.leftTextColorPB.styleSheet(), font)
        self.ui.imagePreviewMain.clear()

    @Slot()
    def showLeftTextAuxiliary(self):
        font = self.ui.fontComboBoxLeft.currentFont()
        font.setPointSize(self.ui.leftFontSize.value())
        self.auxiliaryDisplay.showText(self.ui.leftTextBox.toPlainText(), self.ui.leftTextColorPB.styleSheet(), font)
        self.ui.imagePreviewAuxiliary.clear()

    @Slot()
    def showLeftTextBoth(self):
        self.showLeftTextMain()
        self.showLeftTextAuxiliary()

    @Slot()
    def showRightTextMain(self):
        font = self.ui.fontComboBoxRight.currentFont()
        font.setPointSize(self.ui.rightFontSize.value())
        self.mainDisplay.showText(self.ui.rightTextBox.toPlainText(), self.ui.rightTextColorPB.styleSheet(), font)
        self.ui.imagePreviewMain.clear()

    @Slot()
    def showRightTextAuxiliary(self):
        font = self.ui.fontComboBoxRight.currentFont()
        font.setPointSize(self.ui.rightFontSize.value())
        self.auxiliaryDisplay.showText(self.ui.rightTextBox.toPlainText(), self.ui.rightTextColorPB.styleSheet(), font)
        self.ui.imagePreviewAuxiliary.clear()

    @Slot()
    def showRightTextBoth(self):
        self.showRightTextMain()
        self.showRightTextAuxiliary()

    @Slot()
    def clearLeftText(self):
        self.ui.leftTextBox.clear()

    @Slot()
    def clearRightText(self):
        self.ui.rightTextBox.clear()

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

    # Things Tab Management
    def listThingz(self):
        listText = "Empty"
        if self.ui.thingzListLW.count() > 0:
            listText = ""
            for thingRow in range(self.ui.thingzListLW.count()):
                listText += self.ui.thingzListLW.item(thingRow).text() + "\n"

        return listText

    @Slot()
    def showThingzListMain(self):
        thingFont = self.ui.thingFontFCB.currentFont()
        thingFont.setPointSize(self.ui.thingFontSizeSB.value())
        self.mainDisplay.showText(self.listThingz(), font = thingFont)

    @Slot()
    def showThingzListAuxiliary(self):
        thingFont = self.ui.thingFontFCB.currentFont()
        thingFont.setPointSize(self.ui.thingFontSizeSB.value())
        self.auxiliaryDisplay.showText(self.listThingz(), font = thingFont)

    @Slot()
    def showThingzListBoth(self):
        self.showThingzListMain()
        self.showThingzListAuxiliary()

    @Slot()
    def showThingMain(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            thingFont = self.ui.thingFontFCB.currentFont()
            thingFont.setPointSize(self.ui.thingFontSizeSB.value())
            self.mainDisplay.showText(self.ui.thingzListLW.currentItem().thingData(), self.styleSheet(currentThing.background().color()), thingFont)

    @Slot()
    def showThingAuxiliary(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            thingFont = self.ui.thingFontFCB.currentFont()
            thingFont.setPointSize(self.ui.thingFontSizeSB.value())
            self.auxiliaryDisplay.showText(self.ui.thingzListLW.currentItem().thingData(), self.styleSheet(currentThing.background().color()), thingFont)

    @Slot()
    def showThingBoth(self):
        self.showThingMain()
        self.showThingAuxiliary()

    @Slot()
    def updateThingsText(self):
        currentThing = self.ui.thingzListLW.currentItem()

        if currentThing != None:
            self.ui.thingzListLW.currentItem().updateSubstitutes(self.ui.thingTextEdit.toPlainText())

    @Slot()
    def toggleTeam(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            if currentThing.isLeftSideTeam():
                currentThing.setBackground(self._settings.getRightTeamColor())
                currentThing.setForeground(self.teamFont(self._settings.getRightTeamColor()))
            else:
                currentThing.setBackground(self._settings.getLeftTeamColor())
                currentThing.setForeground(self.teamFont(self._settings.getLeftTeamColor()))

            currentThing.toggleTeam()

    @Slot(ThingzWidget)
    def showSelectedThing(self, thing):
        # Display selected item's title and text in the editor
        self.ui.thingFocusLBL.setText(thing.text())
        self.ui.thingTextEdit.setPlainText(thing.substitutes())

    @Slot(ThingzWidget)
    def titleEdited(self, thing):
        # Display selected item's title and text in the editor
        self.ui.thingFocusLBL.setText(thing.text())

    @Slot()
    def addThingtoList(self):
        thingStr = self.ui.thingNameTxt.text()
        if len(thingStr) > 0:

            # Determine which team is being entered from the radio buttons
            # and color the thing appropriately
            if self.ui.leftThingTeamRB.isChecked():
                newThing = ThingzWidget(thingStr, True, self.ui.thingzListLW)
                newThing.setBackground(self._settings.getLeftTeamColor())
                newThing.setForeground(self.teamFont(self._settings.getLeftTeamColor()))
                self.ui.rightThingTeamRB.setChecked(True)
            else: # Right Team Color
                newThing = ThingzWidget(thingStr, False, self.ui.thingzListLW)
                newThing.setBackground(self._settings.getRightTeamColor())
                newThing.setForeground(self.teamFont(self._settings.getRightTeamColor()))
                self.ui.leftThingTeamRB.setChecked(True)

            newThingFont = newThing.font()
            newThingFont.setPointSize(12)
            newThing.setFont(newThingFont)
            newThing.setFlags(newThing.flags() | Qt.ItemIsEditable)

            self.ui.thingNameTxt.setText("")
            self.ui.thingNameTxt.setFocus()
            self.ui.thingzListLW.setCurrentItem(newThing)
            self.ui.thingTextEdit.clear()

    @Slot()
    def thingzMoveDown(self):
        thingRow = self.ui.thingzListLW.currentRow()
        if thingRow < 0:
            return
        thing = self.ui.thingzListLW.takeItem(thingRow)
        self.ui.thingzListLW.insertItem(thingRow+1,thing)
        self.ui.thingzListLW.setCurrentRow(thingRow+1)

    @Slot()
    def thingzMoveUp(self):
        thingRow = self.ui.thingzListLW.currentRow()
        if thingRow < 0:
            return
        thing = self.ui.thingzListLW.takeItem(thingRow)
        self.ui.thingzListLW.insertItem(thingRow-1,thing)
        self.ui.thingzListLW.setCurrentRow(thingRow-1)

    @Slot()
    def removeThingfromList(self):
        self.ui.thingzListLW.takeItem(self.ui.thingzListLW.row(self.ui.thingzListLW.currentItem()))
        if self.ui.thingzListLW.currentItem() != None:
            self.showSelectedThing(self.ui.thingzListLW.currentItem())
        else:
            self.ui.thingFocusLBL.clear()
            self.ui.thingTextEdit.clear()


    @Slot()
    def clearThingzList(self):
        reply = QMessageBox.question(self.ui, 'Clear Thingz', 'Are you sure you want clear all Thingz?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.thingzListLW.clear()
            self.ui.leftThingTeamRB.setChecked(True)
            self.ui.thingFocusLBL.clear()
            self.ui.thingTextEdit.clear()

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
            for file_info in QDir(_promosDirectory).entryInfoList("*.jpg", QDir.Files, QDir.Name):
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
        # Resample the promos directory once the current cycle is done
        if self.promosMode and self.currentSlide == 0:
            self.loadPromosSlides()

        # Progress the slide show if there are now slides to show in the list
        self.currentSlide += 1
        slideCount = self.ui.slideListLW.count()
        if slideCount > 0:
            self.currentSlide = self.currentSlide % slideCount
            self.ui.slideListLW.setCurrentRow(self.currentSlide)

            self.showSlideMain()
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
        self.slideShowTimer.setInterval(self._settings.getSlideshowDelay()*1000)
        self.ui.slideListLW.setCurrentRow(self.currentSlide)
        self.mainDisplay.blackout() # removes and text colors
        self.showSlideMain()
        self.slideShowTimer.start()

    @Slot()
    def slideShowPause(self):
        self.slideShowTimer.stop()
        self.paused = True

    @Slot()
    def slideShowStop(self):
        self.slideShowTimer.stop()
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
        self.whams = self.ui.spinBox.value()

        nextSlide = self.whammyRandomizer.bounded(0, self.ui.slideListLW.count())
        self.ui.slideListLW.setCurrentRow(nextSlide)
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

        nextSlide = self.whammyRandomizer.bounded(0, self.ui.slideListLW.count())
        self.ui.slideListLW.setCurrentRow(nextSlide)
        self.slideLoadSignal.emit(self.ui.slideListLW.currentItem().imagePath())


    # Media Search Slots
    @Slot()
    def touchPortal(self):
        self.ui.mediaSearchResultsLW.clear()
        self.ui.mediaSearchPreviewLBL.clear()
        self.ui.mediaFileNameLBL.clear()
        foundMedia = self.mediaFileDatabase.searchMedia(self.ui.mediaSearchTagsLE.text(), self.ui.allMediaTagsCB.isChecked())
        if len(foundMedia) > 0:
            for media in foundMedia:
                SlideWidget(QFileInfo(media), self.ui.mediaSearchResultsLW)
        else:
            reply = QMessageBox.information(self.ui, 'No Search Results', 'No media with those tags found.')
    @Slot()
    def searchMedia(self):
        self.ui.mediaSearchResultsLW.clear()
        self.ui.mediaSearchPreviewLBL.clear()
        self.ui.mediaFileNameLBL.clear()
        foundMedia = self.mediaFileDatabase.searchMedia(self.ui.mediaSearchTagsLE.text(), self.ui.allMediaTagsCB.isChecked())
        if len(foundMedia) > 0:
            for media in foundMedia:
                SlideWidget(QFileInfo(media), self.ui.mediaSearchResultsLW)
        else:
            reply = QMessageBox.information(self.ui, 'No Search Results', 'No media with those tags found.')

    @Slot()
    def setMediaLibrary(self):
        setDir = QFileDialog.getExistingDirectory(self.ui,
                "Select the Media Library location",
                self._settings.getMediaDir(), QFileDialog.ShowDirsOnly)
        if setDir:
            self._settings.setMediaDir(setDir)
            mediaCount = self.mediaFileDatabase.indexMedia(setDir)
            self.ui.mediaFilesCountLBL.setText(str(mediaCount))

            # The Media Library is also part of the Media mediaModel so reset it
            self.imageTreeView = self.ui.slideShowFilesTreeView
            self.imageTreeView.setModel(self.mediaModel)
            self.imageTreeView.setRootIndex(self.mediaModel.index(setDir))
            for i in range(1, self.mediaModel.columnCount()):
                self.imageTreeView.header().hideSection(i)
            self.imageTreeView.setHeaderHidden(True)

    @Slot(SlideWidget)
    def previewSelectedMedia(self, slide):
        mediaInfo = slide.fileInfo()
        self.ui.mediaFileNameLBL.setText(slide.imagePath())
        self.searchPreviewMovie.stop()
        if mediaInfo.suffix().lower() == 'gif':
            self.searchPreviewMovie.setFileName(slide.imagePath())
            if self.searchPreviewMovie.isValid():
                self.searchPreviewMovie.setScaledSize(self.ui.mediaSearchPreviewLBL.size())
                self.ui.mediaSearchPreviewLBL.setMovie(self.searchPreviewMovie)
                self.searchPreviewMovie.start()
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
    def showMediaPreviewMain(self, slide):
        self.showMediaOnMain(slide.imagePath())

    @Slot()
    def searchToMainShow(self):
        if self.ui.mediaSearchResultsLW.currentItem() != None:
            slide = self.ui.mediaSearchResultsLW.currentItem()
            self.showMediaOnMain(slide.imagePath())
    @Slot()
    def searchToAuxShow(self):
        if self.ui.mediaSearchResultsLW.currentItem() != None:
            slide = self.ui.mediaSearchResultsLW.currentItem()
            self.showMediaOnAux(slide.imagePath())

    @Slot()
    def searchtoSlideShow(self):
        if self.ui.mediaSearchResultsLW.currentItem() != None:
            SlideWidget(QFileInfo(self.ui.mediaSearchResultsLW.currentItem().imagePath()), self.ui.slideListLW)

    # Sound Search Slots
    @Slot()
    def searchSounds(self):
        self.ui.soundSearchResultsLW.clear()
        foundSounds = self.mediaFileDatabase.searchSounds(self.ui.soundSearchTagsLE.text(), self.ui.allsoundTagsCB.isChecked())
        if len(foundSounds) > 0:
            for sound in foundSounds:
                SlideWidget(QFileInfo(sound), self.ui.soundSearchResultsLW)
        else:
            QMessageBox.information(self.ui, 'No Search Results', 'No sounds with those tags found.')


    @Slot()
    def setSoundLibrary(self):
        setDir = QFileDialog.getExistingDirectory(self.ui,
                "Select the Sound Library location",
                self._settings.getSoundDir(), QFileDialog.ShowDirsOnly)
        if setDir:
            self._settings.setSoundDir(setDir)
            soundsCount = self.mediaFileDatabase.indexSounds(setDir)
            self.ui.soundFilesCountLBL.setText(str(soundsCount))

    @Slot()
    def soundPlay(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PausedState:
            self.mediaPlayer.play()
            return

        if self.ui.soundSearchResultsLW.currentItem() != None:
            self.mediaPlayer.setSource(QUrl.fromLocalFile(self.ui.soundSearchResultsLW.currentItem().imagePath()))
            self.mediaPlayer.setPosition(0)
            self.mediaPlayer.play()

    @Slot()
    def soundPause(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PausedState:
            self.mediaPlayer.play()
            return

        if self.mediaPlayer.isPlaying():
            self.mediaPlayer.pause()

    @Slot()
    def soundStop(self):
        self.mediaPlayer.stop()

    @Slot()
    def soundLoop(self):
        if self.ui.soundLoopPB.isChecked():
            self.mediaPlayer.setLoops(QMediaPlayer.Infinite)
        else:
            self.mediaPlayer.setLoops(QMediaPlayer.Once)
            if self.mediaPlayer.isPlaying():
                self.mediaPlayer.stop()

    @Slot(int)
    def setSoundVolume(self, value):
        self.audioOutput.setVolume(value/self.ui.soundVolumeSL.maximum())

    @Slot()
    def loadSoundQueue(self):
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
    def saveSoundQueue(self):
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
    def saveSoundFXPallette(self):
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
        self.loadSoundPallettes()

    @Slot()
    def clearSoundQueue(self):
        reply = QMessageBox.question(self.ui, 'Clear Sounds', 'Are you sure you want clear all sounds?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.soundQueueLW.clear()


    @Slot()
    def soundMoveUp(self):
        soundRow = self.ui.soundQueueLW.currentRow()
        if soundRow < 0:
            return
        sound = self.ui.soundQueueLW.takeItem(soundRow)
        self.ui.soundQueueLW.insertItem(soundRow-1,sound)
        self.ui.soundQueueLW.setCurrentRow(soundRow-1)

    @Slot()
    def soundMoveDown(self):
        soundRow = self.ui.soundQueueLW.currentRow()
        if soundRow < 0:
            return
        sound = self.ui.soundQueueLW.takeItem(soundRow)
        self.ui.soundQueueLW.insertItem(soundRow+1,sound)
        self.ui.soundQueueLW.setCurrentRow(soundRow+1)

    @Slot()
    def soundAddToList(self):
        if self.ui.soundSearchResultsLW.currentItem() != None:
            sound = self.ui.soundSearchResultsLW.takeItem(self.ui.soundSearchResultsLW.currentRow())
            self.ui.soundQueueLW.addItem(sound)

    @Slot()
    def soundRemoveFromList(self):
        if self.ui.soundQueueLW.currentItem() != None:
            sound = self.ui.soundQueueLW.takeItem(self.ui.soundQueueLW.currentRow())
            self.ui.soundSearchResultsLW.addItem(sound)

    @Slot(QMediaPlayer.Error, str)
    def playerError(self, error, error_string):
        QMessageBox.critical(self.ui, "Media Player Error", error_string)

    # Sound Palletes
    @Slot(int)
    def loadSoundPallettes(self):
        self.palletteSelect.clear()
        palletteIter = QDirIterator(self._settings.getConfigDir(),{"*.sfx"})
        while palletteIter.hasNext():
            palletteFileInfo = palletteIter.nextFileInfo()
            palletteFileName = palletteFileInfo.completeBaseName()
            self.palletteSelect.addItem(palletteFileName, palletteFileInfo)

    @Slot(int)
    def loadSoundEffects(self, index):
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
                if buttonNumber < self.soundFXNumber:
                    if QFileInfo.exists(sound[1]): # The file still exists
                        file = QFileInfo(sound[1])
                        if file.suffix() == "wav": # Only wav files are supported for sound effect
                            self.sfx_buttons[buttonNumber].loadSoundEffect(file)
                        else:
                            self.sfx_buttons[buttonNumber].disable()
                    else:
                        self.sfx_buttons[buttonNumber].disable()

                buttonNumber += 1

        for disabledButton in range(buttonNumber, self.soundFXNumber):
            self.sfx_buttons[disabledButton].disable()

    @Slot(int)
    def setFXVolume(self, value):
        sliderMax = self.ui.soundFXVolumeHS.maximum()
        for sound in self.sfx_buttons:
            sound.setFXVolume(value/sliderMax)

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
        self._settings.setStartupImage(self.selectImageFile())

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
