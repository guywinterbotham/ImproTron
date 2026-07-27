# roster_feature.py
# This Python file uses the following encoding: utf-8
import csv
import logging
from enum import IntEnum

from PySide6.QtCore import QObject, Slot, QItemSelection, Qt, QSize, QRect, QModelIndex
from PySide6.QtGui import QStandardItem, QStandardItemModel, QColor, QMovie, QPainter, QPen
from PySide6.QtWidgets import QApplication, QStyle, QListWidgetItem, QFileDialog, QStyledItemDelegate, QLineEdit, QStyleOptionViewItem
import utilities

from monitor_preview import SmartOverlayLabel
class TeamRole(IntEnum):
    UNASSIGNED = 0
    LEFT_TEAM = 1
    RIGHT_TEAM = 2
    DJ = 3
    OFFICIAL = 4

    # Custom data role identifier for your model
PlayerRoleData = Qt.ItemDataRole.UserRole + 100

logger = logging.getLogger(__name__)

# Controls the color selection then an item is selected so as to get better contrast
class PlayerDelegate(QStyledItemDelegate):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings

    def _get_team_color(self, index) -> QColor:
        # Retrieve the enum integer cleanly using the custom role
        role_value = index.data(PlayerRoleData)

        if role_value == TeamRole.LEFT_TEAM:
            return self._settings.get_left_team_color()
        elif role_value == TeamRole.RIGHT_TEAM:
            return self._settings.get_right_team_color()
        elif role_value == TeamRole.DJ:
            return QColor(Qt.GlobalColor.darkMagenta)  # Ref Stripes / Dark Grey
        elif role_value == TeamRole.OFFICIAL:
            return QColor(Qt.GlobalColor.black)  # Ref Stripes / Dark Grey
        return QColor(Qt.GlobalColor.white)      # Unassigned Default Roster Grey

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        if not index.isValid():
            return

        is_selected = bool(option.state & QStyle.State_Selected)
        bg_color = self._get_team_color(index)
        font = index.data(Qt.ItemDataRole.FontRole) or painter.font()

        if is_selected:
            font.setBold(True)

        painter.save()
        painter.setFont(font)

        # 1. Fill base team background (unmodified color for max contrast)
        painter.fillRect(option.rect, bg_color)

        # 2. Render Selection Treatment (Gold Outline + Left Indicator Pill)
        text_offset = 5
        if is_selected:
            # Left-edge indicator bar (6px thick)
            indicator_rect = QRect(option.rect.left() + 2, option.rect.top() + 2, 6, option.rect.height() - 4)
            painter.fillRect(indicator_rect, QColor("#FFD700"))  # High-visibility Gold
            text_offset = 14  # Shift text right to accommodate indicator

            # 2px Inner Gold Border around entire row
            pen = QPen(QColor("#FFD700"), 2)
            pen.setJoinStyle(Qt.MiterJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(option.rect.adjusted(1, 1, -1, -1))

        # 3. Dynamic contrast text pass
        painter.setPen(utilities.team_font(bg_color))
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""

        # Adjust padding dynamically so text never overlaps the selection bar
        text_rect = option.rect.adjusted(text_offset, 0, -5, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        painter.restore()

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        font = index.data(Qt.ItemDataRole.FontRole) or parent.font()
        editor.setFont(font)

        bg_color = self._get_team_color(index)
        fg_color = utilities.team_font(bg_color)

        editor.setStyleSheet(
            f"QLineEdit {{ background-color: {bg_color.name()}; color: {fg_color.name()}; border: none; }}"
        )
        return editor

    def setEditorData(self, editor, index):
        editor.setText(index.data(Qt.ItemDataRole.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def sizeHint(self, option, index):
        return QSize(100, 30)

class RosterFeature(QObject):
    def __init__(self, ui, settings, mainDisplay, auxiliaryDisplay):
        super(RosterFeature, self).__init__()

        self.ui = ui
        self._settings = settings
        self.mainDisplay = mainDisplay
        self.auxiliaryDisplay = auxiliaryDisplay
        self.ui.rosterLW.setItemDelegate(PlayerDelegate(settings))

        # Flag to determine starting team for Call On & Tie-breakers
        self.ui.leftTeamFirstCB.setChecked(self._settings.get_left_team_first())

        # Promote the roster preview labels so it can handle QMovies with smart overlays
        old_label = self.ui.rosterPreviewLBL
        layout = self.ui.rosterPreviewVL
        index = layout.indexOf(old_label)

        if index != -1:
            stretch = layout.stretch(index)
            alignment = layout.alignment()
            old_stylesheet = old_label.styleSheet()  # Capture Style Sheet

            new_label = SmartOverlayLabel(old_label.parentWidget())
            new_label.setObjectName(old_label.objectName())
            new_label.setMinimumSize(old_label.minimumSize())
            new_label.setMaximumSize(old_label.maximumSize())
            new_label.setSizePolicy(old_label.sizePolicy())
            new_label.setStyleSheet(old_stylesheet)  # Apply Style Sheet

            layout.removeWidget(old_label)
            layout.insertWidget(index, new_label, stretch=stretch, alignment=alignment)

            self.ui.rosterPreviewLBL = new_label
            old_label.deleteLater()

            self.connect_slots()

    def connect_slots(self):
        self.ui.rosterLW.itemChanged.connect(self.on_player_changed) # Refresh when a player in the roster is edited
        self.ui.rosterSetTroupePB.clicked.connect(self.set_troupe_list) # On preferences Page

        self.ui.rosterTextSLD.valueChanged.connect(self.roster_preview_changed)
        self.ui.rosterTextSLD.setValue(self._settings.get_roster_text_size())

        self.ui.rosterFontCB.currentIndexChanged.connect(self.roster_preview_changed)
        self.ui.rosterLW.currentRowChanged.connect(self.roster_preview_changed)
        self.ui.addPlayerPB.clicked.connect(self.add_player_to_list)
        self.ui.addPlayerLE.returnPressed.connect(self.add_player_to_list)

        # Switch Role Pushbuttons
        self.ui.rosterLeftPB.clicked.connect(self.assign_selected_to_left_team)
        self.ui.rosterRightPB.clicked.connect(self.assign_selected_to_right_team)
        self.ui.rosterDJPB.clicked.connect(self.assign_selected_to_dj)
        self.ui.rosterOfficialPB.clicked.connect(self.assign_selected_to_official)
        self.ui.rosterOfficialPB.setText(self._settings.get_official_team_name())

        self.ui.movePlayerUpPB.clicked.connect(self.move_player_up)
        self.ui.movePlayerUpPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))

        self.ui.movePlayerDownPB.clicked.connect(self.move_player_down)
        self.ui.movePlayerDownPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))

        self.ui.removePlayerPB.clicked.connect(self.remove_selected_players)
        self.ui.removePlayerPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton))

        self.ui.clearRosterPB.clicked.connect(self.remove_all_players)
        self.ui.clearRosterPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogDiscardButton))

        # Player call on and off sorts
        self.ui.rosterCallOnPB.clicked.connect(self.on_rosterCallOnPB_clicked)
        self.ui.rosterOffByTeam.clicked.connect(self.on_rosterOffByTeam_clicked)
        self.ui.rosterOffByPlayerPB.clicked.connect(self.on_rosterOffByPlayerPB_clicked)
        self.ui.leftTeamFirstCB.toggled.connect(self.on_leftTeamFirstCB_toggled)

        # Display on Monitor action
        self.ui.rosterOnMainPB.clicked.connect(self.show_player_main)
        self.ui.rosterOnAuxPB.clicked.connect(self.show_player_aux)
        self.ui.rosterNextOnMainPB.clicked.connect(self.show_next_player_main)
        self.ui.rosterNextOnAuxPB.clicked.connect(self.show_next_player_aux)

        # Maintain a model/view of the troupe
        self._troupe_list_view = self.ui.rosterTroupeLV
        self._troupe_model = QStandardItemModel(self._troupe_list_view)
        self._troupe_list_view.setModel(self._troupe_model)
        self.read_troupe()

        # Selection changes will trigger a slot
        selectionModel = self._troupe_list_view.selectionModel()
        selectionModel.selectionChanged.connect(self.player_selected)

    # File Utilities for Preferences:

    # Opens a file dialog filtered strictly to QMovie supported formats.
    # Returns the absolute file path string, or an empty string if canceled.
    def get_player_background(self):
        # Dynamically extract formats: e.g., ['*.gif', '*.webp']
        extensions = [f"*.{str(fmt, 'utf-8')}" for fmt in QMovie.supportedFormats()]
        file_filter = f"Improv Media Files ({' '.join(extensions)})"

        file_path, _ = QFileDialog.getOpenFileName(
            self.ui,
            "Select Player Background",
            self._settings.get_media_directory(),
            file_filter
        )
        return file_path  # Returns "" if user cancels out

    # Returns the validated graphic path for the active match-play role.
    # Falls back to a clean string if UNASSIGNED to blank the display layer.
    def get_role_background(self, role: TeamRole):
        mapping = {
            TeamRole.LEFT_TEAM: self._settings.get_left_graphic,
            TeamRole.RIGHT_TEAM: self._settings.get_right_graphic,
            TeamRole.DJ: self._settings.get_dj_graphic,
            TeamRole.OFFICIAL: self._settings.get_official_graphic
        }

        getter = mapping.get(role)
        return getter() if getter else ""

    # Returns the validated graphic path for the active match-play role.
    # Falls back to a clean string if UNASSIGNED to blank the display layer.
    def get_role_name(self, role: TeamRole):
        mapping = {
            TeamRole.LEFT_TEAM: self._settings.get_left_team_name,
            TeamRole.RIGHT_TEAM: self._settings.get_right_team_name,
            TeamRole.DJ: self._settings.get_dj_team_name,
            TeamRole.OFFICIAL: self._settings.get_official_team_name
        }

        getter = mapping.get(role)
        return getter() if getter else ""

    def next_player(self):
        # Get the currently selected items
        selected_items = self.ui.rosterLW.selectedItems()

        # If no item is selected, start from the top
        if not selected_items:
            next_index = 0
        else:
            # Get the index of the currently selected item
            current_item = selected_items[0]
            current_index = self.ui.rosterLW.row(current_item)

            # Calculate the next index (wrap around if at the end)
            next_index = (current_index + 1) % self.ui.rosterLW.count()

        # Select the next item
        self.ui.rosterLW.setCurrentRow(next_index)
        next_item = self.ui.rosterLW.item(next_index)

        # Trigger the click event
        if next_item is not None:
            self.ui.rosterLW.itemPressed.emit(next_item)

    def first_player(self):
        # Select the first item
        self.ui.rosterLW.setCurrentRow(0)
        first_item = self.ui.rosterLW.item(0)

        # Trigger the click event
        if first_item is not None:
            self.ui.rosterLW.itemPressed.emit(first_item)

    @Slot(int)
    def roster_preview_changed(self, value):
        self.draw_player_slide(self.ui.rosterPreviewLBL)

    # Refreshes preview if the edited item is the active current item.
    @Slot(QListWidgetItem)
    def on_player_changed(self, player: QListWidgetItem):
        if player is self.ui.rosterLW.currentItem():
            self.draw_player_slide(self.ui.rosterPreviewLBL)

    @Slot()
    def show_player_main(self):
        current_item = self.ui.rosterLW.currentItem()
        if not current_item:
            return

        player_name = current_item.text()

        # Extract role enum and get mapped team background asset
        role_id = current_item.data(PlayerRoleData)
        current_role = TeamRole(role_id) if role_id is not None else TeamRole.UNASSIGNED
        graphic_path = self.get_role_background(current_role)

        # Derive team display string (adjust team names to match match-day settings)
        team_names = {
            TeamRole.LEFT_TEAM: self._settings.get_left_team_name(),
            TeamRole.RIGHT_TEAM: self._settings.get_right_team_name(),
            TeamRole.DJ: self._settings.get_dj_team_name(),
            TeamRole.OFFICIAL: self._settings.get_official_team_name(),
            TeamRole.UNASSIGNED: ""
        }
        team_name = team_names.get(current_role, "")

        font = self.ui.rosterFontCB.currentFont()
        scale = self.ui.rosterTextSLD.value()
        self._settings.set_roster_text_size(scale)

        if graphic_path:
            # Call the  dual-layer display function on the main display screen
            self.mainDisplay.show_player(
                background_path=graphic_path,
                player_name=player_name,
                team_name=team_name,
                font=font,
                scale=scale,
                textColor=QColor(Qt.GlobalColor.white)
            )

        self.draw_player_slide(self.ui.imagePreviewMain)

    @Slot()
    def show_next_player_main(self):
        self.next_player()
        self.show_player_main()

    @Slot()
    def show_1st_player_main(self):
        self.first_player()
        self.show_player_main()

    @Slot()
    def show_player_aux(self):
        current_item = self.ui.rosterLW.currentItem()
        if not current_item:
            return

        player_name = current_item.text()

        # Extract role enum and get mapped team background asset
        role_id = current_item.data(PlayerRoleData)
        current_role = TeamRole(role_id) if role_id is not None else TeamRole.UNASSIGNED
        graphic_path = self.get_role_background(current_role)

        # Derive team display string (adjust team names to match match-day settings)
        team_names = {
            TeamRole.LEFT_TEAM: self._settings.get_left_team_name(),
            TeamRole.RIGHT_TEAM: self._settings.get_right_team_name(),
            TeamRole.DJ: self._settings.get_dj_team_name(),
            TeamRole.OFFICIAL: self._settings.get_official_team_name(),
            TeamRole.UNASSIGNED: ""
        }
        team_name = team_names.get(current_role, "")

        font = self.ui.rosterFontCB.currentFont()
        scale = self.ui.rosterTextSLD.value()
        self._settings.set_roster_text_size(scale)

        if graphic_path:
            # Call the updated dual-layer display function on the main display screen
            self.auxiliaryDisplay.show_player(
                background_path=graphic_path,
                player_name=player_name,
                team_name=team_name,
                font=font,
                scale=scale,
                textColor=QColor(Qt.GlobalColor.white)
            )

            self.draw_player_slide(self.ui.imagePreviewAuxiliary)

    @Slot()
    def show_next_player_aux(self):
        self.next_player()
        self.show_player_aux()

    @Slot()
    def show_1st_player_aux(self):
        self.first_player()
        self.show_player_aux()

    def draw_player_slide(self, label):
        player_name = "No player selected"
        team_name = "No Role"
        current_role = TeamRole.UNASSIGNED
        bg_path = ""

        current_item = self.ui.rosterLW.currentItem()
        if current_item:
            player_name = current_item.text()
            role_id = current_item.data(PlayerRoleData)
            current_role = (
                TeamRole(role_id) if role_id is not None else TeamRole.UNASSIGNED
            )
            team_name = self.get_role_name(current_role)
            bg_path = self.get_role_background(current_role)

        font = self.ui.rosterFontCB.currentFont()
        scale = float(self.ui.rosterTextSLD.value())

        if current_role != TeamRole.UNASSIGNED:
            label.set_player_overlay(
                background_path=bg_path,
                player_name=player_name,
                team_name=team_name,
                font=font,
                scale=scale,
                color=QColor(Qt.GlobalColor.white),
            )

    # Add a player via the text entry
    @Slot()
    def add_player_to_list(self):
        if len(self.ui.addPlayerLE.text()) > 0:
            list_item = QListWidgetItem(self.ui.addPlayerLE.text())
            list_item.setFlags(list_item.flags() | Qt.ItemIsEditable)
            list_item.setData(PlayerRoleData, int(TeamRole.UNASSIGNED))
            self.ui.rosterLW.addItem(list_item)
            self.ui.addPlayerLE.setText("")
            self.ui.addPlayerLE.setFocus()

    # Add a player via clicking an entry from the troupe list
    @Slot(QItemSelection, QItemSelection)
    def player_selected(self, selected, deselected):
        indexes = selected.indexes()
        if len(indexes):
            item = indexes[0]
            description = item.data(Qt.UserRole)
            list_item = QListWidgetItem(description)
            list_item.setFlags(list_item.flags() | Qt.ItemIsEditable)
            list_item.setData(PlayerRoleData, int(TeamRole.UNASSIGNED))
            self.ui.rosterLW.addItem(list_item)


    @Slot()
    def move_player_down(self):
        player_row = self.ui.rosterLW.currentRow()
        if player_row < 0:
            return
        player = self.ui.rosterLW.takeItem(player_row)
        self.ui.rosterLW.insertItem(player_row+1,player)
        self.ui.rosterLW.setCurrentRow(player_row+1)

    @Slot()
    def move_player_up(self):
        player_row = self.ui.rosterLW.currentRow()
        if player_row < 0:
            return
        player = self.ui.rosterLW.takeItem(player_row)
        self.ui.rosterLW.insertItem(player_row-1,player)
        self.ui.rosterLW.setCurrentRow(player_row-1)

    @Slot()
    def remove_selected_players(self):
        selected_items = self.ui.rosterLW.selectedItems()
        for item in selected_items:
            self.ui.rosterLW.takeItem(self.ui.rosterLW.row(item))

    @Slot()
    def remove_all_players(self):
        self.ui.rosterLW.clear()

    @Slot()
    def set_troupe_list(self):
        file_name = QFileDialog.getOpenFileName(self.ui, "Set Troupe List",
                                                self._settings.get_config_dir(),
                                                "Troupe Files (*.csv)")
        if len(file_name[0]) > 0:
            self._settings.set_troupe_file(file_name[0])
            self.read_troupe()

    def read_troupe(self):
        self._troupe_model.clear()
        self._troupe_model.setHorizontalHeaderLabels(["Name"])
        troupe_file = self._settings.get_troupe_file()

        if len(troupe_file) > 0:
            try:
                with open(troupe_file, newline='', encoding='utf-8') as csv_file:
                    reader = csv.reader(csv_file)
                    try:
                        next(reader)  # Skip header
                    except StopIteration:
                        logger.error(f"Troupe CSV file {troupe_file} is empty or missing header.")
                        return

                    for row in reader:
                        if len(row) < 3:
                            logger.warning(f"Skipping malformed row in {troupe_file}, line {reader.line_num}: {row}")
                            continue

                        last, first, stage_name = row[0], row[1], row[2]

                        name_item = QStandardItem(first+' '+last)
                        name_item.setData(stage_name, Qt.UserRole)
                        name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                        self._troupe_model.appendRow([name_item])

            except FileNotFoundError:
                logger.error(f"Troup CSV file not found: {troupe_file}")
            except (IOError, OSError) as e:
                logger.error(f"Error reading rosters CSV file {troupe_file}: {e}")
            except csv.Error as e:
                logger.error(f"Error parsing CSV file {troupe_file}: {e}")


    # Pushbuttons action to change the team assignments

    # Assigns selected roster items to the Left Team.
    @Slot()
    def assign_selected_to_left_team(self):
        # Get color metrics from app settings config
        bg_color = self._settings.get_left_team_color()
        fg_color = utilities.team_font(bg_color)

        # Process only selected items in rosterLW
        for item in self.ui.rosterLW.selectedItems():
            # Update custom data role for the PlayerDelegate pass
            item.setData(PlayerRoleData, int(TeamRole.LEFT_TEAM))

            # Explicit item overrides to guarantee native fallback states update
            item.setBackground(bg_color)
            item.setForeground(fg_color)

        self.ui.rosterLW.clearSelection()

    # Assigns selected roster items to the Right Team.
    @Slot()
    def assign_selected_to_right_team(self):
        # Get color metrics from app settings config
        bg_color = self._settings.get_right_team_color()
        fg_color = utilities.team_font(bg_color)

        # Process only selected items in rosterLW
        for item in self.ui.rosterLW.selectedItems():
            # Update custom data role for the PlayerDelegate pass
            item.setData(PlayerRoleData, int(TeamRole.RIGHT_TEAM))

            # Explicit item overrides to guarantee native fallback states update
            item.setBackground(bg_color)
            item.setForeground(fg_color)

        self.ui.rosterLW.clearSelection()

    # Assigns selected roster items to the Officials Team.
    @Slot()
    def assign_selected_to_dj(self):
        bg_color = QColor(Qt.GlobalColor.darkMagenta)
        fg_color = utilities.team_font(bg_color)

        # Process only selected items in rosterLW
        for item in self.ui.rosterLW.selectedItems():
            # Update custom data role for the PlayerDelegate pass
            item.setData(PlayerRoleData, int(TeamRole.DJ))

            # Explicit item overrides to guarantee native fallback states update
            item.setBackground(bg_color)
            item.setForeground(fg_color)

        self.ui.rosterLW.clearSelection()

    # Assigns selected roster items to the Officials Team.
    @Slot()
    def assign_selected_to_official(self):
        bg_color = QColor(Qt.GlobalColor.black)
        fg_color = utilities.team_font(bg_color)

        # Process only selected items in rosterLW
        for item in self.ui.rosterLW.selectedItems():
            # Update custom data role for the PlayerDelegate pass
            item.setData(PlayerRoleData, int(TeamRole.OFFICIAL))

            # Explicit item overrides to guarantee native fallback states update
            item.setBackground(bg_color)
            item.setForeground(fg_color)

        self.ui.rosterLW.clearSelection()

    # Call on and off logic

    #Helper to safely fetch current scores from spinboxes.
    def _get_team_scores(self):
        left_val = self.ui.teamScoreLeft.value()
        right_val = self.ui.teamScoreRight.value()
        return left_val, right_val

    def _extract_roster_items(self):
        """Take all items out of rosterLW and return them as a Python list."""
        items = []
        while self.ui.rosterLW.count() > 0:
            items.append(self.ui.rosterLW.takeItem(0))
        return items

    def _repopulate_roster(self, items):
        """Re-insert sorted items back into rosterLW and select the first item."""
        for item in items:
            self.ui.rosterLW.addItem(item)

        if self.ui.rosterLW.count() > 0:
            self.ui.rosterLW.setCurrentRow(0)

    # -------------------------------------------------------------------------
    # Call On
    # -------------------------------------------------------------------------
    @Slot()
    def on_rosterCallOnPB_clicked(self):
        """Sorts list: Primary Team -> Secondary Team -> Officials -> Unassigned."""
        items = self._extract_roster_items()

        first_role = TeamRole.LEFT_TEAM if self._settings.get_left_team_first() else TeamRole.RIGHT_TEAM
        second_role = TeamRole.RIGHT_TEAM if self._settings.get_left_team_first() else TeamRole.LEFT_TEAM

        role_priority = {
            first_role: 0,
            second_role: 1,
            TeamRole.DJ : 2,
            TeamRole.OFFICIAL: 3,
            TeamRole.UNASSIGNED: 4
        }

        # Stable sort preserves current team order
        items.sort(key=lambda item: role_priority.get(TeamRole(item.data(PlayerRoleData)), 99))
        self._repopulate_roster(items)

    # -------------------------------------------------------------------------
    # Call Off by Team
    # -------------------------------------------------------------------------
    @Slot()
    def on_rosterOffByTeam_clicked(self):
        """Sorts list: Losing Team -> Winning Team -> Officials -> Unassigned.
        Falls back to 'first_team_is_left' flag on ties."""
        left_score, right_score = self._get_team_scores()

        if left_score < right_score:
            losing_role, winning_role = TeamRole.LEFT_TEAM, TeamRole.RIGHT_TEAM
        elif right_score < left_score:
            losing_role, winning_role = TeamRole.RIGHT_TEAM, TeamRole.LEFT_TEAM
        else:
            # Tie: Fall back to persistent Call On preference
            losing_role = TeamRole.LEFT_TEAM if self._settings.get_left_team_first() else TeamRole.RIGHT_TEAM
            winning_role = TeamRole.RIGHT_TEAM if self._settings.get_left_team_first() else TeamRole.LEFT_TEAM

        role_priority = {
            losing_role: 0,
            winning_role: 1,
            TeamRole.DJ : 2,
            TeamRole.OFFICIAL: 3,
            TeamRole.UNASSIGNED: 4
        }

        items = self._extract_roster_items()
        items.sort(key=lambda item: role_priority.get(TeamRole(item.data(PlayerRoleData)), 99))
        self._repopulate_roster(items)

    # -------------------------------------------------------------------------
    # Call Off by Player (Interleaved)
    # -------------------------------------------------------------------------
    @Slot()
    def on_rosterOffByPlayerPB_clicked(self):
        """Interleaves Losing & Winning players 1:1, followed by Officials."""
        left_score, right_score = self._get_team_scores()

        if left_score < right_score:
            losing_role, winning_role = TeamRole.LEFT_TEAM, TeamRole.RIGHT_TEAM
        elif right_score < left_score:
            losing_role, winning_role = TeamRole.RIGHT_TEAM, TeamRole.LEFT_TEAM
        else:
            losing_role = TeamRole.LEFT_TEAM if self._settings.get_left_team_first() else TeamRole.RIGHT_TEAM
            winning_role = TeamRole.RIGHT_TEAM if self._settings.get_left_team_first() else TeamRole.LEFT_TEAM

        items = self._extract_roster_items()

        # Group items while maintaining order
        losing_team = [i for i in items if TeamRole(i.data(PlayerRoleData)) == losing_role]
        winning_team = [i for i in items if TeamRole(i.data(PlayerRoleData)) == winning_role]
        djs = [i for i in items if TeamRole(i.data(PlayerRoleData)) == TeamRole.DJ]
        officials = [i for i in items if TeamRole(i.data(PlayerRoleData)) == TeamRole.OFFICIAL]
        others = [i for i in items if TeamRole(i.data(PlayerRoleData)) == TeamRole.UNASSIGNED]

        # Interleave 1:1
        interleaved = []
        while losing_team or winning_team:
            if losing_team:
                interleaved.append(losing_team.pop(0))
            if winning_team:
                interleaved.append(winning_team.pop(0))

        # Append remaining officials & unassigned
        final_order = interleaved + djs + officials + others
        self._repopulate_roster(final_order)

    # Updates persistent setting when 'Call Left Team on first' is toggled.
    @Slot(bool)
    def on_leftTeamFirstCB_toggled(self, checked: bool) -> None:
        self._settings.set_left_team_first(checked)
