# games_feature.py
# This Python file uses the following encoding: utf-8
import csv
from PySide6.QtCore import QObject, Slot, QItemSelection, Qt, QTimer, QFileInfo, QRandomGenerator
from PySide6.QtGui import QImageReader, QPixmap, QColor, QStandardItem, QStandardItemModel, QPainter, QFontMetrics
from PySide6.QtWidgets import QApplication, QStyle, QFileDialog, QColorDialog, QListWidgetItem

class games_feature(QObject):
    def __init__(self, ui, settings, mainDisplay, auxiliaryDisplay):

        self.ui = ui
        self._settings = settings
        self.mainDisplay = mainDisplay
        self.auxiliaryDisplay = auxiliaryDisplay
        self._game_whams = 0
        self._games_background_file = "" # The name of the last background will need to be stored so start as a zero length name
        self._games_background = None
        self._game_color_selected = QColor("black")
        self._whammy_randomizer = QRandomGenerator()

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
        self.ui.gameToBothShowPB.clicked.connect(self.show_game_both)
        self.ui.addGamePB.clicked.connect(self.add_game_to_list)
        self.ui.addGameLE.returnPressed.connect(self.add_game_to_list)
        self.ui.setGameToImagePB.clicked.connect(self.set_game_to_image)
        self.ui.setGameToSlidePB.clicked.connect(self.set_game_to_slide)

        # A double click on a list item will copy it to the list of game
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

    # Games List Management
    @Slot()
    def set_games_list(self):
        # Open file dialog to select a CSV file
        file_name = QFileDialog.getOpenFileName(self.ui, "Set Games List",
                                    self._settings.getConfigDir(),
                                    "Games Files (*.csv)")
        if len(file_name[0]) > 0:
            self._settings.setgames_file(fileName[0])
            self.rad_games()

    # Read the games file. Trigger on setting it and also at startup
    def read_games(self):
        self._games_model.clear()
        self._games_model.setHorizontalHeaderLabels(["Category/Name"])

        # Dictionary to track categories and their items
        categories = {}

        # Read the CSV file and add the first and second columns to the list view
        games_file = self._settings.getGamesFile()
        if len(games_file) >0:
            with open(games_file, newline='', encoding='utf-8') as csv_file:
                reader = csv.reader(csv_file)
                next(reader)  # Skip header

                for row in reader:
                    if len(row) < 3:
                        continue  # Skip rows without enough columns

                    category, name, description = row[0], row[1], row[2]

                    # Check if category exists in dictionary; if not, create it
                    if category not in categories:
                        category_item = QStandardItem(category)
                        category_item.setFlags( Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                        self._games_model.appendRow([category_item])
                        categories[category] = category_item

                    # Create the item for Name and set its description as data
                    name_item = QStandardItem(name)
                    name_item.setData(description, Qt.UserRole)  # Store description in UserRole
                    name_item.setFlags( Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                    # Add name item under the category
                    categories[category].appendRow([name_item])

            # Expand all items for better view
            self._games_tree_view.expandAll()

    @Slot()
    def add_to_games(self, index):
        # Get the item clicked in the tree view
        item = self._games_model.itemFromIndex(index)

        if item:
            if item.hasChildren():  # If the item has children, it is a category
                # Iterate over all child items and add them to the games list
                for row in range(item.rowCount()):
                    list_item = QListWidgetItem(item.child(row).text())
                    self.ui.gamesLW.addItem(list_item)
            elif item.parent():  # If the item has a parent, it is a name
                description = item.data(Qt.UserRole)
                list_item = QListWidgetItem(item.text())
                self.ui.gamesLW.addItem(list_item)

    @Slot()
    def search_game_tree(self):
        # Perform a search using the keyboardSearch function
        search_text = self.ui.gameSearchLE.text()
        if search_text:
            self._games_tree_view.keyboardSearch(search_text)

    @Slot()
    def add_selected_to_games(self):
        # Get the currently selected item in the tree view
        selected_indexes = self._games_tree_view.selectionModel().selectedIndexes()

        if selected_indexes:
            index = selected_indexes[0]  # Use the first selected index
            item = self._games_model.itemFromIndex(index)

            if item:
                if item.hasChildren():  # If the item has children, it is a category
                    for row in range(item.rowCount()):
                        list_item = QListWidgetItem(item.child(row).text())
                        self.ui.gamesLW.addItem(list_item)
                elif item.parent():  # If the item has a parent, it is a name
                    list_item = QListWidgetItem(item.text())
                    self.ui.gamesLW.addItem(list_item)
    @Slot()
    def remove_selected_games(self):
        # Get all selected items in the gamesLW
        selected_items = self.ui.gamesLW.selectedItems()

        # Remove each selected item
        for item in selected_items:
            self.ui.gamesLW.takeItem(self.ui.gamesLW.row(item))

    # Scale the text whenever the slider moves
    @Slot(int)
    def game_font_slider_changed(self, value):
        self.draw_games_slide(self.ui.gameBackgroundLBL)

    # Trigger a redraw on font change
    @Slot(int)
    def game_font_changed(self, index):
        self.draw_games_slide(self.ui.gameBackgroundLBL)

    # Trigger a redraw on game name change
    @Slot(int)
    def game_changed(self, row):
        self.draw_games_slide(self.ui.gameBackgroundLBL)

    # Select the color for the text
    @Slot()
    def pick_game_text_color(self):
        color_chooser = QColorDialog(self.ui)
        self._game_color_selected = color_chooser.getColor(title = 'Pick the game text color')

        if self._game_color_selected != None:
            self.draw_games_slide(self.ui.gameBackgroundLBL)

    @Slot()
    def load_background(self):
        selected_file_name = QFileDialog.getOpenFileName(self.ui, "Select Background", self._settings.getMediaDir() , "Background Files (*.png *.jpg *.bmp)")
        self._games_background_file = selected_file_name[0]

        if QFileInfo.exists(self._games_background_file):
            mediaInfo = QFileInfo(self._games_background_file)
            if bytes(mediaInfo.suffix().lower(),"ascii") in  QImageReader.supportedImageFormats():
                reader = QImageReader(self._games_background_file)
                reader.setAutoTransform(True)
                self._games_background = reader.read()
                self.draw_games_slide(self.ui.gameBackgroundLBL)

    @Slot()
    def set_game_to_image(self):
        self._games_background_file = self.ui.mediaFileNameLBL.text()

        if QFileInfo.exists(self._games_background_file):
            mediaInfo = QFileInfo(self._games_background_file)
            if bytes(mediaInfo.suffix().lower(),"ascii") in  QImageReader.supportedImageFormats():
                reader = QImageReader(self._games_background_file)
                reader.setAutoTransform(True)
                self._games_background = reader.read()
                self.draw_games_slide(self.ui.gameBackgroundLBL)

    @Slot()
    def set_game_to_slide(self):
        index = self.ui.slideShowFilesTreeView.selectionModel().currentIndex()
        media_model = self.ui.slideShowFilesTreeView.model()

        if not media_model.isDir(index):
            image_file_info = media_model.fileInfo(index)
            self._games_background_file = image_file_info.absoluteFilePath()

            if QFileInfo.exists(self._games_background_file):
                mediaInfo = QFileInfo(self._games_background_file)
                if bytes(mediaInfo.suffix().lower(),"ascii") in  QImageReader.supportedImageFormats():
                    reader = QImageReader(self._games_background_file)
                    reader.setAutoTransform(True)
                    self._games_background = reader.read()
                    self.draw_games_slide(self.ui.gameBackgroundLBL)

    @Slot()
    def show_game_main(self):
        game_row = self.ui.gamesLW.currentRow()
        if game_row >= 0:
            # Get the text of the first selected item
            text = self.ui.gamesLW.currentItem().text()
        else:
            # Default text if no item is selected
            text = "No game selected"

        font = self.ui.gameTextFontCB.currentFont()
        font.setPixelSize(36)
        self.mainDisplay.showGame(self._games_background, text, font, self.ui.gameTextSLD.value(), self._game_color_selected)
        self.draw_games_slide(self.ui.imagePreviewMain)

    @Slot()
    def show_game_aux(self):
        game_row = self.ui.gamesLW.currentRow()
        if game_row >= 0:
            # Get the text of the first selected item
            text = self.ui.gamesLW.currentItem().text()
        else:
            # Default text if no item is selected
            text = "No game selected"

        font = self.ui.gameTextFontCB.currentFont()
        font.setPixelSize(36)
        self.auxiliaryDisplay.showGame(self._games_background, text, font, self.ui.gameTextSLD.value(), self._game_color_selected)
        self.draw_games_slide(self.ui.imagePreviewAuxiliary)

    @Slot()
    def show_game_both(self):
        self.show_game_main()
        self.show_game_aux()

    def draw_games_slide(self, label):
        # Fetch the text
        game_row = self.ui.gamesLW.currentRow()
        if game_row >= 0:
            # Get the text of the first selected item
            text = self.ui.gamesLW.currentItem().text()
        else:
            # Default text if no item is selected
            text = "No game selected"

        # Use a fresh copy of the background
        if self._games_background:
            pixmap = QPixmap(QPixmap.fromImage(self._games_background.scaled(label.size())))
            # Create a QPainter to draw text on the image
            painter = QPainter(pixmap)
            painter.setPen(self._game_color_selected)  # Set text color

            # Scale the the text so that it its width is the percentage given by the slider. Use 36 pixels
            # just to get a text length to scale with using a number that has lots of integer divisions.
            font = self.ui.gameTextFontCB.currentFont()
            font.setPixelSize(36)
            font_metrics = QFontMetrics(font)
            pixels_wide = font_metrics.horizontalAdvance(text) # Get text length at baseline pixel setting

            # Now we need k such that k*(pw/bw) = slider/100 since slider was set up to represent a percent
            # Therefore k = (slider*bw)/(pw*100). This is used to adjust the font setting
            newFontPixelSize = int(36.0 * (self.ui.gameTextSLD.value()*label.width())/(100.0*pixels_wide))
            font.setPixelSize(newFontPixelSize)
            painter.setFont(font)    # Use the selected game text font
            painter.drawText(pixmap.rect(), Qt.AlignCenter, text)  # Draw text centered
            painter.end()
            label.setPixmap(pixmap)

    # Game Whammy Controls
    @Slot()
    def start_game_whamming(self):
        # If there are no games here is no whammy
        game_count = self.ui.gamesLW.count()
        if game_count == 0:
            return

        # The whammy delay is given by the secsPerGameWhamCB drop down
        self._game_whammy_timer.setInterval(int(float(self.ui.secsPerGameWhamCB.currentText())*1000))
        self._game_whams = self.ui.gameWhammysSB.value()

        self.ui.gamesLW.setCurrentRow(self._whammy_randomizer.bounded(0, game_count))
        self.show_game_main()
        self._game_whammy_timer.start()

    # Triggered by the time out of the Game whammy timer and increments to the next random selection of game
    @Slot()
    def next_game_wham(self):
        self._game_whams -= 1
        if self._game_whams <= 0:
            self._game_whammy_timer.stop()
            return

        self.ui.gamesLW.setCurrentRow(self._whammy_randomizer.bounded(0, self.ui.gamesLW.count()))
        self.draw_games_slide(self.ui.gameBackgroundLBL)
        self.show_game_main()

    # Option to manually add a game or any one line of content for that matter to the list
    @Slot()
    def add_game_to_list(self):
        if len(self.ui.addGameLE.text())> 0:
            list_item = QListWidgetItem(self.ui.addGameLE.text())
            self.ui.gamesLW.addItem(list_item)
            self.ui.addGameLE.setText("")
            self.ui.addGameLE.setFocus()

    # Clear the list of games
    @Slot()
    def remove_all_games(self):
        self.ui.gamesLW.clear()

    # When an item in the games tree is selected then attempt to dereference the item so that its decription
    # can be copied to the description display
    @Slot(QItemSelection, QItemSelection)
    def game_selected(self, selected, deselected):
        indexes = selected.indexes()
        item = indexes[0]
        description = item.data(Qt.UserRole)
        self.ui.gameDescriptionTE.setText(description)
