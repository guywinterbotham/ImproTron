# The display is a container for all the possible features that can be displayed
# This Python file uses the following encoding: utf-8
import json
from PySide6.QtWidgets import QFileDialog, QPushButton, QLineEdit, QListWidgetItem
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QDir, QStandardPaths, Slot, QTimer, QTime, Qt
from PySide6.QtGui import QPixmap, QMovie, QGuiApplication

# Class to handle display on a separate monitor
class ImproTron():
    def __init__(self, name, parent=None):
        super(ImproTron, self).__init__()

        self.loader = QUiLoader()
        self.improTron = self.loader.load("Improtron.ui", None)
        self.improTron.textDisplay.setText(name)
        self.improTron.setGeometry(300, 300, 300, 300)
        self.improTron.setWindowTitle(name)
        self.x = 0
        self.y = 0
        self.media = QPixmap()

        # Store some default text formating
        self.maximize()

        # Countdown Timer
        self.countdownTimer = QTimer()
        self.countdownTimer.timeout.connect(self.countdown)

        self.countdownTime = QTime(0,0,0)
        self.startingTime = QTime(0,0,0)
        self.redTime = QTime(0,0,0)
        self.timerVisible(False)
        self.improTron.countdownLCD.display("00:00:00")

    def shutdown(self):
        self.improtron.close()

    # Functions for the Countdown Timer
    def timerVisible(self, visible = False):
        self.improTron.countdownLCD.setVisible(visible)

    def timerStart(self, time, redTime):
        if not self.countdownTimer.isActive():
            self.countdownTime.setHMS(time.hour(), time.minute(), time.second())
            self.startingTime.setHMS(time.hour(), time.minute(), time.second())
            self.redTime.setHMS(redTime.hour(), redTime.minute(), redTime.second())
            self.improTron.countdownLCD.setStyleSheet("background:black; color: white")

            self.countdownTimer.start(1000)

    def timerPause(self):
        if self.countdownTimer.isActive():
            self.countdownTimer.stop()
        else:
            self.countdownTimer.start(1000)


    def timerReset(self, time, redTime):
        if self.countdownTimer.isActive():
            self.countdownTime.setHMS(time.hour(), time.minute(), time.second())
            self.startingTime.setHMS(time.hour(), time.minute(), time.second())
            self.redTime.setHMS(redTime.hour(), redTime.minute(), redTime.second())
            self.improTron.countdownLCD.setStyleSheet("background:black; color: white")

    @Slot()
    def countdown(self):
        self.countdownTime = self.countdownTime.addSecs(-1)
        text = self.countdownTime.toString("hh:mm:ss")

        # Blinking effect
        if (self.countdownTime.second() % 2) == 0:
            text = text.replace(":", " ")

        # Alert time - something is close to happening
        if self.countdownTime <= self.redTime:
            self.improTron.countdownLCD.setStyleSheet("background:black; color: red")

        # Timeout - when countime rolls over and goes to midnight then
        # it has timed out. However the default comparison logic will see the rolled
        # over time as greater than zero time. SO detect the rollover instead.
        if self.countdownTime > self.startingTime:
            self.countdownTimer.stop()
            return

        self.improTron.countdownLCD.display(text)


    # Colorize the Left score display
    def colorizeLeftScore(self, scoreStyle):
        self.improTron.leftTeamLabel.setStyleSheet(scoreStyle)
        self.improTron.leftScoreLCD.setStyleSheet(scoreStyle)

    # Colorize the Right score display
    def colorizeRightScore(self, scoreStyle):
        self.improTron.rightTeamLabel.setStyleSheet(scoreStyle)
        self.improTron.rightScoreLCD.setStyleSheet(scoreStyle)

    # Clear the text display and show
    def clearText(self):
        self.improTron.textDisplay.clear()
        self.improTron.setCurrentWidget(self.improTron.displayText)

        # Clear the display to black
    def blackout(self):
        self.improTron.textDisplay.setStyleSheet("background:black; color:black")
        self.improTron.textDisplay.setText("blackout")
        self.improTron.setCurrentWidget(self.improTron.displayText)

    # Show Text on the display
    def showText(self, text_msg, style=None, autoScale = False, font=None):
        if font != None:
            self.improTron.textDisplay.setFont(font)

        if style != None:
            self.improTron.textDisplay.setStyleSheet(style)

        # Figure out if the height of the text is going to bee too big and autoscale if needed
        fontMetrics = self.improTron.textDisplay.fontMetrics()
        textHeight = fontMetrics.size(Qt.TextExpandTabs,text_msg).height()
        textBoxHeight = self.improTron.textDisplay.rect().height()
        if (textHeight >= textBoxHeight) or autoScale:
            textBoxFont = self.improTron.textDisplay.font()
            newSize = max(1, int(textBoxFont.pointSize()*textBoxHeight/textHeight))
            textBoxFont.setPointSize(newSize)
            self.improTron.textDisplay.setFont(textBoxFont)

        self.improTron.textDisplay.setText(text_msg)
        self.improTron.setCurrentWidget(self.improTron.displayText)

    # Show an image on the disaply
    def showImage(self, fileName, stretch = True):
        if self.media.load(fileName):
            if stretch:
                self.improTron.textDisplay.setPixmap(self.media.scaled(self.improTron.textDisplay.size()))
            else:
                self.improTron.textDisplay.setPixmap(self.media.scaledToHeight(self.improTron.textDisplay.size().height()))

        self.improTron.setCurrentWidget(self.improTron.displayText)

    # Show an image on the from the clipboard
    def pasteImage(self, stretch = True):
        pixmap = QGuiApplication.clipboard().pixmap()
        if pixmap != None:
            if stretch:
                self.improTron.textDisplay.setPixmap(pixmap.scaled(self.improTron.textDisplay.size()))
            else:
                self.improTron.textDisplay.setPixmap(pixmap.scaledToHeight(self.improTron.textDisplay.size().height()))

            self.improTron.setCurrentWidget(self.improTron.displayText)

    # Show an movie on the disaply
    def showMovie(self, movieFile):
        movie = QMovie(movieFile)
        movie.setSpeed(100)
        movie.setScaledSize(self.improTron.textDisplay.size())
        self.improTron.textDisplay.setMovie(movie)
        movie.start()
        self.improTron.setCurrentWidget(self.improTron.displayText)

    # Set the name of the Left Team
    def showLeftTeam(self, teamName):
        self.improTron.leftTeamLabel.setText(teamName)

    # Set the name of the Right Team
    def showRightTeam(self, teamName):
        self.improTron.rightTeamLabel.setText(teamName)

    # Update the scores on the score board
    def updateScores(self, argLeft, argRight):
        self.improTron.leftScoreLCD.setText(str(argLeft))
        self.improTron.rightScoreLCD.setText(str(argRight))
        self.improTron.setCurrentWidget(self.improTron.displayScore)

    # Maximize on the screen where the improtron was moved to
    def maximize(self):
        flags = Qt.Window | Qt.FramelessWindowHint
        self.improTron.setWindowFlags(flags)
        self.improTron.showMaximized()

    # Return to a know size to facilitate movement
    def restore(self):
        flags = Qt.Window
        self.improTron.setWindowFlags(flags)
        self.improTron.setGeometry(300, 300, 300, 300)
        self.improTron.showNormal()
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
        self.hot_button_image_file.setText("C:\\Users\\guywi\\OneDrive\\Pictures\\Roanoke\\PICT0339.JPG")

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
        dialog = QFileDialog(self.control_board)
        locations = QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)
        directory = locations[-1] if locations else QDir.currentPath()
        dialog.setDirectory(directory)
        fileName = QFileDialog.getOpenFileName(self.control_board, "Open Image", "" , "Image Files (*.png *.jpg *.bmp)")
        if len(fileName[0])>0:
            self.hot_button_image_file.setText(fileName[0])

    @Slot()
    def hotButtonClicked(self):
        self.control_board.showImageOnMain(self.hot_button_image_file.text())

