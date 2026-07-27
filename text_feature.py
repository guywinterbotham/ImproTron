# text_feature.py
import logging
import re
from PySide6.QtCore import QObject, Slot, QRegularExpression, QFile, QFileInfo, QIODevice, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QStyle, QFileDialog, QColorDialog, QPushButton, QMessageBox
import utilities

logger = logging.getLogger(__name__)

class TextFeature(QObject):
    MAX_FILE_LINES = 10

    def __init__(self, ui, settings, mainDisplay, auxiliaryDisplay):

        self.ui = ui
        self._settings = settings
        self.mainDisplay = mainDisplay
        self.auxiliaryDisplay = auxiliaryDisplay

        self.right_text_color = self._settings.get_right_text_color()
        self.ui.rightTextColorPB.setStyleSheet(utilities.style_sheet(self.right_text_color))

        self.left_text_color = self._settings.get_left_text_color()
        self.ui.leftTextColorPB.setStyleSheet(utilities.style_sheet(self.left_text_color))

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

        # Pull the preset colors onto the selection buttons
        self.set_preset_colors()

        # Connect preset color boxes so they change the color selection button.
        for i in range(1, 9):
            getattr(self.ui, f"leftColorPreset{i}").clicked.connect(
                lambda _, btn=getattr(self.ui, f"leftColorPreset{i}"): self.use_left_color_preset(btn)
            )
            getattr(self.ui, f"rightColorPreset{i}").clicked.connect(
                lambda _, btn=getattr(self.ui, f"rightColorPreset{i}"): self.use_right_color_preset(btn)
            )


# End Connections
    def get_text_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self.ui, "Open Text File", self._settings.get_document_directory(), "Text File (*.txt)")
        if not file_name:
            return None

        file_info = QFileInfo(file_name)
        self._settings.set_document_directory(file_info.absolutePath())
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

    # Text box color extraction from preset buttons
    def parse_stle(self, colorStyle):

        # 1. Extract the background value
        bg_match = re.search(r'background(?:-color)?\s*:\s*([^;]+)', colorStyle)
        if not bg_match:
            logger.error(f"No background property found in: {colorStyle}")
            return

        color_str = bg_match.group(1).strip()
        new_color = QColor()

        # 2. Parse based on format
        if 'rgb' in color_str:
            # Extract digits: finds all numbers in 'rgb(255, 85, 0)' -> ['255', '85', '0']
            nums = re.findall(r'\d+', color_str)
            if len(nums) >= 3:
                new_color = QColor(int(nums[0]), int(nums[1]), int(nums[2]))
        else:
            # Fallback for hex (#RRGGBB) or named colors (red, blue)
            new_color = QColor(color_str)

        # 4. Safety check and save
        if not new_color.isValid():
            logger.error(f"Final attempt to parse '{color_str}' failed.")
            return QColor(Qt.GlobalColor.black)
        else:
            return new_color

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

    # Functions called by preset color buttons
    @Slot(QPushButton)
    def use_left_color_preset(self, button):
            style = button.styleSheet()
            self.ui.leftTextColorPB.setStyleSheet(style)
            self.left_text_color = self.parse_stle(style)

    @Slot(QPushButton)
    def use_right_color_preset(self, button):
            style = button.styleSheet()
            self.ui.rightTextColorPB.setStyleSheet(style)
            self.right_text_color = self.parse_stle(style)

    @Slot()
    def pick_left_text_color(self):
        color = self._settings.pick_left_text_color(self.ui)

        self.set_preset_colors() # Update the presets in case one was changed while picking a color

        if self.right_text_color.isValid():
            self.left_text_color = color
            self.ui.leftTextColorPB.setStyleSheet(utilities.style_sheet(self.left_text_color))
        else:
            logger.error("Invalid color on left text color selection")

    @Slot()
    def pick_right_text_color(self):
        color = self._settings.pick_right_text_color(self.ui)

        self.set_preset_colors() # Update the presets in case one was changed while picking a color

        if self.right_text_color.isValid():
            self.right_text_color = color
            self.ui.rightTextColorPB.setStyleSheet(utilities.style_sheet(self.right_text_color))
        else:
            logger.error("Invalid color on right text color selection")

    @Slot()
    def show_left_text_main(self):
        font = self.ui.fontComboBoxLeft.currentFont()
        self.mainDisplay.show_text(self.ui.leftTextBox.toPlainText(), font, self.left_text_color)
        self.ui.imagePreviewMain.capture_window()

    @Slot()
    def show_left_text_auxiliary(self):
        font = self.ui.fontComboBoxLeft.currentFont()
        self.auxiliaryDisplay.show_text(self.ui.leftTextBox.toPlainText(), font, self.left_text_color)
        self.ui.imagePreviewAuxiliary.capture_window()

    @Slot()
    def show_left_text_both(self):
        self.show_left_text_main()
        self.show_left_text_auxiliary()

    @Slot()
    def show_right_text_main(self):
        font = self.ui.fontComboBoxRight.currentFont()
        self.mainDisplay.show_text(self.ui.rightTextBox.toPlainText(), font, self.right_text_color)
        self.ui.imagePreviewMain.capture_window()

    @Slot()
    def show_right_text_auxiliary(self):
        font = self.ui.fontComboBoxRight.currentFont()
        self.auxiliaryDisplay.show_text(self.ui.rightTextBox.toPlainText(), font, self.right_text_color)
        self.ui.imagePreviewAuxiliary.capture_window()

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
