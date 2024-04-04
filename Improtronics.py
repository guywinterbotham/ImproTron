# The display is a container for all the possible features that can be displayed
# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import QPushButton, QLineEdit, QListWidgetItem, QStyle, QApplication, QMainWindow
from PySide6.QtCore import Slot, Qt, QUrl, QObject
from PySide6.QtGui import QPixmap, QMovie, QGuiApplication, QImageReader, QIcon
from PySide6.QtMultimedia import QSoundEffect
from Timer import CountdownTimer
from ui_ImproTron import Ui_ImproTron

# Class to handle display on a separate monitor
class ImproTron(QMainWindow):
    def __init__(self, name, parent=None):
        super(ImproTron, self).__init__()

        self._screen_number = 0
        self._display_name = name

        self.ui = Ui_ImproTron()
        self.ui.setupUi(self)

        self.media = QPixmap()

    # Countdown Timer Passthrough controls
        self._timer = CountdownTimer(self._display_name+" Timer")

    def timerStart(self, time, redTime):
        self._timer.start(time, redTime)

    def timerPause(self):
        self._timer.pause()

    def timerReset(self, time, redTime):
        self._timer.reset(time, redTime)

    def shutdown(self):
        self.close()

    # Functions for the Countdown Timer
    def timerVisible(self, visible = False):
        self._timer.showTimer(self.frameGeometry(), visible)

    # Colorize the Left score display
    def colorizeLeftScore(self, scoreStyle):
        self.ui.leftTeamLabel.setStyleSheet(scoreStyle)
        self.ui.leftScoreLCD.setStyleSheet(scoreStyle)

    # Colorize the Right score display
    def colorizeRightScore(self, scoreStyle):
        self.ui.rightTeamLabel.setStyleSheet(scoreStyle)
        self.ui.rightScoreLCD.setStyleSheet(scoreStyle)

    # Clear the text display and show
    def clearText(self):
        self.ui.textDisplay.clear()
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayText)

        # Clear the display to black
    def blackout(self):
        self.ui.textDisplay.setStyleSheet("background:black; color:white")
        self.ui.textDisplay.clear()
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayText)

    # Show Text on the display
    def showText(self, text_msg, style=None, font=None):
        if font != None:
            self.ui.textDisplay.setFont(font)

        if style != None:
            self.ui.textDisplay.setStyleSheet(style)

        # Figure out if the height of the text is going to be too big and autoscale if needed
        fontMetrics = self.ui.textDisplay.fontMetrics()
        textHeight = fontMetrics.size(Qt.TextExpandTabs,text_msg).height()
        textWidth = fontMetrics.size(Qt.TextExpandTabs,text_msg).width()

        textBoxHeight = self.ui.textDisplay.rect().height()
        textBoxWidth = self.ui.textDisplay.rect().width()

        heightRatio = textHeight/textBoxHeight
        widthRatio  = textWidth/textBoxWidth

        # Determine whether the text scaling is most needed for the height or width
        scaleHeight = False
        scaleWidth = False

        if textHeight >= textBoxHeight: # Text is higher than the display box
            scaleHeight = True
        if textWidth >= textBoxWidth: # Text is wider than the display box
            scaleWidth = True

        # The text fits in neither direction. Scale based on the worst case.
        if scaleHeight and scaleWidth:

            if heightRatio > widthRatio:
                scaleHeight = True
                scaleWidth = False
            else:
                scaleHeight = False
                scaleWidth = True

        # Some scaling has to occur so pull the font out and scale
        if scaleHeight or scaleWidth:
            textBoxFont = self.ui.textDisplay.font()
            if scaleHeight:
                newSize = max(1, int(textBoxFont.pointSize()/heightRatio))
                textBoxFont.setPointSize(newSize)
            if scaleWidth:
                newSize = max(1, int(textBoxFont.pointSize()/widthRatio))
                textBoxFont.setPointSize(newSize)

            self.ui.textDisplay.setFont(textBoxFont) # and put it back

        self.ui.textDisplay.setText(text_msg)
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayText)

    # Show an static slide on the display
    def showSlide(self, image, stretch = True):
        if image:
            if stretch:
                self.ui.textDisplay.setPixmap(QPixmap.fromImage(image.scaled(self.ui.textDisplay.size())))
            else:
                self.ui.textDisplay.setPixmap(QPixmap.fromImage(image.scaledToHeight(self.ui.textDisplay.size().height())))
            self.ui.stackedWidget.setCurrentWidget(self.ui.displayText)

    # Show an image on the display
    def showImage(self, fileName, stretch = True):
        if len(fileName) >0:
            reader = QImageReader(fileName)
            reader.setAutoTransform(True)
            newImage = reader.read()

            if newImage:
                if stretch:
                    self.ui.textDisplay.setPixmap(QPixmap.fromImage(newImage.scaled(self.ui.textDisplay.size())))
                else:
                    self.ui.textDisplay.setPixmap(QPixmap.fromImage(newImage.scaledToHeight(self.ui.textDisplay.size().height())))
                self.ui.stackedWidget.setCurrentWidget(self.ui.displayText)

    # Show an image on the from the clipboard
    def pasteImage(self, stretch = True):
        pixmap = QGuiApplication.clipboard().pixmap()
        if pixmap != None:
            if stretch:
                self.ui.textDisplay.setPixmap(pixmap.scaled(self.ui.textDisplay.size()))
            else:
                self.ui.textDisplay.setPixmap(pixmap.scaledToHeight(self.ui.textDisplay.size().height()))

            self.ui.stackedWidget.setCurrentWidget(self.ui.displayText)

    # Show an movie on the disaply
    def showMovie(self, movieFile):
        if len(movieFile) > 0:
            movie = QMovie(movieFile)
            movie.setSpeed(100)
            movie.setScaledSize(self.ui.textDisplay.size())
            self.ui.textDisplay.setMovie(movie)
            movie.start()
            self.ui.stackedWidget.setCurrentWidget(self.ui.displayText)

    # Set the name of the Left Team
    def showLeftTeam(self, teamName):
        self.ui.leftTeamLabel.setText(teamName)

    # Set the name of the Right Team
    def showRightTeam(self, teamName):
        self.ui.rightTeamLabel.setText(teamName)

    # Update the scores on the score board
    def updateScores(self, argLeft, argRight):
        self.ui.leftScoreLCD.setText(str(argLeft))
        self.ui.rightScoreLCD.setText(str(argRight))
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayScore)

    # Flip to the video player and return the widget to connect the video play to
    def showVideo(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayVideo)
        return self.ui.videoPlayer

    # Flip to the video player and return the widget to connect the video play to
    def showCamera(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayCamera)
        return self.ui.cameraPlayer

    # Return the location to persist
    def getLocation(self):
        return self.pos()

    # Move to the location
    def setLocation(self, q):
        self.move(q)

    # Maximize on the screen where the improtron was moved to
    def maximize(self):
        flags = Qt.Window | Qt.FramelessWindowHint
        self.setWindowFlags(flags)
        self.showMaximized()

    # Restore and move the alloted screen
    def restore(self):
        self.showText(self._display_name)
        self.setWindowTitle(self._display_name)

        flags = Qt.Window
        self.setWindowFlags(flags)
        self.showNormal()

    # End Class ImproTron


