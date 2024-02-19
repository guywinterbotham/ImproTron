# This Python file uses the following encoding: utf-8
import sys
from PySide6.QtWidgets import QApplication
from Improtronics import ImproTron
from Settings import Settings
from ImproTronControlBoard import ImproTronControlBoard

#export QT_LOGGING_RULES="qt.pyside.libpyside.warning=true"

# Commands to use in the build process
# venv\Scripts\activate.bat
# venv\Scripts\pyside6-deploy -c ImproTron.spec
# venv\Scripts\pyside6-rcc -g python ImproTronIcons.qrc > ImproTronIcons.py

if __name__ == "__main__":
    app = QApplication(sys.argv)

    settings = Settings()

    # Fire up some Improtrons and get the party started
    displayAuxiliary = ImproTron("Auxiliary")
    displayMain = ImproTron("Main")
    improTronControlBoard = ImproTronControlBoard(displayMain, displayAuxiliary)

    sys.exit(app.exec())
