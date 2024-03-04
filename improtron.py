# This Python file uses the following encoding: utf-8
import sys
from PySide6.QtWidgets import QApplication
from ImproTronControlBoard import ImproTronControlBoard

#export QT_LOGGING_RULES="qt.pyside.libpyside.warning=true"

# Commands to use in the build process
# venv\Scripts\activate.bat
# venv\Scripts\pyside6-deploy -c ImproTron.spec
# venv\Scripts\pyside6-rcc -g python ImproTronIcons.qrc > ImproTronIcons.py

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Get the party started
    improTronControlBoard = ImproTronControlBoard()

    sys.exit(app.exec())
