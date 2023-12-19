# This Python file uses the following encoding: utf-8
import sys
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QImageReader, QPixmap, QFont
from PySide6.QtWidgets import QApplication, QColorDialog, QFileDialog, QFileSystemModel
from PySide6.QtCore import QDir, QStandardPaths, Slot, Qt
from Improtronics import ImproTron, MonitorInfoApp, HotButtonManager
from audioPlayer import AudioPlayer
#export QT_LOGGING_RULES="qt.pyside.libpyside.warning=true"

@Slot()
def pickLeftTeamColor():
    color_chooser = QColorDialog()
    colorSelected = color_chooser.getColor(title = 'Pick Left Team Color')
    if (colorSelected.red()*0.299 + colorSelected.green()*0.587 + colorSelected.blue()*0.114) < 186:
        buttonCSS = f"QPushButton {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QPushButton {{color:white}}"
        labelCSS = f"QLabel {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QLabel {{color:white}}"
    else:
        buttonCSS = f"QPushButton {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QPushButton {{color:black}}"
        labelCSS = f"QLabel {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QLabel {{color:black}}"

    improTronControlBoard.colorLeftPB.setStyleSheet(buttonCSS)
    display.colorizeLeftScore(labelCSS)

@Slot()
def pickRightTeamColor():
    color_chooser = QColorDialog()
    colorSelected = color_chooser.getColor(title = 'Pick Right Team Color')
    if (colorSelected.red()*0.299 + colorSelected.green()*0.587 + colorSelected.blue()*0.114) < 186:
        buttonCSS = f"QPushButton {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QPushButton {{color:white}}"
        labelCSS = f"QLabel {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QLabel {{color:white}}"
    else:
        buttonCSS = f"QPushButton {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QPushButton {{color:black}}"
        labelCSS = f"QLabel {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QLabel {{color:black}}"

    improTronControlBoard.colorRightPB.setStyleSheet(buttonCSS)
    display.colorizeRightScore(labelCSS)

@Slot()
def pickRightTextColor():
    color_chooser = QColorDialog()
    colorSelected = color_chooser.getColor(title = 'Pick Right Team Color')
    if (colorSelected.red()*0.299 + colorSelected.green()*0.587 + colorSelected.blue()*0.114) < 186:
        buttonCSS = f"QPushButton {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QPushButton {{color:white}}"
        labelCSS = f"QLabel {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QLabel {{color:white}}"
    else:
        buttonCSS = f"QPushButton {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QPushButton {{color:black}}"
        labelCSS = f"QLabel {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QLabel {{color:black}}"

    improTronControlBoard.rightTextColorPB.setStyleSheet(buttonCSS)
    display.colorizeTextDisplay(labelCSS)

@Slot()
def blackout():
    display.blackout()

@Slot()
def pickLeftTextColor():
    color_chooser = QColorDialog()
    colorSelected = color_chooser.getColor(title = 'Pick Left Team Color')
    if (colorSelected.red()*0.299 + colorSelected.green()*0.587 + colorSelected.blue()*0.114) < 186:
        buttonCSS = f"QPushButton {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QPushButton {{color:white}}"
        labelCSS = f"QLabel {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QLabel {{color:white}}"
    else:
        buttonCSS = f"QPushButton {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QPushButton {{color:black}}"
        labelCSS = f"QLabel {{background: rgb({colorSelected.red()},{colorSelected.green()},{colorSelected.blue()})}} QLabel {{color:black}}"

    improTronControlBoard.leftTextColorPB.setStyleSheet(buttonCSS)
    display.colorizeTextDisplay(labelCSS)

@Slot(int)
def textFontSize(size):
    display.sizeTextDisplay(size)

@Slot(QFont)
def textFontChanged(new_font):
    display.sizeTextFont(new_font)

@Slot()
def getImageFile():
    dialog = QFileDialog(improTronControlBoard)
    locations = QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)
    directory = locations[-1] if locations else QDir.currentPath()
    dialog.setDirectory(directory)
    fileName = QFileDialog.getOpenFileName(improTronControlBoard, "Open Image", "" , "Image Files (*.png *.jpg *.bmp)")
    reader = QImageReader(fileName[0])
    reader.setAutoTransform(True)
    newImage = reader.read()

    # Scale to match the preview
    improTronControlBoard.imagePreview.setPixmap(QPixmap.fromImage(newImage.scaled(improTronControlBoard.imagePreview.size())))
    display.showImage(newImage)

