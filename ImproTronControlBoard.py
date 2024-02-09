# This Python file uses the following encoding: utf-8
import json
import sys
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QImageReader, QPixmap, QMovie, QColor, QGuiApplication
from PySide6.QtWidgets import QColorDialog, QFileDialog, QFileSystemModel, QMessageBox, QApplication
from PySide6.QtCore import QObject, QStandardPaths, Slot, Qt, QTimer, QItemSelection, QFileInfo, QFile, QIODevice, QEvent, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from Improtronics import ThingzWidget, SlideWidget
from MediaFileDatabase import MediaFileDatabase
import ImproTronIcons


class ImproTronControlBoard(QObject):
    def __init__(self, mainImprotron, auxiliaryImprotron, parent=None):
        super(ImproTronControlBoard,self).__init__()
        self.mainDisplay = mainImprotron
        self.auxiliaryDisplay = auxiliaryImprotron
        loader = QUiLoader()
        self.ui = loader.load("ImproTronControlPanel.ui")

        self.model = QFileSystemModel()
        self.model.setRootPath(QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0])

        self.mediaFileDatabase = MediaFileDatabase()
        self.mediaDir = QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0]
        mediaCount = self.mediaFileDatabase.indexMedia(self.mediaDir)
        self.ui.mediaFilesCountLBL.setText(str(mediaCount))

        self.soundDir = QStandardPaths.standardLocations(QStandardPaths.MusicLocation)[0]
        soundCount = self.mediaFileDatabase.indexSounds(self.soundDir)
        self.ui.soundFilesCountLBL.setText(str(soundCount))

        self.sound = QMediaPlayer()
        self.audioOutput = QAudioOutput()
        self.sound.setAudioOutput(self.audioOutput)
        self.audioOutput.setVolume(50)

        # Location for all slide shows sounds queues, hotbutton lists etc
        self.configDir = QStandardPaths.standardLocations(QStandardPaths.GenericConfigLocation)[0]+"/ImproTron"

        # Colors for Thingz list
        self.rightTeamBackground = QColor(Qt.white)
        self.rightTeamColor = QColor(Qt.black)
        self.leftTeamBackground = QColor(Qt.white)
        self.leftTeamColor = QColor(Qt.black)

        # Connect Score related signals to slots
        self.ui.colorRightPB.clicked.connect(self.pickRightTeamColor)
        self.ui.colorLeftPB.clicked.connect(self.pickLeftTeamColor)
        self.ui.showScoresMainPB.clicked.connect(self.showScoresMain)
        self.ui.showScoresBothPB.clicked.connect(self.showScoresBoth)
        self.ui.showScoresAuxiliaryPB.clicked.connect(self.showScoresAuxiliary)

        # Quick Add Buttons for score updates.
        self.ui.add50PB.clicked.connect(self.quickAdd50) # Add 5 to Left team
        self.ui.add32PB.clicked.connect(self.quickAdd32) # Add 3 to Left, 2 to Right
        self.ui.add23PB.clicked.connect(self.quickAdd23) # Add 2 to Left, 3 to Right
        self.ui.add05PB.clicked.connect(self.quickAdd05) # Add 5 to Right team

        # Connect Team Name updates
        self.ui.teamNameLeft.textEdited.connect(self.showLeftTeam)
        self.ui.teamNameRight.textEdited.connect(self.showRightTeam)

        # Connect info (text and images) message updates
        self.ui.showLeftTextMainPB.clicked.connect(self.showLeftTextMain)
        self.ui.showLeftTextAuxiliaryPB.clicked.connect(self.showLeftTextAuxiliary)
        self.ui.showLeftTextBothPB.clicked.connect(self.showLeftTextBoth)
        self.ui.showRightTextMainPB.clicked.connect(self.showRightTextMain)
        self.ui.showRightTextAuxiliaryPB.clicked.connect(self.showRightTextAuxiliary)
        self.ui.showRightTextBothPB.clicked.connect(self.showRightTextBoth)
        self.ui.clearLeftTextPB.clicked.connect(self.clearLeftText)
        self.ui.clearRightTextPB.clicked.connect(self.clearRightText)
        self.ui.clearBothTextPB.clicked.connect(self.clearBothText)
        self.ui.loadTextboxBothPB.clicked.connect(self.loadTextboxBoth)
        self.ui.loadTextboxLeftPB.clicked.connect(self.loadTextboxLeft)
        self.ui.loadTextboxRightPB.clicked.connect(self.loadTextboxRight)
        self.ui.loadImageMainPB.clicked.connect(self.getImageFileMain)
        self.ui.loadImageAuxiliaryPB.clicked.connect(self.getImageFileAuxiliary)
        self.ui.pasteImageMainPB.clicked.connect(self.pasteImageMain)
        self.ui.pasteImageAuxiliaryPB.clicked.connect(self.pasteImageAuxiliary)

        # Connect Show Text Config elements
        self.ui.rightTextColorPB.clicked.connect(self.pickRightTextColor)
        self.ui.leftTextColorPB.clicked.connect(self.pickLeftTextColor)
        self.ui.blackoutMainPB.clicked.connect(self.blackoutMain)
        self.ui.blackoutAuxPB.clicked.connect(self.blackoutAux)
        self.ui.blackoutBothPB.clicked.connect(self.blackoutBoth)

        # Countdown timer controls
        self.ui.startTimerPB.clicked.connect(self.startTimer)
        self.ui.resetTimerPB.clicked.connect(self.resetTimer)
        self.ui.pauseTimerPB.clicked.connect(self.pauseTimerPB)
        self.ui.timerVisibleMainCB.stateChanged.connect(self.timerVisibleMain)

        # Connect Thingz Management
        self.ui.thingzListLW.itemClicked.connect(self.showSelectedThing)
        self.ui.thingzListLW.itemChanged.connect(self.titleEdited)
        self.ui.addThingPB.clicked.connect(self.addThingtoList)
        self.ui.thingNameTxt.returnPressed.connect(self.addThingtoList)
        self.ui.removeThingPB.clicked.connect(self.removeThingfromList)
        self.ui.clearThingzPB.clicked.connect(self.clearThingzList)
        self.ui.thingzMoveUpPB.clicked.connect(self.thingzMoveUp)
        self.ui.thingzMoveDownPB.clicked.connect(self.thingzMoveDown)
        self.ui.leftThingTeamRB.clicked.connect(self.leftThingTeam)
        self.ui.rightThingTeamRB.clicked.connect(self.rightThingTeam)
        self.ui.thingTextEdit.textChanged.connect(self.updateThingsText)
        self.ui.showThingMainPB.clicked.connect(self.showThingMain)
        self.ui.showThingAuxiliaryPB.clicked.connect(self.showThingAuxiliary)
        self.ui.showThingBothPB.clicked.connect(self.showThingBoth)
        self.ui.showThingzMainPB.clicked.connect(self.showThingzListMain)
        self.ui.showThingzAuxiliaryPB.clicked.connect(self.showThingzListAuxiliary)
        self.ui.showThingzBothPB.clicked.connect(self.showThingzListBoth)

        # Slide Show Management
        self.imageTreeView = self.ui.slideShowFilesTreeView
        self.imageTreeView.setModel(self.model)
        self.imageTreeView.setRootIndex(self.model.index(QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0]))
        for i in range(1, self.model.columnCount()):
            self.imageTreeView.header().hideSection(i)
        self.imageTreeView.setHeaderHidden(True)

        # Selection changes will trigger a slot
        selectionModel = self.imageTreeView.selectionModel()
        selectionModel.selectionChanged.connect(self.imageSelectedfromDir)

        # Connect Slide Show Management
        self.ui.slideListLW.itemClicked.connect(self.previewSelectedSlide)
        self.ui.slideListLW.itemDoubleClicked.connect(self.showSlideMain)
        self.ui.addSlidePB.clicked.connect(self.addSlidetoList)
        self.ui.slideMoveUpPB.clicked.connect(self.slideMoveUp)
        self.ui.slideMoveDownPB.clicked.connect(self.slideMoveDown)
        self.ui.removeSlidePB.clicked.connect(self.removeSlidefromList)
        self.ui.clearSlideShowPB.clicked.connect(self.clearSlideShow)
        self.ui.loadSlideShowPB.clicked.connect(self.loadSlideShow)
        self.ui.saveSlideShowPB.clicked.connect(self.saveSlideShow)
        self.ui.showSlideMainPB.clicked.connect(self.showSlideMain)
        self.ui.showSlideAuxiliaryPB.clicked.connect(self.showSlideAuxiliary)
        self.ui.showSlideBothPB.clicked.connect(self.showSlideBoth)

        # Slideshow Timer wiring
        self.slideShowTimer = QTimer()
        self.secondsSettings = self.ui.slideShowSecondSB
        self.paused = False
        self. currentSlide = 0
        self.slideShowTimer.timeout.connect(self.nextSlide)
        self.ui.slideShowRestartPB.clicked.connect(self.slideShowRestart)
        self.ui.slideShowRewindPB.clicked.connect(self.slideShowBack)
        self.ui.slideShowPlayPB.clicked.connect(self.slideShowPlay)
        self.ui.slideShowPausePB.clicked.connect(self.slideShowPause)
        self.ui.slideShowStopPB.clicked.connect(self.slideShowStop)
        self.ui.slideShowForwardPB.clicked.connect(self.slideShowForward)
        self.ui.slideShowSkipPB.clicked.connect(self.slideShowSkip)

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

        self.ui.soundBackPB.clicked.connect(self.soundBack)
        self.ui.soundPlayPB.clicked.connect(self.soundPlay)
        self.ui.soundPausePB.clicked.connect(self.soundPause)
        self.ui.soundStopPB.clicked.connect(self.soundStop)
        self.ui.soundLoopPB.clicked.connect(self.soundLoop)
        self.ui.soundVolumeSL.valueChanged.connect(self.audioOutput.setVolume)
        self.sound.errorOccurred.connect(self.playerError)

        self.ui.loadSoundQueuePB.clicked.connect(self.loadSoundQueue)
        self.ui.saveSoundQueuePB.clicked.connect(self.saveSoundQueue)
        self.ui.clearSoundQueuePB.clicked.connect(self.clearSoundQueue)

        self.ui.soundMoveUpPB.clicked.connect(self.soundMoveUp)
        self.ui.soundMoveDownPB.clicked.connect(self.soundMoveDown)
        self.ui.soundAddToListPB.clicked.connect(self.soundAddToList)
        self.ui.soundRemoveFromListPB.clicked.connect(self.soundRemoveFromList)

        # Preferences Wiring
        self.ui.aboutPB.clicked.connect(self.about)

        # Preferences
        self.ui.improtronUnlockPB.clicked.connect(self.improtronUnlock)

        self.ui.setWindowFlags(
            Qt.Window |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint |
            Qt.WindowTitleHint
            )
        self.ui.show()

        # Set up an event filter to handle the orderly shutdown of the app.
        self.ui.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.ui and event.type() == QEvent.Close:
            self.shutdown()
            event.ignore()
            return True
        return super(ImproTronControlBoard, self).eventFilter(obj, event)

    def shutdown(self):
        self.ui.removeEventFilter(self)
        QApplication.quit()

    def getConfigDir(self):
        return self.configDir

    def getMediaDir(self):
        return self.mediaDir

    def getMusicDir(self):
        return self.soundDir

    def findWidget(self, type, widgetName):
        return self.ui.findChild(type, widgetName)

    def selectImageFile(self):
        selectedFileName = QFileDialog.getOpenFileName(self.ui, "Select Media", self.mediaDir , "Media Files (*.png *.jpg *.bmp *.gif *.webp)")
        if selectedFileName != None:
            return selectedFileName[0]

        return None

    def showMediaOnMain(self, fileName):
        if fileName != None:
            if QFileInfo.exists(fileName):
                mediaInfo = QFileInfo(fileName)
                if mediaInfo.suffix().lower() == 'gif':
                    movie = QMovie(fileName)
                    if movie.isValid():
                        movie.setSpeed(100)
                        movie.setScaledSize(self.ui.imagePreviewMain.size())
                        self.ui.imagePreviewMain.setMovie(movie)
                        movie.start()
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
        if fileName != None:
            if QFileInfo.exists(fileName):
                mediaInfo = QFileInfo(fileName)
                if mediaInfo.suffix().lower() == 'gif':
                    movie = QMovie(fileName)
                    if movie.isValid():
                        movie.setSpeed(100)
                        movie.setScaledSize(self.ui.imagePreviewAuxiliary.size())
                        self.ui.imagePreviewAuxiliary.setMovie(movie)
                        movie.start()
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
        fileName = QFileDialog.getOpenFileName(self.ui, "Open Text File", self.configFiles , "Text File (*.txt)")
        if fileName[0] != None:
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

    def teamColor(self, color):
        if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
            return QColor(Qt.white)

        return QColor(Qt.black)

    @Slot()
    def pickLeftTeamColor(self):
        color_chooser = QColorDialog(self.ui)
        colorSelected = color_chooser.getColor(title = 'Pick Left Team Color')
        if colorSelected.isValid():
            self.leftTeamBackground = colorSelected
            self.leftTeamColor = self.teamColor(colorSelected)
            style = self.styleSheet(self.leftTeamBackground)

            self.ui.teamNameLeft.setStyleSheet(style)
            self.ui.leftThingTeamRB.setStyleSheet(style)
            self.mainDisplay.colorizeLeftScore(style)
            self.auxiliaryDisplay.colorizeLeftScore(style)

    @Slot()
    def pickRightTeamColor(self):
        color_chooser = QColorDialog(self.ui)
        colorSelected = color_chooser.getColor(title = 'Pick Left Team Color')
        if colorSelected.isValid():
            self.rightTeamBackground = colorSelected
            self.rightTeamColor = self.teamColor(colorSelected)
            style = self.styleSheet(self.rightTeamBackground)

            self.ui.teamNameRight.setStyleSheet(style)
            self.ui.rightThingTeamRB.setStyleSheet(style)
            self.mainDisplay.colorizeRightScore(style)
            self.auxiliaryDisplay.colorizeRightScore(style)

    @Slot()
    def pickLeftTextColor(self):
        color_chooser = QColorDialog(self.ui)
        colorSelected = color_chooser.getColor(title = 'Pick Left Text Box Color')
        if colorSelected != None:
            style = self.styleSheet(colorSelected)

            self.ui.leftTextColorPB.setStyleSheet(style)

    @Slot()
    def pickRightTextColor(self):
        color_chooser = QColorDialog(self.ui)
        colorSelected = color_chooser.getColor(title = 'Pick Right Text Box Color')
        if colorSelected.isValid():
            style = self.styleSheet(colorSelected)

            self.ui.rightTextColorPB.setStyleSheet(style)

    @Slot()
    def blackoutBoth(self):
        self.mainDisplay.blackout()
        self.auxiliaryDisplay.blackout()

    @Slot()
    def blackoutMain(self):
        self.mainDisplay.blackout()

    @Slot()
    def blackoutAux(self):
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
    def loadTextboxLeft(self):
        textToLoad = self.getTextFile()
        if len(textToLoad) > 0:
            self.ui.leftTextBox.setText(textToLoad)

    @Slot()
    def loadTextboxRight(self):
        textToLoad = self.getTextFile()
        if textToLoad != None:
            self.ui.rightTextBox.setText(textToLoad)

    @Slot()
    def loadTextboxBoth(self):
        textToLoad = self.getTextFile()
        if textToLoad != None:
            self.ui.leftTextBox.setText(textToLoad)
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

    @Slot(str)
    def showRightTeam(self, teamName):
        self.mainDisplay.showRightTeam(teamName)
        self.auxiliaryDisplay.showRightTeam(teamName)
        self.ui.rightThingTeamRB.setText(teamName)

    @Slot()
    def showLeftTextMain(self):
        font = self.ui.fontComboBoxLeft.currentFont()
        font.setPointSize(self.ui.leftFontSize.value())
        self.mainDisplay.showText(self.ui.leftTextBox.toPlainText(), self.ui.leftTextColorPB.styleSheet(), False, font)

    @Slot()
    def showLeftTextAuxiliary(self):
        font = self.ui.fontComboBoxLeft.currentFont()
        font.setPointSize(self.ui.leftFontSize.value())
        self.auxiliaryDisplay.showText(self.ui.leftTextBox.toPlainText(), self.ui.leftTextColorPB.styleSheet(), False, font)

    @Slot()
    def showLeftTextBoth(self):
        self.showLeftTextMain()
        self.showLeftTextAuxiliary()

    @Slot()
    def showRightTextMain(self):
        font = self.ui.fontComboBoxRight.currentFont()
        font.setPointSize(self.ui.rightFontSize.value())
        self.mainDisplay.showText(self.ui.rightTextBox.toPlainText(), self.ui.rightTextColorPB.styleSheet(), False, font)

    @Slot()
    def showRightTextAuxiliary(self):
        font = self.ui.fontComboBoxRight.currentFont()
        font.setPointSize(self.ui.rightFontSize.value())
        self.auxiliaryDisplay.showText(self.ui.rightTextBox.toPlainText(), self.ui.rightTextColorPB.styleSheet(), False, font)

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

    @Slot()
    def clearBothText(self):
        self.clearLeftText()
        self.clearRightText()

    # Unlock the Improtron Displays so they can be moved. Lock them to maximize
    # on th screen they subsequently reside on.
    def improtronUnlock(self):
        if self.ui.improtronUnlockPB.isChecked():
            self.mainDisplay.restore()
            self.auxiliaryDisplay.restore()
        else: # Order matters so the main displays on top
            self.auxiliaryDisplay.maximize()
            self.mainDisplay.maximize()

    def listThingz(self):
        listText = "Empty"
        if self.ui.thingzListLW.count() > 0:
            listText = ""
            for thingRow in range(self.ui.thingzListLW.count()):
                listText += self.ui.thingzListLW.item(thingRow).text() + "\n"

        return listText

    # Things Tab Management
    @Slot()
    def showThingzListMain(self):
        self.mainDisplay.showText(self.listThingz(), self.styleSheet(self.leftTeamBackground), True)

    @Slot()
    def showThingzListAuxiliary(self):
        self.auxiliaryDisplay.showText(self.listThingz(), self.styleSheet(self.rightTeamBackground), True)

    @Slot()
    def showThingzListBoth(self):
        self.showThingzListMain()
        self.showThingzListAuxiliary()

    @Slot()
    def showThingMain(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            self.mainDisplay.showText(self.ui.thingzListLW.currentItem().thingData(), self.styleSheet(currentThing.background().color()), True)

    @Slot()
    def showThingAuxiliary(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            self.auxiliaryDisplay.showText(self.ui.thingzListLW.currentItem().thingData(), self.styleSheet(currentThing.background().color()), True)

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
    def rightThingTeam(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            if currentThing.isLeftSideTeam():
                currentThing.setForeground(self.rightTeamColor)
                currentThing.setBackground(self.rightTeamBackground)
            else:
                currentThing.setForeground(self.leftTeamColor)
                currentThing.setBackground(self.leftTeamBackground)

        currentThing.toggleTeam()

    @Slot()
    def leftThingTeam(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            if currentThing.isLeftSideTeam():
                currentThing.setForeground(self.rightTeamColor)
                currentThing.setBackground(self.rightTeamBackground)
            else:
                currentThing.setForeground(self.leftTeamColor)
                currentThing.setBackground(self.leftTeamBackground)

            currentThing.toggleTeam()

    @Slot(ThingzWidget)
    def showSelectedThing(self, thing):
        # Display selected item's title and text in the editor
        self.ui.thingFocusLBL.setText(thing.text())
        self.ui.thingTextEdit.setPlainText(thing.substitutes())
        if thing.isLeftSideTeam():
            self.ui.leftThingTeamRB.setChecked(True)
        else:
            self.ui.rightThingTeamRB.setChecked(True)

    @Slot(ThingzWidget)
    def titleEdited(self, thing):
        # Display selected item's title and text in the editor
        self.ui.thingFocusLBL.setText(thing.text())
        self.ui.thingTextEdit.setPlainText(thing.substitutes())

    @Slot()
    def addThingtoList(self):
        thingStr = self.ui.thingNameTxt.text()
        if len(thingStr) > 0:

            # Determine which team is being entered from the radio buttons
            # and color the thing appropriately
            if self.ui.leftThingTeamRB.isChecked():
                newThing = ThingzWidget(thingStr, True, self.ui.thingzListLW)
                newThing.setForeground(self.leftTeamColor)
                newThing.setBackground(self.leftTeamBackground)
                self.ui.rightThingTeamRB.setChecked(True)
            else:
                newThing = ThingzWidget(thingStr, False, self.ui.thingzListLW)
                newThing.setForeground(self.rightTeamColor)
                newThing.setBackground(self.rightTeamBackground)
                self.ui.leftThingTeamRB.setChecked(True)

            newThingFont = newThing.font()
            newThingFont.setPointSize(12)
            newThing.setFont(newThingFont)
            newThing.setFlags(newThing.flags() | Qt.ItemIsEditable)

            self.ui.thingNameTxt.setText("")
            self.ui.thingNameTxt.setFocus()

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

    @Slot()
    def clearThingzList(self):
        reply = QMessageBox.question(self.ui, 'Clear Thingz', 'Are you sure you want clear all Thingz?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.thingzListLW.clear()
            self.ui.leftThingTeamRB.setChecked(True)

    # Slideshow Management
    @Slot(QItemSelection, QItemSelection)
    def imageSelectedfromDir(self, new_selection, old_selection):
        # get the text of the selected item
        index = self.imageTreeView.selectionModel().currentIndex()
        if not self.model.isDir(index):
            imageFileInfo = self.model.fileInfo(index)
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
        if not self.model.isDir(index):
            SlideWidget(self.model.fileInfo(index), self.ui.slideListLW)

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
        self.ui.slideListLW.takeItem(self.ui.slideListLW.row(self.ui.slideListLW.currentItem()))

    @Slot()
    def loadSlideShow(self):
        if self.ui.slideListLW.count() > 0:
            reply = QMessageBox.question(self.ui, 'Replace Slides', 'Are you sure you want replace the current slides?',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.ui.slideListLW.clear()

        fileName = QFileDialog.getOpenFileName(self.ui, "Load Slideshow",
                                    self.configDir,
                                    "Slide Shows (*.ssh)")

        # Read the JSON data from the file
        if fileName[0] != None:
            with open(fileName[0], 'r') as json_file:
                slideshow_data = json.load(json_file)

            for slide in slideshow_data.items():
                file = QFileInfo(slide[1])
                SlideWidget(file, self.ui.slideListLW)

    @Slot()
    def saveSlideShow(self):
        fileName = QFileDialog.getSaveFileName(self.ui, "Save Slide Show",
                                   self.configDir,
                                   "Slide Shows (*.ssh)")
        slide_data = {}
        for slide in range(self.ui.slideListLW.count()):
            slideName = "slide"+str(slide)
            slide_data[slideName] = self.ui.slideListLW.item(slide).imagePath()

        # Convert the Python dictionary to a JSON string
        json_data = json.dumps(slide_data, indent=2)

        # Write the JSON string to a file
        with open(fileName[0], 'w') as json_file:
            json_file.write(json_data)

    @Slot()
    def clearSlideShow(self):
        reply = QMessageBox.question(self.ui, 'Clear Slides', 'Are you sure you want clear all slides?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.slideListLW.clear()

    @Slot()
    def showSlideMain(self):
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
        self.currentSlide += 1
        slideCount = self.ui.slideListLW.count()
        if slideCount > 0:
            self.currentSlide = self.currentSlide % slideCount
            self.ui.slideListLW.setCurrentRow(self.currentSlide)
            self.showSlideMain()
        else:
            self.currentSlide = 0

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
        self.slideShowTimer.setInterval(self.secondsSettings.value()*1000)
        self.ui.slideListLW.setCurrentRow(self.currentSlide)
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

    # Media Seach Slots
    @Slot()
    def searchMedia(self):
        self.ui.mediaSearchResultsLW.clear()
        self.ui.mediaSearchPreviewLBL.clear()
        self.ui.mediaFileNameLBL.clear()
        foundMedia = self.mediaFileDatabase.searchMedia(self.ui.mediaSearchTagsLE.text(), self.ui.allMediaTagsCB.isChecked())
        for media in foundMedia:
            SlideWidget(QFileInfo(media), self.ui.mediaSearchResultsLW)

    @Slot()
    def setMediaLibrary(self):
        setDir = QFileDialog.getExistingDirectory(self.ui,
                "Select the Media Library location",
                self.mediaDir, QFileDialog.ShowDirsOnly)
        if setDir:
            self.mediaDir = setDir
            mediaCount = self.mediaFileDatabase.indexMedia(self.mediaDir)
            self.ui.mediaFilesCountLBL.setText(str(mediaCount))

    @Slot(SlideWidget)
    def previewSelectedMedia(self, slide):
        mediaInfo = slide.fileInfo()
        if mediaInfo.suffix().lower() == 'gif':
            movie = QMovie(slide.imagePath())
            if movie.isValid():
                movie.setSpeed(100)
                movie.setScaledSize(self.ui.mediaSearchPreviewLBL.size())
                self.ui.mediaSearchPreviewLBL.setMovie(movie)
                movie.start()
        else:
            pixmap = QPixmap()
            if pixmap.load(slide.imagePath()):
                if self.ui.stretchMainCB.isChecked():
                    self.ui.mediaSearchPreviewLBL.setPixmap(pixmap.scaled(self.ui.mediaSearchPreviewLBL.size()))
                else:
                    self.ui.mediaSearchPreviewLBL.setPixmap(pixmap.scaledToHeight(self.ui.mediaSearchPreviewLBL.size().height()))

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
        for sound in foundSounds:
            SlideWidget(QFileInfo(sound), self.ui.soundSearchResultsLW)

    @Slot()
    def setSoundLibrary(self):
        setDir = QFileDialog.getExistingDirectory(self.ui,
                "Select the Sound Library location",
                self.soundDir, QFileDialog.ShowDirsOnly)
        if setDir:
            self.soundDir = setDir
            soundsCount = self.mediaFileDatabase.indexSounds(self.soundDir)
            self.ui.soundFilesCountLBL.setText(str(soundsCount))

    @Slot()
    def soundBack(self):
        pass

    @Slot()
    def soundPlay(self):
        if self.ui.soundSearchResultsLW.currentItem() != None:
            self.sound.setSource(QUrl.fromLocalFile(self.ui.soundSearchResultsLW.currentItem().imagePath()))
            self.sound.play()


    @Slot()
    def soundPause(self):
        pass

    @Slot()
    def soundStop(self):
        if self.sound.playbackState() != QMediaPlayer.StoppedState:
            self.sound.stop()


    @Slot()
    def soundLoop(self):
        pass

    @Slot()
    def loadSoundQueue(self):
        if self.ui.slideListLW.count() > 0:
            reply = QMessageBox.question(self.ui, 'Replace Spunds', 'Are you sure you want replace the current queue?',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.ui.slideListLW.clear()

        fileName = QFileDialog.getOpenFileName(self.ui, "Load Sound Queue",
                                self.configFiles,
                                "Sound Queue Files(*.sfx)")

        # Read the JSON data from the file
        if fileName[0] != None:
            with open(fileName[0], 'r') as json_file:
                sound_data = json.load(json_file)

            for sound in sound_data.items():
                file = QFileInfo(sound[1])
                SlideWidget(file, self.ui.soundQueueLW)

    @Slot()
    def saveSoundQueue(self):
        fileName = QFileDialog.getSaveFileName(self.ui, "Save Sound Queue",
                                   self.configFiles,
                                   "Sound Queue Files(*.sfx)")
        sound_data = {}
        for sound in range(self.ui.soundQueueLW.count()):
            soundName = "sound"+str(sound)
            sound_data[soundName] = self.ui.soundQueueLW.item(sound).imagePath()

        # Convert the Python dictionary to a JSON string
        json_data = json.dumps(sound_data, indent=2)

        # Write the JSON string to a file
        with open(fileName[0], 'w') as json_file:
            json_file.write(json_data)

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

    @Slot("QMediaPlayer::Error", str)
    def playerError(self, error, error_string):
        print(error_string, file=sys.stderr)
        self.show_status_message(error_string)

    # Miscellaneous Buttons
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
