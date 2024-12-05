# text_feature.py
# This Python file uses the following encoding: utf-8
import csv
from PySide6.QtCore import QObject, Slot, QRegularExpression, QFile, QFileInfo, QIODevice
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtWidgets import QApplication, QStyle, QFileDialog, QColorDialog, QPushButton
import utilities

class text_feature(QObject):
    def __init__(self, ui, settings, mainDisplay, auxiliaryDisplay):

        self.ui = ui
        self._settings = settings
        self.mainDisplay = mainDisplay
        self.auxiliaryDisplay = auxiliaryDisplay

        self.connect_slots()

    def connect_slots(self):
        # Connect text feature components
        self.ui.showLeftTextMainPB.clicked.connect(self.show_left_text_main)
        self.ui.showLeftTextAuxiliaryPB.clicked.connect(self.show_left_text_auxiliary)
        self.ui.showLeftTextBothPB.clicked.connect(self.show_left_text_both)
        self.ui.showRightTextMainPB.clicked.connect(self.show_right_text_main)
        self.ui.showRightTextAuxiliaryPB.clicked.connect(self.show_right_text_auxiliary)
        self.ui.showRightTextBothPB.clicked.connect(self.show_right_text_both)

        self.ui.clearLeftTextPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowLeft))
        self.ui.clearLeftTextPB.clicked.connect(self.clear_left_text)
        self.ui.clearRightTextPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        self.ui.clearRightTextPB.clicked.connect(self.clear_right_text)

        self.ui.loadTextboxLeftPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowLeft))
        self.ui.loadTextboxLeftPB.clicked.connect(self.load_textbox_left)
        self.ui.loadTextboxRightPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        self.ui.loadTextboxRightPB.clicked.connect(self.load_textbox_right)


        # Ininialize preset color boxes from dialog custom colors.
        self.set_preset_colors()
        self.ui.leftColorPreset1.clicked.connect(self.use_left_color_preset_1)
        self.ui.leftColorPreset2.clicked.connect(self.use_left_color_preset_2)
        self.ui.leftColorPreset3.clicked.connect(self.use_left_color_preset_3)
        self.ui.leftColorPreset4.clicked.connect(self.use_left_color_preset_4)
        self.ui.leftColorPreset5.clicked.connect(self.use_left_color_preset_5)
        self.ui.leftColorPreset6.clicked.connect(self.use_left_color_preset_6)
        self.ui.leftColorPreset7.clicked.connect(self.use_left_color_preset_7)
        self.ui.leftColorPreset8.clicked.connect(self.use_left_color_preset_8)

        self.ui.rightColorPreset1.clicked.connect(self.use_right_color_preset_1)
        self.ui.rightColorPreset2.clicked.connect(self.use_right_color_preset_2)
        self.ui.rightColorPreset3.clicked.connect(self.use_right_color_preset_3)
        self.ui.rightColorPreset4.clicked.connect(self.use_right_color_preset_4)
        self.ui.rightColorPreset5.clicked.connect(self.use_right_color_preset_5)
        self.ui.rightColorPreset6.clicked.connect(self.use_right_color_preset_6)
        self.ui.rightColorPreset7.clicked.connect(self.use_right_color_preset_7)
        self.ui.rightColorPreset8.clicked.connect(self.use_right_color_preset_8)

        # Connect show_ Text Config elements
        self.ui.rightTextColorPB.clicked.connect(self.pick_right_text_color)
        self.ui.leftTextColorPB.clicked.connect(self.pick_left_text_color)


