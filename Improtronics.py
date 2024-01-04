# The display is a container for all the possible features that can be displayed
# This Python file uses the following encoding: utf-8
import json
from PySide6.QtWidgets import QFileDialog, QPushButton, QMainWindow, QLineEdit, QLabel, QVBoxLayout, QWidget, QMessageBox, QListWidgetItem
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QDir, QStandardPaths, Slot, Qt
from PySide6.QtGui import QPixmap, QImage, QImageReader, QFont
from screeninfo import get_monitors

# Class to handle display on a separate monitor
class ImproTron(QMainWindow):
    def __init__(self, parent=None):
        super(ImproTron, self).__init__()
        self.setGeometry(300, 300, 300, 300)
        self.setWindowTitle("Display 1")
        self.loader = QUiLoader()
        self.improTron = self.loader.load("Improtron.ui", None)
        self.setCentralWidget(self.improTron)
        # Store some default text formating
        self.labelCSS = self.improTron.textDisplay.styleSheet()
        self.text_font = self.improTron.textDisplay.font()
        self.maximize()

    # Colorize the left score display
    def colorizeLeftScore(self, labelCSS):
        self.improTron.leftTeamLabel.setStyleSheet(labelCSS)
        self.improTron.leftScoreLCD.setStyleSheet(labelCSS)

    # Colorize the right score display
    def colorizeRightScore(self, labelCSS):
        self.improTron.rightTeamLabel.setStyleSheet(labelCSS)
        self.improTron.rightScoreLCD.setStyleSheet(labelCSS)

    # Colorize the right score display
    def colorizeTextDisplay(self, labelCSS):
        self.labelCSS = labelCSS
        self.improTron.textDisplay.setStyleSheet(self.labelCSS)

    # Clear the display to black
    def blackout(self):
        self.improTron.textDisplay.setStyleSheet("background:black; color:black")
        self.improTron.textDisplay.setText("blackout")
        self.improTron.setCurrentWidget(self.improTron.displayText)

    # Change the font size for the text
    @Slot(QFont)
    def sizeTextFont(self, new_font):
        size = self.text_font.pointSize()
        self.text_font = new_font
        self.text_font.setPointSize(size)
        self.improTron.textDisplay.setFont(self.text_font)

    # Change the font size for the text
    @Slot(int)
    def sizeTextDisplay(self, size):
        if size > 0:
            self.text_font.setPointSize(size)
            self.improTron.textDisplay.setFont(self.text_font)

    # Show Text on the disaply
    @Slot(str)
    def showText(self, text_msg):
        self.improTron.textDisplay.setText(text_msg)
        self.improTron.textDisplay.setStyleSheet(self.labelCSS)
        self.improTron.setCurrentWidget(self.improTron.displayText)

    # Show Text on the disaply
    @Slot(QImage)
    def showImage(self, arg):
        self.improTron.textDisplay.setPixmap(QPixmap.fromImage(arg.scaled(self.improTron.textDisplay.size())))
        self.improTron.setCurrentWidget(self.improTron.displayText)

    # Set the name of the Right Team
    @Slot(str)
    def showRightTeam(self, teamName):
        self.improTron.rightTeamLabel.setText(teamName)

    # Set the name of the Left Team
    @Slot(str)
    def showLeftTeam(self, teamName):
        self.improTron.leftTeamLabel.setText(teamName)

    # Update the scores on the score board
    @Slot(int, int)
    def updateScores(self, argLeft, argRight):
        self.improTron.leftScoreLCD.setText(str(argLeft))
        self.improTron.rightScoreLCD.setText(str(argRight))
        self.improTron.setCurrentWidget(self.improTron.displayScore)

    @Slot()
    def maximize(self):
        self.showFullScreen()

    @Slot()
    def restore(self):
        self.showNormal()
# End Class ImproTron


