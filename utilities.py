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

def get_modern_styles(base_color_hex, is_left=True):
    # Balanced both sides:
    # Top reflection hits hard and tight (0.00 -> 0.05)
    # Bottom shadow mimics this by staying tight at the base (0.95 -> 1.00)
    score_bg = (
        f"qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 rgba(255, 255, 255, 30), "  # Top gloss
        f"stop:0.05 {base_color_hex}, "       # Solid team color starts
        f"stop:0.95 {base_color_hex}, "       # Solid team color ends (pushed lower!)
        f"stop:1.00 rgba(0, 0, 0, 180))"     # Tight, deep, semi-translucent shadow
    )

    inner_divider = ""
    if is_left:
        inner_divider = """
            border-right: 4px solid qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 0),
                stop:0.2 rgba(255, 255, 255, 150),
                stop:0.5 rgba(255, 255, 255, 230),
                stop:0.8 rgba(255, 255, 255, 150),
                stop:1.0 rgba(255, 255, 255, 0));
        """

    name_style = f"""
        background-color: #222;
        color: white;
        border-radius: 0px;
        border-bottom: 3px solid {base_color_hex};
        {inner_divider}
        font-weight: bold;
        padding: 0px 15px;
        margin-bottom: -1px;
    """

    score_style = f"""
        background: {score_bg};
        color: white;
        border-radius: 0px;
        qproperty-alignment: 'AlignCenter';
    """

    return name_style, score_style

def team_font(color):
    if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
        return QColor(Qt.white)

    return QColor(Qt.black)

# Utility encapsulating the ui code to find widgets by name
def findWidget(ui, type, widgetName):
    return ui.findChild(type, widgetName)
