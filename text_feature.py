# text_feature.py
# This Python file uses the following encoding: utf-8
import csv
from PySide6.QtCore import QObject, Slot, QRegularExpression, QFile, QFileInfo, QIODevice
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtWidgets import QApplication, QStyle, QFileDialog, QColorDialog, QPushButton
import utilities

class TextFeature(QObject):
    MAX_FILE_LINES = 10

    def __init__(self, ui, settings, mainDisplay, auxiliaryDisplay):

        self.ui = ui
        self._settings = settings
        self.mainDisplay = mainDisplay
        self.auxiliaryDisplay = auxiliaryDisplay

        self.ui.clearLeftTextPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowLeft))
        self.ui.clearRightTextPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        self.ui.loadTextboxLeftPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowLeft))
        self.ui.loadTextboxRightPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))

        self.connect_slots()

    def connect_slots(self):
        # Connect text feature components
        self.ui.showLeftTextMainPB.clicked.connect(self.show_left_text_main)
        self.ui.showLeftTextAuxiliaryPB.clicked.connect(self.show_left_text_auxiliary)
        self.ui.showLeftTextBothPB.clicked.connect(self.show_left_text_both)
        self.ui.showRightTextMainPB.clicked.connect(self.show_right_text_main)
        self.ui.showRightTextAuxiliaryPB.clicked.connect(self.show_right_text_auxiliary)
        self.ui.showRightTextBothPB.clicked.connect(self.show_right_text_both)

        self.ui.clearLeftTextPB.clicked.connect(self.clear_left_text)
        self.ui.clearRightTextPB.clicked.connect(self.clear_right_text)

        self.ui.loadTextboxLeftPB.clicked.connect(self.load_textbox_left)
        self.ui.loadTextboxRightPB.clicked.connect(self.load_textbox_right)

        # Connect show_ Text Config elements
        self.ui.rightTextColorPB.clicked.connect(self.pick_right_text_color)
        self.ui.leftTextColorPB.clicked.connect(self.pick_left_text_color)

        # Ininialize preset color boxes from dialog custom colors.
        for i in range(1, 9):
            getattr(self.ui, f"leftColorPreset{i}").clicked.connect(
                lambda _, btn=getattr(self.ui, f"leftColorPreset{i}"): self.use_color_preset(btn, self.ui.leftTextColorPB)
            )
            getattr(self.ui, f"rightColorPreset{i}").clicked.connect(
                lambda _, btn=getattr(self.ui, f"rightColorPreset{i}"): self.use_color_preset(btn, self.ui.rightTextColorPB)
            )

# End Connections

    def use_color_preset(self, button, target):
            style = button.styleSheet()
            self.set_text_box_color(target, style)

    def get_text_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self.ui, "Open Text File", self._settings.getDocumentDir(), "Text File (*.txt)")
        if not file_name:
            return None

        file_info = QFileInfo(file_name)
        self._settings.setDocumentDir(file_info.absolutePath())
        file = QFile(file_name)
        if not file.open(QIODevice.ReadOnly | QIODevice.Text):
            QMessageBox.warning(self.ui, "Error", "Failed to open the file.")
            return None

        text = ""
        for _ in range(self.MAX_FILE_LINES):
            if file.atEnd():
                break
            text += file.readLine().data().decode("utf-8")
        return text

    # Text box color management
    def set_text_box_color(self, coloredButton, colorStyle):
        coloredButton.setStyleSheet(colorStyle)

    # Populate the preset color buttons with the presets defined in the color dialog
    def set_preset_colors(self):
        left_presets = QRegularExpression('leftColorPreset')
        right_presets = QRegularExpression('rightColorPreset')

        # Use the index provided by the QColorDialog. Cap at the max number of buttons
        max_color_presets = QColorDialog.customCount()

        colorIndex = 0
        for colorButton in self.ui.textDisplayTab.findChildren(QPushButton, left_presets):
            if colorIndex < max_color_presets:
                colorButton.setStyleSheet(utilities.style_sheet(QColorDialog.customColor(colorIndex)))

            colorIndex += 1

        colorIndex = 0
        for colorButton in self.ui.textDisplayTab.findChildren(QPushButton, right_presets):
            if colorIndex < max_color_presets:
                colorButton.setStyleSheet(utilities.style_sheet(QColorDialog.customColor(colorIndex)))

            colorIndex += 1

    @Slot()
    def pick_left_text_color(self):
        color_chooser = QColorDialog(self.ui)
        color_selected = color_chooser.getColor(title = 'Pick Left Text Box Color')

        # Update the presets incase one was changed while picking a color
        self.set_preset_colors()

        if color_selected != None:
            style = utilities.style_sheet(color_selected)
            self.set_text_box_color(self.ui.leftTextColorPB, style)

    @Slot()
    def pick_right_text_color(self):
        color_chooser = QColorDialog(self.ui)
        color_selected = color_chooser.getColor(title = 'Pick Right Text Box Color')

        # Update the presets incase one was changed while picking a color
        self.set_preset_colors()

        if color_selected.isValid():
            style = utilities.style_sheet(color_selected)
            self.set_text_box_color(self.ui.rightTextColorPB, style)

    @Slot()
    def show_left_text_main(self):
        font = self.ui.fontComboBoxLeft.currentFont()
        font.setPointSize(self.ui.leftFontSize.value())
        self.mainDisplay.show_text(self.ui.leftTextBox.toPlainText(), self.ui.leftTextColorPB.styleSheet(), font)
        self.ui.imagePreviewMain.clear()

    @Slot()
    def show_left_text_auxiliary(self):
        font = self.ui.fontComboBoxLeft.currentFont()
        font.setPointSize(self.ui.leftFontSize.value())
        self.auxiliaryDisplay.show_text(self.ui.leftTextBox.toPlainText(), self.ui.leftTextColorPB.styleSheet(), font)
        self.ui.imagePreviewAuxiliary.clear()

    @Slot()
    def show_left_text_both(self):
        self.show_left_text_main()
        self.show_left_text_auxiliary()

    @Slot()
    def show_right_text_main(self):
        font = self.ui.fontComboBoxRight.currentFont()
        font.setPointSize(self.ui.rightFontSize.value())
        self.mainDisplay.show_text(self.ui.rightTextBox.toPlainText(), self.ui.rightTextColorPB.styleSheet(), font)
        self.ui.imagePreviewMain.clear()

    @Slot()
    def show_right_text_auxiliary(self):
        font = self.ui.fontComboBoxRight.currentFont()
        font.setPointSize(self.ui.rightFontSize.value())
        self.auxiliaryDisplay.show_text(self.ui.rightTextBox.toPlainText(), self.ui.rightTextColorPB.styleSheet(), font)
        self.ui.imagePreviewAuxiliary.clear()

    @Slot()
    def show_right_text_both(self):
        self.show_right_text_main()
        self.show_right_text_auxiliary()

    @Slot()
    def clear_left_text(self):
        self.ui.leftTextBox.clear()

    @Slot()
    def clear_right_text(self):
        self.ui.rightTextBox.clear()

    @Slot()
    def load_textbox_left(self):
        text = self.get_text_file()
        if text != None:
            self.ui.leftTextBox.setText(text)

    @Slot()
    def load_textbox_right(self):
        text = self.get_text_file()
        if text != None:
            self.ui.rightTextBox.setText(text)