@Slot()
def showScores():
    display.updateScores(improTronControlBoard.teamScoreLeft.value(),improTronControlBoard.teamScoreRight.value())

@Slot(str)
def showLeftTeam(teamName):
    display.showLeftTeam(teamName)

@Slot(str)
def showRightTeam(teamName):
    display.showRightTeam(teamName)

@Slot()
def showLeftText():
    display.showText(improTronControlBoard.leftTextBox.toPlainText())

@Slot()
def showRightText():
    display.showText(improTronControlBoard.rightTextBox.toPlainText())

# Messages used to prototype
# @Slot()
# def showScreens():
#    screen = QApplication. primaryScreen()
#    print(screen.name(), screen.model(), screen.manufacturer())
#    for siblingScreen in screen.virtualSiblings():
#        print(siblingScreen.name(), siblingScreen.model(), siblingScreen.manufacturer())
#    rectangle = screen.virtualGeometry()
#    print(rectangle.top(), rectangle.bottom(), rectangle.left(), rectangle.right())

@Slot()
def showFullScreen():
    display.maximize()

@Slot()
def showNormal():
    display.restore()

@Slot()
def getImageList():
    path = QFileDialog.getExistingDirectory(improTronControlBoard, "Select Image Directory")
    model.index(path)

if __name__ == "__main__":
    loader = QUiLoader()
    app = QApplication(sys.argv)
    model = QFileSystemModel()
    model.setRootPath(QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0])

    improTronControlBoard = loader.load("ImproTronControlPanel.ui", None)
    imageSearchList = improTronControlBoard.imageSearchList
    imageSearchList.setModel(model)
    imageSearchList.setRootIndex(model.index(QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0]))
    display = ImproTron()

    # Connect Score related signals to slots
    improTronControlBoard.colorRightPB.clicked.connect(pickRightTeamColor)
    improTronControlBoard.colorLeftPB.clicked.connect(pickLeftTeamColor)
    improTronControlBoard.showScorePB.clicked.connect(showScores)

    # Connect Team Name updates
    improTronControlBoard.teamNameLeft.textEdited.connect(showLeftTeam)
    improTronControlBoard.teamNameRight.textEdited.connect(showRightTeam)

    # Connect info (text and images) message updates
    improTronControlBoard.leftShowText.clicked.connect(showLeftText)
    improTronControlBoard.rightShowText.clicked.connect(showRightText)
    improTronControlBoard.loadImagePB.clicked.connect(getImageFile)

    # Connect Show Text Config elements
    improTronControlBoard.rightTextColorPB.clicked.connect(pickRightTextColor)
    improTronControlBoard.leftTextColorPB.clicked.connect(pickLeftTextColor)
    improTronControlBoard.blackOutPB.clicked.connect(blackout)
    improTronControlBoard.leftFontSize.valueChanged.connect(textFontSize)
    improTronControlBoard.fontComboBoxLeft.currentFontChanged.connect(textFontChanged)

    # Prototype buttons used for experimenting
    improTronControlBoard.resetTimerPB.clicked.connect(showFullScreen)
    improTronControlBoard.startTimerPB.clicked.connect(showNormal)
    improTronControlBoard.searchImagesPB.clicked.connect(getImageList)

    hot_buttonsmanager = HotButtonManager(improTronControlBoard, display)

    #monitor_info_app = MonitorInfoApp()
    #audio_player = AudioPlayer()

    #screens = app.screens()
    #print('Screen', len(screens))
    #one way; with two screens
    #if len(screens) > 1:
    #    screen = screens[1]
    #else:
    #    screen = screens[0]
    #size = screens[0].size()
    #print('0: width', size.width(), 'height', size.height())

    #size = screens[1].size()
    #print('1: width', size.width(), 'height', size.height())


    # Another way to remove primary screen and choose from remaining screens
    # current_screen = app.primaryScreen()
    # screens.remove(current_screen)
    # screen = screens[0]

    #qr = screen.geometry()
    #improTronControlBoard.move(qr.left(), qr.top())
    improTronControlBoard.setWindowFlags(
        Qt.WindowMinimizeButtonHint |
        Qt.WindowMaximizeButtonHint |
        Qt.WindowCloseButtonHint |
        Qt.WindowStaysOnTopHint |
        Qt.WindowTitleHint
        )
    improTronControlBoard.show()

    sys.exit(app.exec())
