# The display is a container for all the possible features that can be displayed
import logging

from PySide6.QtWidgets import QPushButton, QLineEdit, QListWidgetItem, QStyle, QApplication, QMainWindow
from PySide6.QtCore import Slot, Signal, Qt, QUrl, QObject, QEvent
from PySide6.QtGui import QPixmap, QMovie, QGuiApplication, QImageReader, QIcon, QFontMetrics, QColor, QPainter
from PySide6.QtMultimedia import QSoundEffect

import utilities
from Timer import CountdownTimer
from ui_ImproTron import Ui_ImproTron

logger = logging.getLogger(__name__)

# Class to handle display on a separate monitor
class ImproTron(QMainWindow):
    def __init__(self, name, parent=None):
        super(ImproTron, self).__init__()

        self._screen_number = 0
        self.shutting_down = False # used to flag a controlled shutdown to be able to filter a user accidentally clsong the window
        self._display_name = name

        self.ui = Ui_ImproTron()
        self.ui.setupUi(self)
        logger.info(f"Loading display {name}")

        self.media = QPixmap()
        self.movie = QMovie() # Keep the memory allocated
        self.movie.setSpeed(100)

        logger.info(f"About to force a score update {name}")
        self.updateScores(0.0, 0.0) # Force a font scaling

    # Countdown Timer Passthrough controls
        self._timer = CountdownTimer(self._display_name+" Timer")

    def timerStart(self, time, redTime):
        self._timer.start(time, redTime)

    def timerPause(self):
        self._timer.pause()

    def timerReset(self, time, redTime):
        self._timer.reset(time, redTime)

    def shutdown(self):
        self.shutting_down = True

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
        self.movie.stop()
        self.ui.textDisplay.setStyleSheet("background:black; color:white")
        self.ui.textDisplay.clear()
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayText)

    # Show Text on the display
    def show_text(self, text_msg, style=None, font=None):
        self.movie.stop()
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

        self.ui.textDisplay.clear()
        self.ui.textDisplay.setText(text_msg)
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayText)

    # Show an static slide on the display
    def showSlide(self, image, stretch = True):
        self.movie.stop()
        if image:
            self.blackout() # Clears the display and sets it to the current tab
            if stretch:
                self.ui.textDisplay.setPixmap(QPixmap.fromImage(image.scaled(self.ui.textDisplay.size())))
            else:
                self.ui.textDisplay.setPixmap(QPixmap.fromImage(image.scaledToHeight(self.ui.textDisplay.size().height())))

    # Show a background then over lay text using a font and ratio to the display
    def showGame(self, image, text, font, scale, textColor = QColor("black")):
        self.movie.stop()
        if image:
            self.blackout() # Clears the display and sets it to the current tab
            pixmap = QPixmap.fromImage(image.scaled(self.ui.textDisplay.size()))
            # Create a QPainter to draw text on the image
            painter = QPainter(pixmap)
            painter.setPen(textColor)  # Set text color
            baseFontWidth = float(font.pixelSize())

            # Scale the the text so that it its width is the percentage given by the slider.
            fontMetrics = QFontMetrics(font)
            pixelsWide = fontMetrics.horizontalAdvance(text) # Get text length at baseline pixel setting

            # Now we need k such that k*(pw/bw) = slider/100 since slider was set up to represent a percent
            # Therefore k = (slider*bw)/(pw*100). This is used to adjust the font setting
            newFontPixelSize = int(baseFontWidth * (scale*self.ui.textDisplay.rect().width())/(100.0*pixelsWide))
            font.setPixelSize(newFontPixelSize)
            painter.setFont(font)    # Use the selected game text font
            painter.drawText(pixmap.rect(), Qt.AlignCenter, text)  # Draw text centered
            painter.end()
            self.ui.textDisplay.setPixmap(pixmap)

    # Show an image on the display
    def showImage(self, image, stretch = True):
        self.movie.stop()
        if image:
            self.blackout() # Clears the display and sets it to the current tab
            if stretch:
                self.ui.textDisplay.setPixmap(QPixmap.fromImage(image.scaled(self.ui.textDisplay.size())))
            else:
                self.ui.textDisplay.setPixmap(QPixmap.fromImage(image.scaledToHeight(self.ui.textDisplay.size().height())))

    # Show an image on the from the clipboard
    def pasteImage(self, stretch = True):
        self.movie.stop()
        pixmap = QGuiApplication.clipboard().pixmap()
        if pixmap != None:
            self.blackout() # Clears the display and sets it to the current tab
            if stretch:
                self.ui.textDisplay.setPixmap(pixmap.scaled(self.ui.textDisplay.size()))
            else:
                self.ui.textDisplay.setPixmap(pixmap.scaledToHeight(self.ui.textDisplay.size().height()))

    # Show an pixel map on the from a drop event on the preview
    def dropImage(self, pixmap, stretch = True):
        self.movie.stop()
        if pixmap != None:
            self.blackout() # Clears the display and sets it to the current tab
            if stretch:
                self.ui.textDisplay.setPixmap(pixmap.scaled(self.ui.textDisplay.size()))
            else:
                self.ui.textDisplay.setPixmap(pixmap.scaledToHeight(self.ui.textDisplay.size().height()))

    # Show an movie on the disaply
    def showMovie(self, movieFile):
        if len(movieFile) > 0:
            self.movie.stop()
            self.blackout() # Clears the display and sets it to the current tab
            self.movie.setFileName(movieFile)
            self.movie.setScaledSize(self.ui.textDisplay.size())
            self.ui.textDisplay.setMovie(self.movie)
            self.movie.start()

    # Find the optimal width for the team name
    def find_optimal_team_font_size(self, nameLabel):
        # Get the team name
        labelText = nameLabel.text()

        fontMetrics = nameLabel.fontMetrics()
        textWidth = fontMetrics.horizontalAdvance(labelText)
        textHeight = fontMetrics.boundingRect(labelText).height()

        # If the string is empty, don't scale as it result in a divide by zero
        if textHeight == 0 or textWidth == 0:
            return

        labelRect = nameLabel.rect()
        labelHeight = labelRect.height() - 30 # as a margin
        labelWidth = labelRect.width() - 50 # as a margin

        heightRatio = textHeight/labelHeight
        widthRatio  = textWidth/labelWidth

        scaleByF = 1.0

        # Case 1: Text would fully fit inside the QLabel. Scale up by the smallest ratio. That is the one that
        # increases the size in one direction that is almost the right scale
        if textHeight <= labelHeight and textWidth <= labelWidth:
            scaleByF = 1/max(heightRatio, widthRatio)

        # Case 2: The text is outside the label on both sides. Find the most aggregious side and scale down by that
        # Since the ratios will be by definition > 1, invert them
        if textHeight > labelHeight and textWidth > labelWidth:
            scaleByF = 1/max(heightRatio, widthRatio)

        # Case 3a: The text is too high so scale down by the height ratio
        if textHeight > labelHeight and  textWidth <= labelWidth:
            scaleByF = 1/heightRatio

        # Case 3b: The text is too wide so scale down by the width ratio
        if textHeight <= labelHeight and  textWidth > labelWidth:
            scaleByF = 1/widthRatio

        textBoxFont = nameLabel.font()
        originalSize = textBoxFont.pointSize()
        newSize = int(originalSize * scaleByF)

        if (abs(originalSize-newSize) < 3): # Ignore very small changes that will cause the string to oscillate in size
            newSize = originalSize
        textBoxFont.setPointSize(newSize)
        nameLabel.setFont(textBoxFont) # and put it back


    # Set the name of the Left Team
    def showLeftTeam(self, teamName):

        self.ui.leftTeamLabel.setText(teamName)

        # Determine the font size needed to fit the text in the label width
        self.find_optimal_team_font_size(self.ui.leftTeamLabel)


    # Set the name of the Right Team
    def showRightTeam(self, teamName):

        self.ui.rightTeamLabel.setText(teamName)

        # Determine the font size needed to fit the text in the label width
        self.find_optimal_team_font_size(self.ui.rightTeamLabel)

    # Update the scores on the score board
    def updateScores(self, argLeft, argRight):
        # Trim the fractional part if it is zero
        if argLeft.is_integer():
            self.ui.leftScoreLCD.setText(str(int(argLeft)))
        else:
            self.ui.leftScoreLCD.setText(str(argLeft))

        if argRight.is_integer():
            self.ui.rightScoreLCD.setText(str(int(argRight)))
        else:
            self.ui.rightScoreLCD.setText(str(argRight))

        self.ui.stackedWidget.setCurrentWidget(self.ui.displayScore)

        # Set the background image and style for the score labels
        style = """
            QLabel {{
                background-image: url(icons/yesand.png);
                background-color: rgba(0, 0, 0, 0.5);
                color: white;
            }}
        """
        self.ui.leftTeamLabel.setStyleSheet(style)
        self.ui.rightTeamLabel.setStyleSheet(style)
        self.ui.leftScoreLCD.setStyleSheet(style)
        self.ui.rightScoreLCD.setStyleSheet(style)


        # Force a resize after display so as to ensure the final dimensions are locked it
        # Changing before viewing for the first time doesn't work due the stacked tab not being fully initialized
        self.find_optimal_team_font_size(self.ui.leftTeamLabel)
        self.find_optimal_team_font_size(self.ui.rightTeamLabel)
        self.find_optimal_team_font_size(self.ui.leftScoreLCD)
        self.find_optimal_team_font_size(self.ui.rightScoreLCD)

    # Flip to the video player and return the widget to connect the video play to
    def showVideo(self):
        self.movie.stop() # Stop a GIF if it is playing
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayVideo)
        return self.ui.videoPlayer

    # Flip to the video player and return the widget to connect the video play to
    def showCamera(self):
        self.movie.stop() # Stop a GIF if it is playing
        self.ui.stackedWidget.setCurrentWidget(self.ui.displayCamera)
        return self.ui.cameraPlayer

    # Return the location to persist
    def get_location(self):
        return self.pos()

    # Move to the location
    def set_location(self, q):
        self.move(q)

    # Maximize on the screen where the improtron was moved to
    def maximize(self):
        flags = Qt.Window | Qt.FramelessWindowHint
        self.setWindowFlags(flags)
        self.showMaximized()

    # Restore and move the alloted screen
    def restore(self):
        self.show_text(self._display_name)
        self.setWindowTitle(self._display_name)

        flags = Qt.Window
        self.setWindowFlags(flags)
        self.showNormal()

    def closeEvent(self, event):
        # Override closeEvent to prevent accidental closure
        if not self.shutting_down:
            event.ignore()
