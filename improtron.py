# This Python file uses the following encoding: utf-8
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from ImproTronControlBoard import ImproTronControlBoard
from PySide6.QtMultimedia import (QAudioInput, QCamera, QCameraDevice,
                                    QImageCapture, QMediaCaptureSession,
                                    QMediaDevices, QMediaMetaData,
                                    QMediaRecorder, QMediaPlayer, QAudioOutput)
#export QT_LOGGING_RULES="qt.pyside.libpyside.warning=true"

# Commands to use in the build process
# venv\Scripts\activate.bat
# venv\Scripts\pyside6-deploy -c ImproTron.spec
# venv\Scripts\pyside6-rcc -g python ImproTronIcons.qrc > ImproTronIcons.py
# venv\Scripts\pyside6-uic ImproTronControlBoard.ui -o ui_ImproTronControlBoard.py
# venv\Scripts\pyside6-uic ImproTron.ui -o ui_ImproTron.py

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Get the party started
    improTronControlBoard = ImproTronControlBoard()

    sys.exit(app.exec())