# End Connections

    # Load a saved text file
    def get_text_file(self):
        file_name = QFileDialog.getOpenFileName(self.ui, "Open Text File", self._settings.getDocumentDir() , "Text File (*.txt)")
        if len(file_name[0]) > 0:
            file_info = QFileInfo(file_name[0])
            self._settings.setDocumentDir(file_info.absolutePath())

            file = QFile(file_name[0])
            if not file.open(QIODevice.ReadOnly | QIODevice.Text):
                return
            text = ""
            line_count = 0

            # To avoid reading in large files which couldn't be displayed anyway,
            # limit the lines to something reasonable
            while (line_count < 10) and (not file.atEnd()):
                text += file.readLine()
                line_count += 1
            return text
        else:
            return None

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
                colorButton.setStyleSheet(utilities.styleSheet(QColorDialog.customColor(colorIndex)))

            colorIndex += 1

        colorIndex = 0
        for colorButton in self.ui.textDisplayTab.findChildren(QPushButton, right_presets):
            if colorIndex < max_color_presets:
                colorButton.setStyleSheet(utilities.styleSheet(QColorDialog.customColor(colorIndex)))

            colorIndex += 1

    # Left side preset colors
    @Slot()
    def use_left_color_preset_1(self):
        style = self.ui.leftColorPreset1.styleSheet()
        self.set_text_box_color(self.ui.leftTextColorPB, style)

    @Slot()
    def use_left_color_preset_1(self):
        style = self.ui.leftColorPreset1.styleSheet()
        self.set_text_box_color(self.ui.leftTextColorPB, style)

    @Slot()
    def use_left_color_preset_2(self):
        style = self.ui.leftColorPreset2.styleSheet()
        self.set_text_box_color(self.ui.leftTextColorPB, style)

    @Slot()
    def use_left_color_preset_3(self):
        style = self.ui.leftColorPreset3.styleSheet()
        self.set_text_box_color(self.ui.leftTextColorPB, style)

    @Slot()
    def use_left_color_preset_4(self):
        style = self.ui.leftColorPreset4.styleSheet()
        self.set_text_box_color(self.ui.leftTextColorPB, style)

    @Slot()
    def use_left_color_preset_5(self):
        style = self.ui.leftColorPreset5.styleSheet()
        self.set_text_box_color(self.ui.leftTextColorPB, style)

    @Slot()
    def use_left_color_preset_6(self):
        style = self.ui.leftColorPreset6.styleSheet()
        self.set_text_box_color(self.ui.leftTextColorPB, style)

    @Slot()
    def use_left_color_preset_7(self):
        style = self.ui.leftColorPreset7.styleSheet()
        self.set_text_box_color(self.ui.leftTextColorPB, style)

    @Slot()
    def use_left_color_preset_8(self):
        style = self.ui.leftColorPreset8.styleSheet()
        self.set_text_box_color(self.ui.leftTextColorPB, style)


    @Slot()
    def pick_left_text_color(self):
        color_chooser = QColorDialog(self.ui)
        color_selected = color_chooser.getColor(title = 'Pick Left Text Box Color')

        # Update the presets incase one was changed while picking a color
        self.set_preset_colors()

        if color_selected != None:
            style = utilities.styleSheet(color_selected)
            self.set_text_box_color(self.ui.leftTextColorPB, style)

    # Right side preset colors
    @Slot()
    def use_right_color_preset_1(self):
        style = self.ui.rightColorPreset1.styleSheet()
        self.set_text_box_color(self.ui.rightTextColorPB, style)

    @Slot()
    def use_right_color_preset_1(self):
        style = self.ui.rightColorPreset1.styleSheet()
        self.set_text_box_color(self.ui.rightTextColorPB, style)

    @Slot()
    def use_right_color_preset_2(self):
        style = self.ui.rightColorPreset2.styleSheet()
        self.set_text_box_color(self.ui.rightTextColorPB, style)

    @Slot()
    def use_right_color_preset_3(self):
        style = self.ui.rightColorPreset3.styleSheet()
        self.set_text_box_color(self.ui.rightTextColorPB, style)

    @Slot()
    def use_right_color_preset_4(self):
        style = self.ui.rightColorPreset4.styleSheet()
        self.set_text_box_color(self.ui.rightTextColorPB, style)

    @Slot()
    def use_right_color_preset_5(self):
        style = self.ui.rightColorPreset5.styleSheet()
        self.set_text_box_color(self.ui.rightTextColorPB, style)

    @Slot()
    def use_right_color_preset_6(self):
        style = self.ui.rightColorPreset6.styleSheet()
        self.set_text_box_color(self.ui.rightTextColorPB, style)

    @Slot()
    def use_right_color_preset_7(self):
        style = self.ui.rightColorPreset7.styleSheet()
        self.set_text_box_color(self.ui.rightTextColorPB, style)

    @Slot()
    def use_right_color_preset_8(self):
        style = self.ui.rightColorPreset8.styleSheet()
        self.set_text_box_color(self.ui.rightTextColorPB, style)


    @Slot()
    def pick_right_text_color(self):
        color_chooser = QColorDialog(self.ui)
        color_selected = color_chooser.getColor(title = 'Pick Right Text Box Color')

        # Update the presets incase one was changed while picking a color
        self.set_preset_colors()

        if color_selected.isValid():
            style = utilities.styleSheet(color_selected)
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
