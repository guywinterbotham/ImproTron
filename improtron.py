# This Python file uses the following encoding: utf-8
import sys
from PySide6.QtWidgets import QApplication
from Improtronics import ImproTron, HotButtonManager
from ImproTronControlBoard import ImproTronControlBoard

#export QT_LOGGING_RULES="qt.pyside.libpyside.warning=true"

# Commands to use in the build process
# venv\Scripts\activate.bet
# venv\Scripts\pyside6-deploy -c ImproTron.spec
# venv\Scripts\pyside6-rcc -g python ImproTronIcons.qrc > ImproTronIcons.py

if __name__ == "__main__":
    #from screeninfo import get_monitors
    # Get all connected monitors
    #monitors = get_monitors()
    # Print information about each monitor
    #for monitor in monitors:
    #    print("Screen {}:".format(monitor))
    #    print("  Width: {} pixels".format(monitor.width))
    #    print("  Height: {} pixels".format(monitor.height))
    #    print("  Position: {}x{}".format(monitor.x, monitor.y))
    #    print("  Aspect Ratio: {:.2f}".format(monitor.width / monitor.height))
    #    print()

    #format = QMediaFormat()
    #for codec in format.supportedAudioCodecs(QMediaFormat.Encode):
    #     print(QMediaFormat.audioCodecDescription(codec))

    app = QApplication(sys.argv)

    # Fire up some Improtrons and get the party started
    displayAuxiliary = ImproTron("Auxiliary Display")
    displayMain = ImproTron("Main Display")
    improTronControlBoard = ImproTronControlBoard(displayMain, displayAuxiliary)

    hot_buttons_manager = HotButtonManager(improTronControlBoard, displayMain, displayAuxiliary)

    sys.exit(app.exec())