# End Class ImproTron

class HotButtonHandler(QObject):
    mainMediaShow = Signal(str)    # Custom signal that decouples the media display from controlboard
    auxMediaShow  = Signal(str)    # Custom signal that decouples the media display from controlboard
    def __init__(self, button_number, ui, media_features):

        super(HotButtonHandler,self).__init__()

        self.button_number = button_number
        self.text = "Button "+str(button_number)
        self.media_features = media_features

        # Take control of the actual button
        self.hot_button = utilities.findWidget(ui, QPushButton, "hotPB" +str(button_number))
        self.hot_button.installEventFilter(self)

        self.hot_button_title = utilities.findWidget(ui, QLineEdit, "titleHotButton" +str(button_number))
        self.hot_button_title.textChanged.connect(self.hotButtonNameChange)
        self.hot_button_title.setText(self.text)

        self.hot_button_image_file = utilities.findWidget(ui, QLineEdit, "imageFileTxt" +str(button_number))
        self.hot_button_image_file.setText("")

        self.hot_button_select_file = utilities.findWidget(ui, QPushButton, "selectPB" +str(button_number))
        self.hot_button_select_file.clicked.connect(self.selectImage)

    # Allow for right and left click actions
    def eventFilter(self, obj, event):
        if obj is self.hot_button and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.mainMediaShow.emit(self.hot_button_image_file.text())
                return True
            elif event.button() == Qt.RightButton:
                self.auxMediaShow.emit(self.hot_button_image_file.text())
                return True
        return False  # Pass the event to the default handler

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
        fileName = self.media_features.select_image_file()
        if fileName != None:
            self.hot_button_image_file.setText(fileName)

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
    def set_fx_volume(self, value):
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

# Class to hold Slide info useful in maintaining list of images
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
