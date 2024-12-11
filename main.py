# This Python file uses the following encoding: utf-8
import sys
import logging
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox
from ImproTronControlBoard import ImproTronControlBoard
#export QT_LOGGING_RULES="qt.pyside.libpyside.warning=true"

# Commands to use in the build process
# venv\Scripts\activate.bat
# venv\Scripts\pyside6-deploy -c ImproTron.spec
# venv\Scripts\pyside6-rcc -g python ImproTronIcons.qrc > ImproTronIcons.py
# venv\Scripts\pyside6-uic ImproTronControlBoard.ui -o ui_ImproTronControlBoard.py
# venv\Scripts\pyside6-uic ImproTron.ui -o ui_ImproTron.py

# Set the logging configuration
logging.basicConfig(
    level = logging.ERROR,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers =[
        logging.FileHandler(QStandardPaths.standardLocations(QStandardPaths.GenericConfigLocation)[0]+"/ImproTron/improton_error.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Call the default excepthook on KeyboardInterrupt and exit the program
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    # Log the exception
    logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

class ImproTronApplication(QApplication):
    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception as e:
            logging.critical('Uncaught exception during event processing!', exc_info=true)
            raise e

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Get the party started
    improTronControlBoard = ImproTronControlBoard()

    sys.exit(app.exec())
