# utilities.py
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMainWindow, QLabel
from PySide6.QtCore import Qt

def style_sheet(color):
    style = f"background: rgb({color.red()},{color.green()},{color.blue()}); color:"
    if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
        style += "white"
    else:
        style += "black"

    return style

def team_font(color):
    if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
        return QColor(Qt.white)

    return QColor(Qt.black)

# Capture the given QMainWindow and display it on the QLabel
def capture_window(window: QMainWindow, preview_label: QLabel):
    pixmap = window.grab()  # Grab the content of the QMainWindow
    scaled_pixmap = pixmap.scaled(
        preview_label.size(),
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    preview_label.setPixmap(scaled_pixmap)