class HotButtonManager():
    # Instantiate the Hot Buttons via a Hot Button Object that takes care of the signal and slots
    # leveraging the naming convention
    def __init__(self, controlBoard, mainImproton, auxiliaryImproton):
        self.hot_buttons = [] #empty array
        self.number = 10      #number of hotbuttons
        self.file_name = "C:\\Users\\guywi\\AppData\\Local\\ImproTron\\improtron_hotbuttons.json"
        self.control_board = controlBoard

        for button in range(self.number):
            self.hot_buttons.append(HotButton(button+1, controlBoard))

        # Set a slot for the clear, load and save buttons
        hotButtonClearPB = controlBoard.findWidget(QPushButton,"hotButtonClearPB")
        hotButtonClearPB.clicked.connect(self.clearHotButtonsClicked)

        hotButtonLoadPB = controlBoard.findWidget(QPushButton,"hotButtonLoadPB")
        hotButtonLoadPB.clicked.connect(self.loadHotButtonsClicked)

        hotButtonSavePB = controlBoard.findWidget(QPushButton,"hotButtonSavePB")
        hotButtonSavePB.clicked.connect(self.saveHotButtonsClicked)

    @Slot()
    def clearHotButtonsClicked(self):
        for button in range(self.number):
            self.hot_buttons[button].clear()

    @Slot()
    def loadHotButtonsClicked(self):
        dialog = QFileDialog(self.control_board.ui)
        dialog.setDirectory('C:/Users/guywi/AppData/Local/ImproTron')
        fileName = QFileDialog.getOpenFileName(self.control_board.ui, "Load Hot Buttons",
                    "C:/Users/guywi/AppData/Local/ImproTron/improtron_hotbuttons.json" ,
                    "Config Files(*.json)")

        # Read the JSON data from the file
        with open(fileName[0], 'r') as json_file:
            button_data = json.load(json_file)

        for button in range(self.number):
            self.hot_buttons[button].load(button_data)

    @Slot()
    def saveHotButtonsClicked(self):
        #**** Bad encapsulation ****
        dialog = QFileDialog(self.control_board.ui)
        dialog.setDirectory('C:/Users/guywi/AppData/Local/ImproTron')
        fileName = QFileDialog.getSaveFileName(self.control_board.ui, "Save Hot Buttons",
                                   "C:/Users/guywi/AppData/Local/ImproTron/improtron_hotbuttons.json",
                                   "Config Files (*.json)")
        button_data = {}
        for button in range(self.number):
            self.hot_buttons[button].save(button_data)

        # Convert the Python dictionary to a JSON string
        json_data = json.dumps(button_data, indent=2)

        # Write the JSON string to a file
        with open(fileName[0], 'w') as json_file:
            json_file.write(json_data)

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