class HotButton():
    def __init__(self, button_number, controlBoard):

        self.button_number = button_number
        self.text = "Button "+str(button_number)
        self.control_board = controlBoard

        # Take control of the actual button
        self.hot_button = controlBoard.findWidget(QPushButton, "hotPB" +str(button_number))
        self.hot_button.clicked.connect(self.hotButtonClicked)

        self.hot_button_title = controlBoard.findWidget(QLineEdit, "titleHotButton" +str(button_number))
        self.hot_button_title.textChanged.connect(self.hotButtonNameChange)
        self.hot_button_title.setText(self.text)

        self.hot_button_image_file = controlBoard.findWidget(QLineEdit, "imageFileTxt" +str(button_number))
        self.hot_button_image_file.setText("")

        self.hot_button_select_file = controlBoard.findWidget(QPushButton, "selectPB" +str(button_number))
        self.hot_button_select_file.clicked.connect(self.selectImage)

    def clear(self):
        self.hot_button_image_file.clear()
        self.hot_button_title.clear()
        self.text = "Button "+str(self.button_number)
        self.hot_button.setText(self.text)

    def save(self, hot_buttons_json):
        hot_buttons_json[self.hot_button_title.objectName()] = self.hot_button_title.text()
        hot_buttons_json[self.hot_button_image_file.objectName()] = self.hot_button_image_file.text()

    def load(self, hot_buttons_json):
        self.hot_button_title.setText(hot_buttons_json[self.hot_button_title.objectName()])
        self.hot_button_image_file.setText(hot_buttons_json[self.hot_button_image_file.objectName()])

    @Slot(str)
    def hotButtonNameChange(self,new_name):
        self.hot_button.setText(new_name)
        self.text = new_name

    @Slot()
    def selectImage(self):
        fileName = self.control_board.selectImageFile()
        if fileName != None:
            self.hot_button_image_file.setText(fileName)

    @Slot()
    def hotButtonClicked(self):
        self.control_board.showMediaOnMain(self.hot_button_image_file.text())

