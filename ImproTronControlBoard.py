# This Python file uses the following encoding: utf-8
import json
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QImageReader, QPixmap, QFont, QMovie, QColor
from PySide6.QtWidgets import QColorDialog, QFileDialog, QFileSystemModel, QMessageBox
from PySide6.QtCore import QDir, QStandardPaths, Slot, Qt, QTimer, QItemSelection, QFileInfo, QFile, QIODevice
from Improtronics import ThingzWidget, SlideWidget
import ImproTronIcons


class ImproTronControlBoard():
    def __init__(self, mainImprotron, auxiliaryImprotron, parent=None):

        self.mainDisplay = mainImprotron
        self.auxiliaryDisplay = auxiliaryImprotron
        loader = QUiLoader()
        self.ui = loader.load("ImproTronControlPanel.ui")

        self.model = QFileSystemModel()
        self.model.setRootPath(QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0])

        self.ui.imageSearchList.setModel(self.model)
        self.ui.imageSearchList.setRootIndex(self.model.index(QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0]))

        # Colors for Thingz list
        self.rightTeamBackground = QColor(Qt.white)
        self.rightTeamFont = QColor(Qt.black)
        self.leftTeamBackground = QColor(Qt.white)
        self.leftTeamFont = QColor(Qt.black)

        # Connect Score related signals to slots
        self.ui.colorRightPB.clicked.connect(self.pickRightTeamColor)
        self.ui.colorLeftPB.clicked.connect(self.pickLeftTeamColor)
        self.ui.showScoresMainPB.clicked.connect(self.showScoresMain)
        self.ui.showScoresBothPB.clicked.connect(self.showScoresBoth)
        self.ui.showScoresAuxiliaryPB.clicked.connect(self.showScoresAuxiliary)

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

        # Connect Show Text Config elements
        self.ui.rightTextColorPB.clicked.connect(self.pickRightTextColor)
        self.ui.leftTextColorPB.clicked.connect(self.pickLeftTextColor)
        self.ui.blackOutPB.clicked.connect(self.blackout)

        # Prototype buttons used for experimenting
        self.ui.resetTimerPB.clicked.connect(self.showFullScreen)
        self.ui.startTimerPB.clicked.connect(self.showNormal)
        self.ui.searchImagesPB.clicked.connect(self.getImageList)

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

        # selection changes will trigger a slot
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

        self.ui.setWindowFlags(
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint |

            Qt.WindowTitleHint
            )
        self.ui.show()

    def center(self, dialog):
            qr = self.ui.window().frameGeometry()
            #cp = appMain.MainWindow.geometry(self).center()
            #qr.moveCenter(cp)
            #self.move(qr.center())
            x = (qr.width() - dialog.width()) / 2
            y = (qr.height() - dialog.height()) / 2
            dialog.move(x,y)

    def findWidget(self, type, widgetName):
        return self.ui.findChild(type, widgetName)

    def showImageOnMain(self, imageFile):
        reader = QImageReader(imageFile)
        reader.setAutoTransform(True)
        newImage = reader.read()

        # Scale to match the preview
        self.ui.imagePreviewMain.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.imagePreviewMain.size())))
        self.mainDisplay.showImage(newImage)

    def getTextFile(self):
        dialog = QFileDialog(self.ui)
        locations = QStandardPaths.standardLocations(QStandardPaths.AppDataLocation)
        directory = locations[-1] if locations else QDir.currentPath()
        dialog.setDirectory(directory)
        fileName = QFileDialog.getOpenFileName(self.ui, "Open Text File", "" , "Text File (*.txt)")
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

    @Slot()
    def pickLeftTeamColor(self):
        color_chooser = QColorDialog(self.ui)
        self.leftTeamBackground = color_chooser.getColor(title = 'Pick Left Team Color')
        styleSheet = f"background: rgb({self.leftTeamBackground.red()},{self.leftTeamBackground.green()},{self.leftTeamBackground.blue()}); color:"
        if (self.leftTeamBackground.red()*0.299 + self.leftTeamBackground.green()*0.587 + self.leftTeamBackground.blue()*0.114) < 186:
            styleSheet += "white"
            self.leftTeamFont = QColor(Qt.white)
        else:
            styleSheet += "black"
            self.leftTeamFont = QColor(Qt.black)

        self.ui.colorLeftPB.setStyleSheet(styleSheet)
        self.ui.leftThingTeamRB.setStyleSheet(styleSheet)
        self.mainDisplay.colorizeLeftScore(styleSheet)
        self.auxiliaryDisplay.colorizeLeftScore(styleSheet)

    @Slot()
    def pickRightTeamColor(self):
        color_chooser = QColorDialog(self.ui)
        self.rightTeamBackground = color_chooser.getColor(title = 'Pick Right Team Color')
        styleSheet = f"background: rgb({self.rightTeamBackground.red()},{self.rightTeamBackground.green()},{self.rightTeamBackground.blue()}); color:"
        if (self.rightTeamBackground.red()*0.299 + self.rightTeamBackground.green()*0.587 + self.rightTeamBackground.blue()*0.114) < 186:
            styleSheet += "white"
            self.rightTeamFont = QColor(Qt.white)
        else:
            styleSheet += "black"
            self.rightTeamFont = QColor(Qt.black)

        self.ui.colorRightPB.setStyleSheet(styleSheet)
        self.ui.rightThingTeamRB.setStyleSheet(styleSheet)
        self.mainDisplay.colorizeRightScore(styleSheet)
        self.auxiliaryDisplay.colorizeRightScore(styleSheet)

    @Slot()
    def pickLeftTextColor(self):
        color_chooser = QColorDialog(self.ui)
        self.center(color_chooser)
        colorSelected = color_chooser.getColor(title = 'Pick Right Team Color')
        styleSheet = f"background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()}); color:"
        if (colorSelected.red()*0.299 + colorSelected.green()*0.587 + colorSelected.blue()*0.114) < 186:
            styleSheet += "white"
        else:
            styleSheet += "black"

        self.ui.leftTextColorPB.setStyleSheet(styleSheet)

    @Slot()
    def pickRightTextColor(self):
        color_chooser = QColorDialog(self.ui)
        self.center(color_chooser)
        colorSelected = color_chooser.getColor(title = 'Pick Right Text Box Color')
        styleSheet = f"background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()}); color:"
        if (colorSelected.red()*0.299 + colorSelected.green()*0.587 + colorSelected.blue()*0.114) < 186:
            styleSheet += "white"
        else:
            styleSheet += "black"

        self.ui.rightTextColorPB.setStyleSheet(styleSheet)

    @Slot()
    def blackout(self):
        self.mainDisplay.blackout()
        self.auxiliaryDisplay.blackout()

    @Slot()
    def getImageFileMain(self):
        dialog = QFileDialog(self.ui)
        locations = QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)
        directory = locations[-1] if locations else QDir.currentPath()
        dialog.setDirectory(directory)
        fileName = QFileDialog.getOpenFileName(self.ui, "Open Media", "" , "Media Files (*.png *.jpg *.bmp *.gif *.webp)")
        if not(fileName[0] == None):
            mediaInfo = QFileInfo(fileName[0])
            if mediaInfo.completeSuffix().lower() == 'gif':
                movie = QMovie(fileName[0])
                if movie.isValid():
                    print("Wait what?")
                    movie.setSpeed(100)
                    movie.setScaledSize(self.ui.imagePreviewMain.size())
                    self.ui.imagePreviewMain.setMovie(movie)
                    movie.start()
                    self.mainDisplay.showMovie(fileName[0])
            else:
                reader = QImageReader(fileName[0])
                reader.setAutoTransform(True)
                newImage = reader.read()

                # Scale to match the preview
                self.ui.imagePreviewMain.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.imagePreviewMain.size())))
                self.mainDisplay.showImage(newImage)

    @Slot()
    def getImageFileAuxiliary(self):
        dialog = QFileDialog(self.ui)
        locations = QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)
        directory = locations[-1] if locations else QDir.currentPath()
        dialog.setDirectory(directory)
        fileName = QFileDialog.getOpenFileName(self.ui, "Open Media", "" , "Media Files (*.png *.jpg *.bmp *.gif *.webp)")
        if not(fileName[0] == None):
            mediaInfo = QFileInfo(fileName[0])
            if mediaInfo.completeSuffix().lower() == 'gif':
                movie = QMovie(fileName[0])
                if movie.isValid():
                    print("Wait what?")
                    movie.setSpeed(100)
                    movie.setScaledSize(self.ui.imagePreviewAuxiliary.size())
                    self.ui.imagePreviewAuxiliary.setMovie(movie)
                    movie.start()
                    self.auxiliaryDisplay.showMovie(fileName[0])
            else:
                reader = QImageReader(fileName[0])
                reader.setAutoTransform(True)
                newImage = reader.read()

                # Scale to match the preview
                self.ui.imagePreviewMain.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.imagePreviewAuxiliary.size())))
                self.auxiliaryDisplay.showImage(newImage)
    @Slot()
    def loadTextboxLeft(self):
        textToLoad = self.getTextFile()
        if len(textToLoad) > 0:
            self.ui.leftTextBox.setText(textToLoad)

    @Slot()
    def loadTextboxRight(self):
        textToLoad = self.getTextFile()
        if len(textToLoad) > 0:
            self.ui.rightTextBox.setText(textToLoad)

    @Slot()
    def loadTextboxBoth(self):
        textToLoad = self.getTextFile()
        if len(textToLoad) > 0:
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
        self.mainDisplay.showText(self.ui.leftTextBox.toPlainText(), self.ui.leftTextColorPB.styleSheet(), font)

    @Slot()
    def showLeftTextAuxiliary(self):
        font = self.ui.fontComboBoxLeft.currentFont()
        font.setPointSize(self.ui.leftFontSize.value())
        self.auxiliaryDisplay.showText(self.ui.leftTextBox.toPlainText(), self.ui.leftTextColorPB.styleSheet(), font)

    @Slot()
    def showLeftTextBoth(self):
        self.showLeftTextMain()
        self.showLeftTextAuxiliary()

    @Slot()
    def showRightTextMain(self):
        font = self.ui.fontComboBoxRight.currentFont()
        font.setPointSize(self.ui.rightFontSize.value())
        self.mainDisplay.showText(self.ui.rightTextBox.toPlainText(), self.ui.rightTextColorPB.styleSheet(), font)
        print(self.ui.rightTextColorPB.styleSheet())

    @Slot()
    def showRightTextAuxiliary(self):
        font = self.ui.fontComboBoxRight.currentFont()
        font.setPointSize(self.ui.rightFontSize.value())
        self.auxiliaryDisplay.showText(self.ui.rightTextBox.toPlainText(), self.ui.rightTextColorPB.styleSheet(), font)

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

    @Slot()
    def showFullScreen(self):
        self.mainDisplay.maximize()

    @Slot()
    def showNormal(self):
        self.mainDisplay.restore()

    @Slot()
    def getImageList(self):
        path = QFileDialog.getExistingDirectory(self.ui, "Select Image Directory")
        self.model.index(path)

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
        self.mainDisplay.showText(self.listThingz())

    @Slot()
    def showThingzListAuxiliary(self):
        self.auxiliaryDisplay.showText(self.listThingz())

    @Slot()
    def showThingzListBoth(self):
        self.showThingzListMain()
        self.showThingzListAuxiliary()

    @Slot()
    def showThingMain(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            thingColor = currentThing.background().color()
            styleSheet = f"background: rgb({thingColor.red()},{thingColor.green()},{thingColor.blue()}); color:"
            if (thingColor.red()*0.299 + thingColor.green()*0.587 + thingColor.blue()*0.114) < 186:
                styleSheet += "white"
            else:
                styleSheet += "black"
            print(styleSheet)
            self.mainDisplay.showText(self.ui.thingzListLW.currentItem().thingData(), styleSheet)

    @Slot()
    def showThingAuxiliary(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            thingColor = currentThing.background().color()
            styleSheet = f"background: rgb({thingColor.red()},{thingColor.green()},{thingColor.blue()}); color:"
            if (thingColor.red()*0.299 + thingColor.green()*0.587 + thingColor.blue()*0.114) < 186:
                styleSheet += "white"
            else:
                styleSheet += "black"

            self.auxiliaryDisplay.showText(self.ui.thingzListLW.currentItem().thingData(), styleSheet)

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
                currentThing.setForeground(self.rightTeamFont)
                currentThing.setBackground(self.rightTeamBackground)
            else:
                currentThing.setForeground(self.leftTeamFont)
                currentThing.setBackground(self.leftTeamBackground)

        currentThing.toggleTeam()

    @Slot()
    def leftThingTeam(self):
        currentThing = self.ui.thingzListLW.currentItem()
        if currentThing != None:
            if currentThing.isLeftSideTeam():
                currentThing.setForeground(self.rightTeamFont)
                currentThing.setBackground(self.rightTeamBackground)
            else:
                currentThing.setForeground(self.leftTeamFont)
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
                newThing.setForeground(self.leftTeamFont)
                newThing.setBackground(self.leftTeamBackground)
                self.ui.rightThingTeamRB.setChecked(True)
            else:
                newThing = ThingzWidget(thingStr, False, self.ui.thingzListLW)
                newThing.setForeground(self.rightTeamFont)
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

        dialog = QFileDialog(self.ui)
        dialog.setDirectory('C:/Users/guywi/AppData/Local/ImproTron')
        fileName = QFileDialog.getOpenFileName(self.ui, "Load Slideshow",
                    "C:/Users/guywi/AppData/Local/ImproTron/default_slideshow.json" ,
                    "Config Files(*.json)")

        # Read the JSON data from the file
        with open(fileName[0], 'r') as json_file:
            slideshow_data = json.load(json_file)

        for slide in slideshow_data.items():
            file = QFileInfo(slide[1])
            SlideWidget(file, self.ui.slideListLW)

    @Slot()
    def saveSlideShow(self):
        dialog = QFileDialog(self.ui)
        dialog.setDirectory('C:/Users/guywi/AppData/Local/ImproTron')
        fileName = QFileDialog.getSaveFileName(self.ui, "Save Slide Show",
                                   "C:/Users/guywi/AppData/Local/ImproTron/default_slideshow.json",
                                   "Config Files (*.json)")
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
        reply = QMessageBox.question(self.controlBoard, 'Clear Slides', 'Are you sure you want clear all slides?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.slideListLW.clear()

    @Slot()
    def showSlideMain(self):
        if self.ui.slideListLW.currentItem() != None:
            reader = QImageReader(self.ui.slideListLW.currentItem().imagePath())
            reader.setAutoTransform(True)
            newImage = reader.read()

            self.mainDisplay.showImage(newImage)

    @Slot()
    def showSlideAuxiliary(self):
        if self.ui.slideListLW.currentItem() != None:
            reader = QImageReader(self.ui.slideListLW.currentItem().imagePath())
            reader.setAutoTransform(True)
            newImage = reader.read()

            self.auxiliaryDisplay.showImage(newImage)

    @Slot()
    def showSlideBoth(self):
        if self.ui.slideListLW.currentItem() != None:
            reader = QImageReader(self.ui.slideListLW.currentItem().imagePath())
            reader.setAutoTransform(True)
            newImage = reader.read()

            self.mainDisplay.showImage(newImage)
            self.auxiliaryDisplay.showImage(newImage)

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
