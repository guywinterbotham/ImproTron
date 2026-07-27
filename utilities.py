# utilities.py
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

def style_sheet(color):
    style = f"background: rgb({color.red()},{color.green()},{color.blue()}); color:"
    if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
        style += "white"
    else:
        style += "black"

    return style

def lighten_color(hex_color: str, factor: float = 0.4) -> str:
    """Lightens a hex color string towards white."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    try:
        r, g, b = [int(hex_color[i : i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return "#FFFFFF"

    r_new = int(r + (255 - r) * factor)
    g_new = int(g + (255 - g) * factor)
    b_new = int(b + (255 - b) * factor)
    return f"#{r_new:02X}{g_new:02X}{b_new:02X}"


def darken_color(hex_color: str, factor: float = 0.4) -> str:
    """Darkens a hex color string towards black (for rich bottom ambient shadow)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    try:
        r, g, b = [int(hex_color[i : i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return "#000000"

    r_new = int(r * (1.0 - factor))
    g_new = int(g * (1.0 - factor))
    b_new = int(b * (1.0 - factor))
    return f"#{r_new:02X}{g_new:02X}{b_new:02X}"


def get_modern_styles(base_color_hex, is_left=True):
    # Derived colors for 3D curvature
    top_highlight = lighten_color(base_color_hex, factor=0.50)
    top_gloss = lighten_color(base_color_hex, factor=0.25)
    bottom_shadow = darken_color(base_color_hex, factor=0.45)

    # Perfectly balanced 3D block gradient:
    score_bg = (
        f"qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, "
        f"stop:0.00 #FFFFFF, "            # Crisp specular top edge
        f"stop:0.02 {top_highlight}, "    # Bright 3D highlight curve
        f"stop:0.08 {top_gloss}, "        # Soft gloss falloff
        f"stop:0.15 {base_color_hex}, "   # Full vibrant team color starts
        f"stop:0.85 {base_color_hex}, "   # Full vibrant team color ends
        f"stop:0.95 {bottom_shadow}, "   # Rich ambient shadow (team-tinted)
        f"stop:1.00 rgba(0, 0, 0, 200))"  # Deep bottom rim lip
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
        background-color: #222222;
        color: white;
        border-radius: 0px;
        border-bottom: 3px solid {base_color_hex};
        {inner_divider}
        font-weight: bold;
        padding: 0px 15px;
        margin-bottom: 0px;
    """

    score_style = f"""
        background: {score_bg};
        color: white;
        border: none;
        border-radius: 0px;
        qproperty-alignment: 'AlignCenter';
    """

    return name_style, score_style

def team_font(color):
    if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
        return QColor(Qt.GlobalColor.white)

    return QColor(Qt.GlobalColor.black)

# Utility encapsulating the ui code to find widgets by name
def findWidget(ui, type, widgetName):
    return ui.findChild(type, widgetName)
