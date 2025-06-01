import sys
import os
import logging
import argparse
import traceback
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication
from ImproTronControlBoard import ImproTronControlBoard

# Commands to use in the build process
#
# .qtcreator\Python_3_12_10venv\Scripts\activate
# .qtcreator\Python_3_12_10venv\Scripts\pyside6-deploy -c ImproTron.spec
# .qtcreator\Python_3_12_10venv\Scripts\pyside6-rcc -g python ImproTronIcons.qrc > ImproTronIcons.py
# .qtcreator\Python_3_12_10venv\Scripts\pyside6-uic ImproTronControlBoard.ui -o ui_ImproTronControlBoard.py
# .qtcreator\Python_3_12_10venv\Scripts\pyside6-uic ImproTron.ui -o ui_ImproTron.py

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical(
        "Uncaught exception:\n"
        "Type: %s\nValue: %s\nTraceback: %s",
        exc_type.__name__, str(exc_value), ''.join(traceback.format_tb(exc_traceback)),
        exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = handle_exception

# The determination of the location duplicates Settings. For a fresh install the first log file may not be in the config directory
def setup_logging():
    log_dir_list = QStandardPaths.standardLocations(QStandardPaths.GenericConfigLocation)
    log_dir = log_dir_list[0] + "/ImproTron" if log_dir_list else os.path.join(os.getcwd(), "ImproTron")
    os.makedirs(log_dir, exist_ok=True)

    log_level = args.log_level or os.getenv("IMPROTRON_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=logging.getLevelName(log_level) if log_level in logging._nameToLevel else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "improton_error.log")),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    logging.info("ImproTron starting")
    logging.info("Environment Details: OS=%s, Python=%s", sys.platform, sys.version)

    app = QApplication(sys.argv)
    improTronControlBoard = ImproTronControlBoard()
    result = app.exec()
    del improTronControlBoard
    return result

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="ImproTron Application")
    parser.add_argument(
        "--log-level",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO.",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )
    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        print(f"Argument parsing error: {e}", file=sys.stderr)
        sys.exit(2)

    # Set up logging
    setup_logging()

    # Run the application
    sys.exit(main())