class HotButton():
    def __init__(self, button_number, controlBoard, improtron):

        self.button_number = button_number
        self.text = "Button "+str(button_number)
        self.control_board = controlBoard
        self.display = improtron
        # Take control of the actual button
        self.hot_button = controlBoard.improtronControlPanel.findChild(QPushButton, "hotPB" +str(button_number))
        self.hot_button.clicked.connect(self.hotButtonClicked)

        self.hot_button_title = controlBoard.improtronControlPanel.findChild(QLineEdit, "titleHotButton" +str(button_number))
        self.hot_button_title.textChanged.connect(self.hotButtonNameChange)
        self.hot_button_title.setText(self.text)

        self.hot_button_image_file = controlBoard.improtronControlPanel.findChild(QLineEdit, "imageFileTxt" +str(button_number))
        self.hot_button_image_file.setText("C:\\Users\\guywi\\OneDrive\\Pictures\\Roanoke\\PICT0339.JPG")

        self.hot_button_select_file = controlBoard.improtronControlPanel.findChild(QPushButton, "selectPB" +str(button_number))
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
        reader = QImageReader(self.hot_button_image_file.text())
        reader.setAutoTransform(True)
        newImage = reader.read()

        # Scale to match the preview
        self.control_board.imagePreviewLeft.setPixmap(QPixmap.fromImage(newImage.scaled(self.control_board.imagePreviewLeft.size())))
        self.control_board.imagePreviewRight.setPixmap(QPixmap.fromImage(newImage.scaled(self.control_board.imagePreviewRight.size())))
        self.display.showImage(newImage)

class HotButtonManager():
    # Instantiate the Hot Buttons via a Hot Button Object that takes care of the signal and slots
    # leveraging the naming convention
    def __init__(self, controlBoard, improtron):
        self.hot_buttons = [] #empty array
        self.number = 10      #number of hotbuttons
        self.file_name = "C:\\Users\\guywi\\AppData\\Local\\ImproTron\\improtron_hotbuttons.json"
        self.control_board = controlBoard

        for button in range(self.number):
            self.hot_buttons.append(HotButton(button+1, controlBoard, improtron))

        # Set a slot for the clear, load and save buttons
        controlBoard.hotButtonClearPB.clicked.connect(self.clearHotButtonsClicked)
        controlBoard.hotButtonLoadPB.clicked.connect(self.loadHotButtonsClicked)
        controlBoard.hotButtonSavePB.clicked.connect(self.saveHotButtonsClicked)

    @Slot()
    def clearHotButtonsClicked(self):
        for button in range(self.number):
            self.hot_buttons[button].clear()

    @Slot()
    def loadHotButtonsClicked(self):
        dialog = QFileDialog(self.control_board)
        dialog.setDirectory('C:/Users/guywi/AppData/Local/ImproTron')
        fileName = QFileDialog.getOpenFileName(self.control_board, "Load Hot Buttons",
                    "C:/Users/guywi/AppData/Local/ImproTron/improtron_hotbuttons.json" ,
                    "Config Files(*.json)")

        # Read the JSON data from the file
        with open(fileName[0], 'r') as json_file:
            button_data = json.load(json_file)

        for button in range(self.number):
            self.hot_buttons[button].load(button_data)

    @Slot()
    def saveHotButtonsClicked(self):
        dialog = QFileDialog(self.control_board)
        dialog.setDirectory('C:/Users/guywi/AppData/Local/ImproTron')
        fileName = QFileDialog.getSaveFileName(self.control_board, "Save Hot Buttons",
                                   "C:/Users/guywi/AppData/Local/ImproTron/improtron_hotbuttons.json",
                                   "Config Files (*.json)")
        button_data = {}
        for button in range(self.number):
            self.hot_buttons[button].save(button_data)

        # Convert the Python dictionary to a JSON string
        json_data = json.dumps(button_data, indent=2)

        print('file is', fileName)

        # Write the JSON string to a file
        with open(fileName[0], 'w') as json_file:
            json_file.write(json_data)

#Code for returning screen information

class MonitorInfoApp(QWidget):
    def __init__(self):
        super(MonitorInfoApp, self).__init__()

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Get a list of connected monitors
        monitors = get_monitors()

        if not monitors:
            layout.addWidget(QLabel("No monitors found"))
        else:
            for i, monitor in enumerate(monitors, 1):
                monitor_label = QLabel(f"Monitor {i}: {monitor.name}, {monitor.width}x{monitor.height} pixels, Primary{monitor.is_primary}")
                layout.addWidget(monitor_label)

        self.setLayout(layout)
        self.setWindowTitle("Monitor Information")
        self.show()