# SoundFX Pallette Management. This class handles loading of a saved queue and converting
# and WAV files contained into sound effect buttons
class SoundFX():
    def __init__(self, sfx_button):

        self.sfx_button = sfx_button
        self.soundFX = QSoundEffect()

        # Take control of the actual button
        self.sfx_button.clicked.connect(self.soundFXButtonClicked)

    @Slot(str)
    def loadSoundEffect(self, new_SoundFX):

        self.sfx_button.setIcon(QIcon())
        self.sfx_button.setText(new_SoundFX.baseName())
        self.soundFX.setSource(QUrl.fromLocalFile(new_SoundFX.absoluteFilePath()))

        self.sfx_button.setEnabled(True)

    # Assumes a value btween 0-1
    @Slot(str)
    def setFXVolume(self, value):
        self.soundFX.setVolume(value)

    @Slot(str)
    def disable(self):
        self.sfx_button.setText("")
        self.sfx_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.sfx_button.setEnabled(False)

    @Slot()
    def soundFXButtonClicked(self):
        if self.soundFX.isPlaying():
            self.soundFX.stop()
        else:
            self.soundFX.play()

# Subclass to maintain the additional substitutes information associated with a Thing
class ThingzWidget(QListWidgetItem):
    def __init__(self, title, isLeftSideTeam, parent=None):
        super().__init__(title, parent)

        self._substitutes = ""
        self._isLeftSideTeam = isLeftSideTeam

    def substitutes(self):
        return self._substitutes

    def thingData(self):
        return self.text() + "\n\n" + self._substitutes

    def updateSubstitutes(self, substitutesText):
        self._substitutes = substitutesText

    def isLeftSideTeam(self):
        return self._isLeftSideTeam

    def toggleTeam(self):
        self._isLeftSideTeam = not self._isLeftSideTeam

# To Do
# Have file model filter for all supported image file types
# implement the show fwd reverse functions
# do a json file file save and load, although the load could be fun without the file info.
# add some try excpet handling around the load for when files have been removed
class SlideWidget(QListWidgetItem):
    def __init__(self, imageFileInfo, parent=None):
        super().__init__(imageFileInfo.fileName(), parent)

        self._fileInto = imageFileInfo
        newSlideFont = self.font()
        newSlideFont.setPointSize(12)
        self.setFont(newSlideFont)

    def title(self):
        return self.text()

    def fileInfo(self):
        return self._fileInto

    def imagePath(self):
        return self._fileInto.absoluteFilePath()

# Used during slide shows and Whammy to load images aynchronously
class SlideLoaderThread(QObject):

    def __init__(self):
        super(SlideLoaderThread, self).__init__()
        self.reader = QImageReader()
        self.reader.setAutoTransform(True)
        self.newImage = None

    @Slot(str)
    def loadSlide(self, fileName):
        self.reader.setFileName(fileName)
        self.newImage = self.reader.read()

    @Slot()
    def getSlide(self):
        return self.newImage
