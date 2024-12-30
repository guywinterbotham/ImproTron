# thingz_feature
# This Python file uses the following encoding: utf-8
from PySide6.QtCore import QObject, Slot, Qt
from PySide6.QtWidgets import QApplication, QStyle, QListWidgetItem, QMessageBox
import utilities

# Subclass to maintain the additional substitutes information associated with a Thing
class ThingzItem(QListWidgetItem):
    def __init__(self, title, is_left_side_team, parent=None):
        super().__init__(title, parent)

        self._substitutes = ""
        self._is_left_side_team = is_left_side_team

    def substitutes(self):
        return self._substitutes

    def thing_data(self):
        thing_text = self.text()
        if len(self._substitutes) > 0:
            thing_text += "\n" + self._substitutes

        return thing_text

    def update_substitutes(self, substitutesText):
        self._substitutes = substitutesText

    def is_left_side_team(self):
        return self._is_left_side_team

    def toggle_team(self):
        self._is_left_side_team = not self._is_left_side_team

class ThingzFeature(QObject):
    def __init__(self, ui, settings, main_display, auxiliary_display):
        super(ThingzFeature, self).__init__()

        self.ui = ui
        self._settings = settings
        self.main_display = main_display
        self.auxiliary_display = auxiliary_display

        self.ui.removeThingPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton))
        self.ui.clearThingzPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogDiscardButton))
        self.ui.thingzMoveUpPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))
        self.ui.thingzMoveDownPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))

        self.connect_slots()

    # Connect Thingz Management
    def connect_slots(self):
        self.ui.thingzListLW.itemClicked.connect(self.show_selected_thing)
        self.ui.thingzListLW.itemChanged.connect(self.title_edited)

        self.ui.addThingPB.clicked.connect(self.add_thing_to_list)
        self.ui.thingNameTxt.returnPressed.connect(self.add_thing_to_list)

        self.ui.toggleTeamPB.clicked.connect(self.toggle_team)
        self.ui.removeThingPB.clicked.connect(self.remove_thing_from_list)
        self.ui.clearThingzPB.clicked.connect(self.clear_thingz_list)
        self.ui.thingzMoveUpPB.clicked.connect(self.thingz_move_up)
        self.ui.thingzMoveDownPB.clicked.connect(self.thingz_move_down)

        self.ui.thingTextEdit.textChanged.connect(self.update_things_text)
        self.ui.showThingMainPB.clicked.connect(self.show_thing_main)
        self.ui.showThingAuxiliaryPB.clicked.connect(self.show_thing_auxiliary)
        self.ui.showThingBothPB.clicked.connect(self.show_thing_both)
        self.ui.showThingzMainPB.clicked.connect(self.show_thingz_list_main)
        self.ui.showThingzAuxiliaryPB.clicked.connect(self.show_thingz_list_auxiliary)
        self.ui.showThingzBothPB.clicked.connect(self.show_thingz_list_both)
        self.ui.reverseThingzListPB.clicked.connect(self.reverse_thingz)
        self.ui.nextThingMainPB.clicked.connect(self.show_next_thing_main)
        self.ui.nextThingAuxPB.clicked.connect(self.show_next_thing_aux)
    # End Connections

    # Things Tab Management
    def show_thingz_list(self, display_type):
        list_text = "Empty"
        if self.ui.thingzListLW.count() > 0:
            list_text = ""
            for thingRow in range(self.ui.thingzListLW.count()):
                list_text += self.ui.thingzListLW.item(thingRow).text()
                if thingRow < self.ui.thingzListLW.count()-1:
                    list_text += "\n"

            thing_font = self.ui.thingFontFCB.currentFont()
            thing_font.setPointSize(self.ui.thingFontSizeSB.value())

            if display_type in ("main", "both"):
                self.main_display.show_text(list_text, font = thing_font)
                utilities.capture_window(self.main_display, self.ui.imagePreviewMain)
            if display_type in ("auxiliary", "both"):
                self.auxiliary_display.show_text(list_text, font = thing_font)
                utilities.capture_window(self.auxiliary_display, self.ui.imagePreviewAuxiliary)

    @Slot()
    def reverse_thingz(self):
        # Extract all QListWidgetItem objects
        items = [self.ui.thingzListLW.takeItem(0) for _ in range(self.ui.thingzListLW.count())]

        # Reverse the list of items
        items.reverse()

        # Add them back to the QListWidget
        for item in items:
            self.ui.thingzListLW.addItem(item)

    def next_thing(self):
        # Get the currently selected items
        selected_items = self.ui.thingzListLW.selectedItems()

        # If no item is selected, start from the top
        if not selected_items:
            next_index = 0
        else:
            # Get the index of the currently selected item
            current_item = selected_items[0]
            current_index = self.ui.thingzListLW.row(current_item)

            # Calculate the next index (wrap around if at the end)
            next_index = (current_index + 1) % self.ui.thingzListLW.count()

        # Select the next item
        self.ui.thingzListLW.setCurrentRow(next_index)
        next_item = self.ui.thingzListLW.item(next_index)

        # Trigger the click event
        if next_item is not None:
            self.ui.thingzListLW.itemPressed.emit(next_item)
            self.show_selected_thing(next_item)

    @Slot()
    def show_next_thing_main(self):
        self.next_thing()
        self.show_thing("main")

    @Slot()
    def show_next_thing_aux(self):
        self.next_thing()
        self.show_thing("auxiliary")

    @Slot()
    def show_thingz_list_main(self):
        self.show_thingz_list("main")

    @Slot()
    def show_thingz_list_auxiliary(self):
        self.show_thingz_list("auxiliary")

    @Slot()
    def show_thingz_list_both(self):
        self.show_thingz_list("both")

    def show_thing(self, display_type):
        current_thing = self.ui.thingzListLW.currentItem()
        if not current_thing:
            return
        thing_font = self.ui.thingFontFCB.currentFont()
        thing_font.setPointSize(self.ui.thingFontSizeSB.value())
        thing_data = current_thing.thing_data()
        style = utilities.style_sheet(current_thing.background().color())

        if display_type in ("main", "both"):
            self.main_display.show_text(thing_data, style, thing_font)
            utilities.capture_window(self.main_display, self.ui.imagePreviewMain)
        if display_type in ("auxiliary", "both"):
            self.auxiliary_display.show_text(thing_data, style, thing_font)
            utilities.capture_window(self.auxiliary_display, self.ui.imagePreviewAuxiliary)

    @Slot()
    def show_thing_main(self):
       self.show_thing("main")

    @Slot()
    def show_thing_auxiliary(self):
       self.show_thing("auxiliary")

    @Slot()
    def show_thing_both(self):
       self.show_thing("both")

    @Slot()
    def update_things_text(self):
        currentThing = self.ui.thingzListLW.currentItem()

        if currentThing != None:
            self.ui.thingzListLW.currentItem().update_substitutes(self.ui.thingTextEdit.toPlainText())

    @Slot()
    def toggle_team(self):
        current_thing = self.ui.thingzListLW.currentItem()
        if not current_thing:
            return
        is_left_team = not current_thing.is_left_side_team()
        color = self._settings.get_left_team_color() if is_left_team else self._settings.get_right_team_color()
        current_thing.setBackground(color)
        current_thing.setForeground(utilities.team_font(color))
        current_thing.toggle_team()

    @Slot(ThingzItem)
    def show_selected_thing(self, thing):
        # Display selected item's title and text in the editor
        self.ui.thingFocusLBL.setText(thing.text())
        self.ui.thingTextEdit.setPlainText(thing.substitutes())

    @Slot(ThingzItem )
    def title_edited(self, thing):
        # Display selected item's title and text in the editor
        self.ui.thingFocusLBL.setText(thing.text())

    @Slot()
    def add_thing_to_list(self):
        thingStr = self.ui.thingNameTxt.text()
        if len(thingStr) > 0:

            # Determine which team is being entered from the radio buttons
            # and color the thing appropriately
            if self.ui.leftThingTeamRB.isChecked():
                newThing = ThingzItem (thingStr, True, self.ui.thingzListLW)
                newThing.setBackground(self._settings.get_left_team_color())
                newThing.setForeground(utilities.team_font(self._settings.get_left_team_color()))
                self.ui.rightThingTeamRB.setChecked(True)
            else: # Right Team Color
                newThing = ThingzItem (thingStr, False, self.ui.thingzListLW)
                newThing.setBackground(self._settings.get_right_team_color())
                newThing.setForeground(utilities.team_font(self._settings.get_right_team_color()))
                self.ui.leftThingTeamRB.setChecked(True)

            newThingFont = newThing.font()
            newThingFont.setPointSize(12)
            newThing.setFont(newThingFont)
            newThing.setFlags(newThing.flags() | Qt.ItemIsEditable)

            self.ui.thingNameTxt.setText("")
            self.ui.thingNameTxt.setFocus()
            self.ui.thingzListLW.setCurrentItem(newThing)
            self.ui.thingTextEdit.clear()

    @Slot()
    def thingz_move_down(self):
        thingRow = self.ui.thingzListLW.currentRow()
        if thingRow < 0:
            return
        thing = self.ui.thingzListLW.takeItem(thingRow)
        self.ui.thingzListLW.insertItem(thingRow+1,thing)
        self.ui.thingzListLW.setCurrentRow(thingRow+1)

    @Slot()
    def thingz_move_up(self):
        thingRow = self.ui.thingzListLW.currentRow()
        if thingRow < 0:
            return
        thing = self.ui.thingzListLW.takeItem(thingRow)
        self.ui.thingzListLW.insertItem(thingRow-1,thing)
        self.ui.thingzListLW.setCurrentRow(thingRow-1)

    @Slot()
    def remove_thing_from_list(self):
        self.ui.thingzListLW.takeItem(self.ui.thingzListLW.row(self.ui.thingzListLW.currentItem()))
        if self.ui.thingzListLW.currentItem() != None:
            self.show_selected_thing(self.ui.thingzListLW.currentItem())
        else:
            self.ui.thingFocusLBL.clear()
            self.ui.thingTextEdit.clear()


    @Slot()
    def clear_thingz_list(self):
        reply = QMessageBox.question(self.ui, 'Clear Thingz', 'Are you sure you want clear all Thingz?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.thingzListLW.clear()
            self.ui.leftThingTeamRB.setChecked(True)
            self.ui.thingFocusLBL.clear()
            self.ui.thingTextEdit.clear()
