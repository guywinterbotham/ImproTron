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
    # The "Glass" body with the specular highlight
    score_bg = f"""
        qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 20),
        stop:0.1 {base_color_hex},
        stop:0.9 {base_color_hex},
        stop:1 #111)
    """

    inner_divider = ""
    if is_left:
        # This is your 4px "Glowing" divider
        inner_divider = """
            border-right: 4px solid qlineargradient(x1:0, y1:0, x2:0, y2:1,
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
        background-color: {score_bg};
        color: white;
        border-radius: 0px;
        qproperty-alignment: 'AlignCenter';
    """

    return name_style, score_style

def team_font(color):
    if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
        return QColor(Qt.white)

    return QColor(Qt.black)

# Capture the given QMainWindow and display it on the QLabel
def capture_window(window: QMainWindow, preview_label: QLabel):
    pixmap = window.grab()  # Grab the content of the QMainWindow
    scaled_pixmap = pixmap.scaled(
        preview_label.size(),
        Qt.IgnoreAspectRatio,
        Qt.SmoothTransformation,
    )
    preview_label.setPixmap(scaled_pixmap)

# Utility encapsulating the ui code to find widgets by name
def findWidget(ui, type, widgetName):
    return ui.findChild(type, widgetName)
