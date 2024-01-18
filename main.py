# This Python file uses the following encoding: utf-8
import sys
from PySide6.QtWidgets import QApplication
from Improtronics import ImproTron, HotButtonManager
from ImproTronControlBoard import ImproTronControlBoard

#export QT_LOGGING_RULES="qt.pyside.libpyside.warning=true"

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Fire up some Improtrons and get the party started
    displayAuxiliary = ImproTron("Auxiliary Display")
    displayMain = ImproTron("Main Display")
    improTronControlBoard = ImproTronControlBoard(displayMain, displayAuxiliary)

    hot_buttons_manager = HotButtonManager(improTronControlBoard, displayMain, displayAuxiliary)

    #audio_player = AudioPlayer()

    sys.exit(app.exec())
