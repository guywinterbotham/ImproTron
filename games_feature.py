# games_feature.py
# This Python file uses the following encoding: utf-8
import csv
import logging
from PySide6.QtCore import QObject, Slot, QItemSelection, Qt, QTimer, QFileInfo, QRandomGenerator, QSortFilterProxyModel, QRegularExpression, QModelIndex
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QStyle, QFileDialog, QColorDialog, QListWidgetItem
from monitor_preview import SmartOverlayLabel

logger = logging.getLogger(__name__)

class GamesFeature(QObject):
    def __init__(self, ui, settings, mainDisplay, auxiliaryDisplay):
        super(GamesFeature, self).__init__()

        self.ui = ui
        self._settings = settings
        self.mainDisplay = mainDisplay
        self.auxiliaryDisplay = auxiliaryDisplay

        # Promote the screen preview labels so they can handle GIFs with smart overlays
        # --- 1. GAME TAB PREVIEW (gameBackgroundLBL) REPLACEMENT ---
        if hasattr(self.ui, 'gameBackgroundLBL') and not isinstance(self.ui.gameBackgroundLBL, SmartOverlayLabel):
            old_label = self.ui.gameBackgroundLBL
            if hasattr(self.ui, 'gameImageVL') and self.ui.gameImageVL is not None:
                layout = self.ui.gameImageVL
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

                    self.ui.gameBackgroundLBL = new_label
                    old_label.deleteLater()
            else:
                logger.error("Could not find the 'gameImageVL' layout container at runtime.")

        self._game_whams = 0
        self._games_background_path = ""
        self._game_color_selected = self._settings.get_game_text_color()

        # Initialize background path and configure local control UI slider
        self._games_background_path = self._settings.get_game_background()
        self.ui.gameTextSLD.setValue(self._settings.get_game_text_size())
        self._whammy_randomizer = QRandomGenerator()

        # Load file asset to setup engine previews
        self.load_background_file(self._games_background_path)

        # Maintain a model/view of the games with live filtering proxy
        self._games_tree_view = self.ui.gamesTreeView
        self._games_model = QStandardItemModel(self._games_tree_view)

        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._games_model)
        self._proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        # Enable recursive filtering so matching children keep their parent category visible
        self._proxy_model.setRecursiveFilteringEnabled(True)

        self._games_tree_view.setModel(self._proxy_model)
        self.read_games()

        self.connect_slots()

    def connect_slots(self):
        # Games List Management Wiring
        self.ui.setGamesListPB.clicked.connect(self.set_games_list)
        self.ui.loadBackgroundPB.clicked.connect(self.load_background)
        self.ui.gameTextColorPB.clicked.connect(self.pick_game_text_color)
        self.ui.gameTextSLD.valueChanged.connect(self.game_preview_changed)
        self.ui.gameTextFontCB.currentIndexChanged.connect(self.game_preview_changed)
        self.ui.gamesLW.currentRowChanged.connect(self.game_preview_changed)
        self.ui.gameToMainShowPB.clicked.connect(self.show_game_main)
        self.ui.gameToAuxShowPB.clicked.connect(self.show_game_aux)
        self.ui.nextGameAuxPB.clicked.connect(self.show_next_game_aux)
        self.ui.addGamePB.clicked.connect(self.add_game_to_list)
        self.ui.addGameLE.returnPressed.connect(self.add_game_to_list)
        self.ui.setGameToImagePB.clicked.connect(self.set_game_to_image)
        self.ui.setGameToSlidePB.clicked.connect(self.set_game_to_slide)

        # A double click on a list item will copy it to the list of games
        self.ui.gamesTreeView.doubleClicked.connect(self.add_to_games)
        self.ui.gametoListPB.clicked.connect(self.add_selected_to_games)
        self.ui.gametoListPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))

        self.ui.removeGamePB.clicked.connect(self.remove_selected_games)
        self.ui.removeGamePB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton))

        self.ui.removeAllGamesPB.clicked.connect(self.remove_all_games)
        self.ui.removeAllGamesPB.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogDiscardButton))

        self.ui.gameMoveUpPB.clicked.connect(self.move_game_up)
        self.ui.gameMoveUpPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))

        self.ui.gameMoveDownPB.clicked.connect(self.move_game_down)
        self.ui.gameMoveDownPB.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))

        # Connect game search
        self.ui.gameSearchLE.textChanged.connect(self.filter_game_tree)

        # Selection changes will trigger a slot
        selectionModel = self._games_tree_view.selectionModel()
        selectionModel.selectionChanged.connect(self.game_selected)

        # Game Whammy seconds settings
        self.ui.secsPerGameWhamCB.addItems(['0.5', '1.0', '1.5', '2.0'])
        self.ui.gameWhammyPB.clicked.connect(self.start_game_whamming)
        self._game_whammy_timer = QTimer()
        self._game_whammy_timer.timeout.connect(self.next_game_wham)

    @Slot()
    def set_games_list(self):
        file_name = QFileDialog.getOpenFileName(self.ui, "Set Games List",
                                                self._settings.get_config_dir(),
                                                "Games Files (*.csv)")
        if len(file_name[0]) > 0:
            self._settings.set_games_file(file_name[0])
            self.read_games()

    def read_games(self):
        self._games_model.clear()
        self._games_model.setHorizontalHeaderLabels(["Category/Name"])
        categories = {}
        games_file = self._settings.get_games_file()

        if len(games_file) > 0:
            try:
                with open(games_file, newline='', encoding='utf-8') as csv_file:
                    reader = csv.reader(csv_file)
                    try:
                        next(reader)  # Skip header
                    except StopIteration:
                        logger.error(f"Games CSV file {games_file} is empty or missing header.")
                        return

                    for row in reader:
                        if len(row) < 3:
                            logger.warning(f"Skipping malformed row in {games_file}, line {reader.line_num}: {row}")
                            continue

                        category, name, description = row[0], row[1], row[2]

                        if category not in categories:
                            category_item = QStandardItem(category)
                            category_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                            self._games_model.appendRow([category_item])
                            categories[category] = category_item

                        name_item = QStandardItem(name)
                        name_item.setData(description, Qt.UserRole)
                        name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                        categories[category].appendRow([name_item])

                self._games_tree_view.expandAll()

            except FileNotFoundError:
                logger.error(f"Games CSV file not found: {games_file}")
            except (IOError, OSError) as e:
                logger.error(f"Error reading games CSV file {games_file}: {e}")
            except csv.Error as e:
                logger.error(f"Error parsing CSV file {games_file}: {e}")

    @Slot(str)
    def filter_game_tree(self, text):
        """Filters the tree view instantly on text change and expands matching nodes."""
        pattern = QRegularExpression.escape(text)
        regex = QRegularExpression(pattern, QRegularExpression.CaseInsensitiveOption)
        self._proxy_model.setFilterRegularExpression(regex)

        if text.strip():
            self._games_tree_view.expandAll()

    @Slot(QModelIndex)
    def add_to_games(self, proxy_index):
        """Handle double-click using proxy index conversion."""
        source_index = self._proxy_model.mapToSource(proxy_index)
        item = self._games_model.itemFromIndex(source_index)
        if item:
            if item.hasChildren():
                for row in range(item.rowCount()):
                    list_item = QListWidgetItem(item.child(row).text())
                    self.ui.gamesLW.addItem(list_item)
            elif item.parent():
                list_item = QListWidgetItem(item.text())
                self.ui.gamesLW.addItem(list_item)

    @Slot()
    def add_selected_to_games(self):
        """Handle adding button selection using proxy index conversion."""
        selected_indexes = self._games_tree_view.selectionModel().selectedIndexes()
        if selected_indexes:
            source_index = self._proxy_model.mapToSource(selected_indexes[0])
            item = self._games_model.itemFromIndex(source_index)
            if item:
                if item.hasChildren():
                    for row in range(item.rowCount()):
                        list_item = QListWidgetItem(item.child(row).text())
                        self.ui.gamesLW.addItem(list_item)
                elif item.parent():
                    list_item = QListWidgetItem(item.text())
                    self.ui.gamesLW.addItem(list_item)

    @Slot(QItemSelection, QItemSelection)
    def game_selected(self, selected, deselected):
        """Display description when game item selected."""
        indexes = selected.indexes()
        if len(indexes):
            source_index = self._proxy_model.mapToSource(indexes[0])
            description = source_index.data(Qt.UserRole)
            self.ui.gameDescriptionTE.setText(description if description else "")

    @Slot()
    def remove_selected_games(self):
        selected_items = self.ui.gamesLW.selectedItems()
        for item in selected_items:
            self.ui.gamesLW.takeItem(self.ui.gamesLW.row(item))

    @Slot(int)
    def game_preview_changed(self, value):
        self.draw_games_slide(self.ui.gameBackgroundLBL)

    @Slot()
    def move_game_up(self):
        game_row = self.ui.gamesLW.currentRow()
        if game_row < 0:
            return
        game = self.ui.gamesLW.takeItem(game_row)
        self.ui.gamesLW.insertItem(game_row-1,game)
        self.ui.gamesLW.setCurrentRow(game_row-1)

    @Slot()
    def move_game_down(self):
        game_row = self.ui.gamesLW.currentRow()
        if game_row < 0:
            return
        game = self.ui.gamesLW.takeItem(game_row)
        self.ui.gamesLW.insertItem(game_row+1,game)
        self.ui.gamesLW.setCurrentRow(game_row+1)

    @Slot()
    def pick_game_text_color(self):
        color_selected = QColorDialog.getColor(parent=self.ui, title='Pick the game text color')
        self._settings.save_custom_colors()
        if color_selected is not None:
            self._game_color_selected = color_selected
            self._settings.set_game_text_color(color_selected)
            self.draw_games_slide(self.ui.gameBackgroundLBL)

    def load_background_file(self, games_background_file):
        if not games_background_file:
            logger.error("No background file supplied.")
            return

        if not QFileInfo.exists(games_background_file):
            logger.error(f"Selected game background file does not exist: {games_background_file}")
            return

        self._games_background_path = games_background_file
        self._settings.set_game_background(games_background_file)

        # Set the preview to the new background
        self.ui.gameBackgroundLBL.set_background(games_background_file)

        self.draw_games_slide(self.ui.gameBackgroundLBL)

    @Slot()
    def load_background(self):
        selected_file_name = QFileDialog.getOpenFileName(
            self.ui, "Select Background", self._settings.get_media_directory(),
            "Background Files (*.png *.jpg *.bmp *.webp *.gif)"
        )
        if not selected_file_name or not selected_file_name[0]:
            logger.info("No background file selected.")
            return
        self.load_background_file(selected_file_name[0])

    @Slot()
    def set_game_to_image(self):
        self.load_background_file(self.ui.mediaFileNameLBL.text())

    @Slot()
    def set_game_to_slide(self):
        index = self.ui.slideShowFilesTreeView.selectionModel().currentIndex()
        media_model = self.ui.slideShowFilesTreeView.model()
        if not index.isValid() or media_model.isDir(index):
            logger.warning("No valid file selected in slideshow to set as game background.")
            return
        image_file_info = media_model.fileInfo(index)
        self.load_background_file(image_file_info.absoluteFilePath())

    @Slot()
    def show_game_main(self):
        game_row = self.ui.gamesLW.currentRow()
        text = self.ui.gamesLW.currentItem().text() if game_row >= 0 else "No game selected"

        font = self.ui.gameTextFontCB.currentFont()
        slider = self.ui.gameTextSLD.value()
        self._settings.set_game_text_size(slider)

        # Display the game frame on the main monitor
        self.mainDisplay.show_overlay_text(self._games_background_path, text, font, slider, self._game_color_selected)

        self.draw_games_slide(self.ui.imagePreviewMain)

    @Slot()
    def show_game_aux(self):
        game_row = self.ui.gamesLW.currentRow()
        text = self.ui.gamesLW.currentItem().text() if game_row >= 0 else "No game selected"

        font = self.ui.gameTextFontCB.currentFont()
        slider = self.ui.gameTextSLD.value()
        self._settings.set_game_text_size(slider)

        # Display the game frame on the aux monitor
        self.auxiliaryDisplay.show_overlay_text(self._games_background_path, text, font, slider, self._game_color_selected)

        self.draw_games_slide(self.ui.imagePreviewAuxiliary)

    @Slot()
    def show_game_both(self):
        self.show_game_main()
        self.show_game_aux()

    def next_game(self):
        selected_items = self.ui.gamesLW.selectedItems()
        if not selected_items:
            next_index = 0
        else:
            current_item = selected_items[0]
            current_index = self.ui.gamesLW.row(current_item)
            next_index = (current_index + 1) % self.ui.gamesLW.count()

        self.ui.gamesLW.setCurrentRow(next_index)
        next_item = self.ui.gamesLW.item(next_index)
        if next_item is not None:
            self.ui.gamesLW.itemPressed.emit(next_item)

    @Slot()
    def show_next_game_aux(self):
        self.next_game()
        self.show_game_aux()

    def draw_games_slide(self, label):
        game_row = self.ui.gamesLW.currentRow()
        text = (
            self.ui.gamesLW.currentItem().text()
            if game_row >= 0
            else "No game selected"
        )

        font = self.ui.gameTextFontCB.currentFont()
        scale = float(self.ui.gameTextSLD.value())

        if isinstance(label, SmartOverlayLabel):
            label.set_text_overlay(
                background_path=self._games_background_path,
                overlay_text=text,
                font=font,
                scale=scale,
                color=self._game_color_selected,
            )

    @Slot()
    def start_game_whamming(self):
        game_count = self.ui.gamesLW.count()
        if game_count == 0:
            return

        self._game_whammy_timer.setInterval(int(float(self.ui.secsPerGameWhamCB.currentText()) * 1000))
        self._game_whams = self.ui.gameWhammysSB.value()

        self.ui.gamesLW.setCurrentRow(self._whammy_randomizer.bounded(0, game_count))
        if self.ui.copytoAuxCB.isChecked():
            self.show_game_both()
        else:
            self.show_game_main()
        self._game_whammy_timer.start()

    @Slot()
    def next_game_wham(self):
        self._game_whams -= 1
        if self._game_whams <= 0:
            self._game_whammy_timer.stop()
            return

        self.ui.gamesLW.setCurrentRow(self._whammy_randomizer.bounded(0, self.ui.gamesLW.count()))
        self.draw_games_slide(self.ui.gameBackgroundLBL)
        if self.ui.copytoAuxCB.isChecked():
            self.show_game_both()
        else:
            self.show_game_main()

    @Slot()
    def add_game_to_list(self):
        if len(self.ui.addGameLE.text()) > 0:
            list_item = QListWidgetItem(self.ui.addGameLE.text())
            self.ui.gamesLW.addItem(list_item)
            self.ui.addGameLE.setText("")
            self.ui.addGameLE.setFocus()

    @Slot()
    def remove_all_games(self):
        self.ui.gamesLW.clear()
