# utilities.py
# This Python file uses the following encoding: utf-8
from PySide6.QtGui import QColor
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
