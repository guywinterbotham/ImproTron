# utilities.py
# This Python file uses the following encoding: utf-8

def styleSheet(color):
    style = f"background: rgb({color.red()},{color.green()},{color.blue()}); color:"
    if(color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) < 186:
        style += "white"
    else:
        style += "black"

    return style
