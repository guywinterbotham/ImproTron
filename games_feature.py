# games_feature.py
# This Python file uses the following encoding: utf-8
import csv
import logging
from PySide6.QtCore import QObject, Slot, QItemSelection, Qt, QTimer, QFileInfo, QRandomGenerator
from PySide6.QtGui import QFontMetrics, QFont, QColor, QMovie, QPixmap, QPainter, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QStyle, QFileDialog, QColorDialog, QListWidgetItem, QLabel

logger = logging.getLogger(__name__)

# A custom QLabel that seamlessly handles either a running animated background or a static background image, overlaying dynamic text dynamically
# without layout stacks or CSS. Reuses a single permanent QMovie instance to guarantee absolute memory leak protection.
class SmartOverlayLabel(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.overlay_text = ""
        self.overlay_font = QFont()
        self.overlay_color = QColor(Qt.white)

        # Allocate EXACTLY ONE reusable movie engine container in memory
        self._reusable_movie = QMovie(self)
        self._raw_file_path = "" # Track path to handle dynamic resizing operations cleanly

        # Permanently bind the canvas repaint engine once at initialization
        self._reusable_movie.frameChanged.connect(self._trigger_movie_repaint)

    def set_text_overlay(self, text: str, font: QFont, color: QColor):
        self.overlay_text = text
        self.overlay_font = font
        self.overlay_color = color
        self.update()  # Force an immediate repaint of the text layer

    def set_background_asset(self, file_name):
        if not file_name or not QFileInfo.exists(file_name):
            return

        # Optimization: If the asset target hasn't changed, skip parsing overhead
        if self._raw_file_path == file_name:
            return

        self._raw_file_path = file_name
        suffix = QFileInfo(file_name).suffix().lower()

        # Always halt processing loops before modifying file tracks
        self.clear_asset()

        # Ask QMovie if it natively supports this extension (GIF, WEBP, etc.)
        if bytes(suffix, "ascii") in QMovie.supportedFormats():
            # Clear out standard pixmaps so they don't fight with the video buffers
            self.setPixmap(QPixmap())

            # Point the permanent engine at the new file location
            self._reusable_movie.setFileName(file_name)
            self._reusable_movie.setSpeed(100)

            # Re-hook the single-loop safety guard tracking logic before running
            try:
                self._reusable_movie.frameChanged.connect(self._handle_single_loop)
            except Exception:
                pass

            self.setMovie(self._reusable_movie)
            self._reusable_movie.start()
        else:
            pixmap = QPixmap(file_name)
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

    def clear_asset(self):
        """
        Safely clears all current media and settings out of the label widget context.
        Forces immediate garbage collection on underlying C++ pixel buffers,
        ensuring other application features can use this label completely clean.
        """
        self._reusable_movie.stop()  # Turns off frame tickers completely
        self.setMovie(None)          # Flushes the raw uncompressed C++ movie frame buffer caches
        self.setPixmap(QPixmap())    # Wipes any active static images
        self._raw_file_path = ""     # Resets our file path tracking loop
        self.overlay_text = ""       # Clears out background game name strings
        self.update()                # Refreshes canvas to a clean, blank slate

    @Slot(int)
    def _trigger_movie_repaint(self, frame_number):
        """Forces an explicit surface update cycle when the movie engine generates frames."""
        self.update()

    def _handle_single_loop(self, frame_number):
        """
        Monitors the animation frames and halts playback the instant
        the first full cycle reaches its final frame index.
        """
        total_frames = self._reusable_movie.frameCount()

        # frame_number is 0-indexed, so the final frame is total_frames - 1
        if total_frames > 0 and frame_number >= total_frames - 1:
            try:
                # Disconnect dynamically to prevent recursive execution during termination passes
                self._reusable_movie.frameChanged.disconnect(self._handle_single_loop)
            except Exception:
                pass

            # Freeze the movie engine frame cache exactly where it is to drop idle CPU usage to zero
            self._reusable_movie.setPaused(True)

    def resizeEvent(self, event):
        """Ensures both static images and animated clips scale dynamically with the UI panel."""
        super().resizeEvent(event)
        if self._raw_file_path:
            suffix = QFileInfo(self._raw_file_path).suffix().lower()

            if bytes(suffix, "ascii") in QMovie.supportedFormats():
                # FIX: Running set_background_asset on resize resets the whole movie tracking cycle
                # causing infinite single-loop resets. Instead, just recalculate aspect boundaries on the active frames.
                if self.movie():
                    self.setMovie(self.movie())
            else:
                # Static images can scale down linearly via their base assets
                pixmap = QPixmap(self._raw_file_path)
                self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

    def setMovie(self, movie):
        """
        Intercepts incoming animation sequences to turn off the center-third
        magnification distortion before the native painter engine runs.
        """
        if movie:
            # 1. Turn off QLabel's native force-to-edges stretching flag
            self.setScaledContents(False)

            # 2. Query the real native pixel dimensions of the source animation asset
            movie_size = movie.currentPixmap().size()
            if movie_size.isValid() and not movie_size.isEmpty():
                # Scale the animation bounds to fit your UI layout tab geometry
                # while strictly preserving its natural proportions
                scaled_size = movie_size.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatio
                )
                movie.setScaledSize(scaled_size)
            else:
                # Fallback layout calculation if the movie is still loading its first frame
                movie.setScaledSize(self.size())

        # 3. Pass the configured asset cleanly down to the base C++ engine track
        super().setMovie(movie)

    def paintEvent(self, event):
        # 1. Let the native QLabel engine handle rendering the underlying frames first.
        super().paintEvent(event)

        # 2. Layer the sharp text overlay precisely on top of the native canvas pass
        if hasattr(self, 'overlay_text') and self.overlay_text:
            painter = QPainter(self)

            # Prevent the painter from clipping out of bounds or using low-quality transforms
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            if hasattr(self, 'overlay_font') and self.overlay_font:
                painter.setFont(self.overlay_font)
            if hasattr(self, 'overlay_color') and self.overlay_color:
                painter.setPen(self.overlay_color)

            # Draw the text overlay crisply centered directly over the composited frame surface
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.overlay_text)

            # Flush paint commands immediately
            painter.end()

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

        # Maintain a model/view of the games
        self._games_tree_view = self.ui.gamesTreeView
        self._games_model = QStandardItemModel(self._games_tree_view)
        self._games_tree_view.setModel(self._games_model)
        self.read_games()

        self.connect_slots()

    def connect_slots(self):
        # Games List Management Wiring
        self.ui.setGamesListPB.clicked.connect(self.set_games_list)
        self.ui.loadBackgroundPB.clicked.connect(self.load_background)
        self.ui.gameTextColorPB.clicked.connect(self.pick_game_text_color)
        self.ui.gameTextSLD.valueChanged.connect(self.game_font_slider_changed)
        self.ui.gameTextFontCB.currentIndexChanged.connect(self.game_font_changed)
        self.ui.gamesLW.currentRowChanged.connect(self.game_changed)
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

        # Connect game search
        self.ui.gameSearchLE.returnPressed.connect(self.search_game_tree)
        self.ui.searchGamePB.clicked.connect(self.search_game_tree)

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

    @Slot()
    def add_to_games(self, index):
        item = self._games_model.itemFromIndex(index)
        if item:
            if item.hasChildren():
                for row in range(item.rowCount()):
                    list_item = QListWidgetItem(item.child(row).text())
                    self.ui.gamesLW.addItem(list_item)
            elif item.parent():
                list_item = QListWidgetItem(item.text())
                self.ui.gamesLW.addItem(list_item)

    @Slot()
    def search_game_tree(self):
        search_text = self.ui.gameSearchLE.text()
        if search_text:
            self._games_tree_view.keyboardSearch(search_text)

    @Slot()
    def add_selected_to_games(self):
        selected_indexes = self._games_tree_view.selectionModel().selectedIndexes()
        if selected_indexes:
            index = selected_indexes[0]
            item = self._games_model.itemFromIndex(index)
            if item:
                if item.hasChildren():
                    for row in range(item.rowCount()):
                        list_item = QListWidgetItem(item.child(row).text())
                        self.ui.gamesLW.addItem(list_item)
                elif item.parent():
                    list_item = QListWidgetItem(item.text())
                    self.ui.gamesLW.addItem(list_item)

    @Slot()
    def remove_selected_games(self):
        selected_items = self.ui.gamesLW.selectedItems()
        for item in selected_items:
            self.ui.gamesLW.takeItem(self.ui.gamesLW.row(item))

    @Slot(int)
    def game_font_slider_changed(self, value):
        self.draw_games_slide(self.ui.gameBackgroundLBL)

    @Slot(int)
    def game_font_changed(self, index):
        self.draw_games_slide(self.ui.gameBackgroundLBL)

    @Slot(int)
    def game_changed(self, row):
        self.draw_games_slide(self.ui.gameBackgroundLBL)

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

        # Notify the UI layout engine components to reset their active source tracks
        if isinstance(self.ui.gameBackgroundLBL, SmartOverlayLabel):
            self.ui.gameBackgroundLBL.set_background_asset(games_background_file)

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
        self.mainDisplay.showGame(self._games_background_path, text, font, slider, self._game_color_selected)

        self.draw_games_slide(self.ui.imagePreviewMain)

    @Slot()
    def show_game_aux(self):
        game_row = self.ui.gamesLW.currentRow()
        text = self.ui.gamesLW.currentItem().text() if game_row >= 0 else "No game selected"

        font = self.ui.gameTextFontCB.currentFont()
        slider = self.ui.gameTextSLD.value()
        self._settings.set_game_text_size(slider)

        # Display the game frame on the aux monitor
        self.auxiliaryDisplay.showGame(self._games_background_path, text, font, slider, self._game_color_selected)

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
        text = self.ui.gamesLW.currentItem().text() if game_row >= 0 else "No game selected"

        font = self.ui.gameTextFontCB.currentFont()
        font.setPixelSize(36)
        font_metrics = QFontMetrics(font)
        pixels_wide = font_metrics.horizontalAdvance(text)

        if pixels_wide > 0:
            newFontPixelSize = int(36.0 * (self.ui.gameTextSLD.value() * label.width()) / (100.0 * pixels_wide))
            font.setPixelSize(max(1, newFontPixelSize))

        # Update the background asset directly, then apply the text overlay
        if isinstance(label, SmartOverlayLabel):
            # Let the method itself handle asset assignment cleanly
            label.set_background_asset(self._games_background_path)
            label.set_text_overlay(text, font, self._game_color_selected)

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

    @Slot(QItemSelection, QItemSelection)
    def game_selected(self, selected, deselected):
        indexes = selected.indexes()
        if len(indexes):
            item = indexes[0]
            description = item.data(Qt.UserRole)
            self.ui.gameDescriptionTE.setText(description)