class ThingzWidget(QListWidgetItem):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self._title = title
        self._text = "Needs Substitutes"

    def title(self):
        return self._title

    def text(self):
        return self._text

    def thingData(self):
        return self._title + "\n" + self._text

    def updateSubstitutes(self, substitutesText):
        self._text = substitutesText

class ThingzListManager(QWidget):
    def __init__(self, controlBoard, improtron):
        super().__init__()

        self.controlBoard = controlBoard
        self.improTron = improtron

        # Connect Thingz Management
        controlBoard.thingzListLW.itemClicked.connect(self.show_selected_thing)
        controlBoard.addThingPB.clicked.connect(self.addThingtoList)
        controlBoard.thingNameTxt.returnPressed.connect(self.addThingtoList)
        controlBoard.removeThingPB.clicked.connect(self.removeThingfromList)
        controlBoard.clearThingzPB.clicked.connect(self.clearThingzList)
        controlBoard.thingzMoveUpPB.clicked.connect(self.thingzMoveUp)
        controlBoard.thingzMoveDownPB.clicked.connect(self.thingzMoveDown)
        controlBoard.thingTextEdit.textChanged.connect(self.updateThingsText)
        controlBoard.showThingLeftPB.clicked.connect(self.showThingLeft)
        controlBoard.showThingRightPB.clicked.connect(self.showThingLeft)
        controlBoard.showThingBothPB.clicked.connect(self.showThingLeft)

    @Slot()
    def showThingLeft(self):
        self.improTron.showText(self.controlBoard.thingzListLW.currentItem().thingData())

    @Slot()
    def showThingRight(self):
        self.improTron.showText(self.controlBoard.thingzListLW.currentItem().thingData())

    @Slot()
    def showThingBoth(self):
        pass
#        showThingLeft()
#        showThingRight()

    @Slot()
    def updateThingsText(self):
        self.controlBoard.thingzListLW.currentItem().updateSubstitutes(self.controlBoard.thingTextEdit.toPlainText())

    @Slot(ThingzWidget)
    def show_selected_thing(self, thing):
        # Display selected item's title and text in the editor
        self.controlBoard.thingFocusLBL.setText(thing.title())
        self.controlBoard.thingTextEdit.setPlainText(thing.text())
        self.currentThing = thing

    @Slot()
    def addThingtoList(self):
        thingStr = self.controlBoard.thingNameTxt.text()
        if len(thingStr) > 0:
            newThing = ThingzWidget(thingStr, self.controlBoard.thingzListLW)
            newThingFont = newThing.font()
            newThingFont.setPointSize(12)
            newThing.setFont(newThingFont)
            newThing.setFlags(newThing.flags() | Qt.ItemIsEditable)
            self.controlBoard.thingNameTxt.setText("")
            self.controlBoard.thingNameTxt.setFocus()

    @Slot()
    def thingzMoveDown(self):
        thingRow = self.controlBoard.thingzListLW.currentRow()
        if thingRow < 0:
            return
        thing = self.controlBoard.thingzListLW.takeItem(thingRow)
        self.controlBoard.thingzListLW.insertItem(thingRow+1,thing)
        self.controlBoard.thingzListLW.setCurrentRow(thingRow+1)

    @Slot()
    def thingzMoveUp(self):
        thingRow = self.controlBoard.thingzListLW.currentRow()
        if thingRow < 0:
            return
        thing = self.controlBoard.thingzListLW.takeItem(thingRow)
        self.controlBoard.thingzListLW.insertItem(thingRow-1,thing)
        self.controlBoard.thingzListLW.setCurrentRow(thingRow-1)

    @Slot()
    def removeThingfromList(self):
        self.controlBoard.thingzListLW.takeItem(self.controlBoard.thingzListLW.row(self.controlBoard.thingzListLW.currentItem()))

    @Slot()
    def clearThingzList(self):
        reply = QMessageBox.question(self.control_board, 'Clear Thingz', 'Are you sure you want clear all Thingz?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.controlBoard.thingzListLW.clear()



