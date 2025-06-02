import logging
from PySide6.QtCore import QSettings, QStandardPaths, QDir, QCoreApplication, QPoint, QFileInfo, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog

logger = logging.getLogger(__name__)

class Settings:
    DEFAULTS = {
        'leftTeamColor': QColor(Qt.blue),
        'rightTeamColor': QColor(Qt.red),
        'leftTeamName': "Left Team",
        'rightTeamName': "Right Team",
        'promosDirectory': "",
        'slideshowDelay': 10,
        'startupImage': "",
        'configDir': QStandardPaths.standardLocations(QStandardPaths.GenericConfigLocation)[0] + "/ImproTron",
        'mediaDirectory': QStandardPaths.writableLocation(QStandardPaths.PicturesLocation),
        'videoDirectory': QStandardPaths.writableLocation(QStandardPaths.MoviesLocation),
        'soundDirectory': QStandardPaths.writableLocation(QStandardPaths.MusicLocation),
        'documentDirectory': QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation),
        'lastHotButton': "",
        'touchPortalConnect': False,
        'gamesFile': "",
        'mainLocation': QPoint(0, 0),
        'auxLocation': QPoint(0, 0),
    }

    def __init__(self):
        QCoreApplication.setOrganizationName("ComedySportz")
        QCoreApplication.setApplicationName("ImproTron")
        self.settings = QSettings()
        self.load_custom_colors()
        configDir = self.get_config_dir()
        config_info = QDir(configDir)
        if not config_info.exists():
            if not config_info.mkpath(configDir):
                logger.critical(f"Failed to create configuration directory: {configDir}")

    def _get(self, key):
        return self.settings.value(key, self.DEFAULTS.get(key))

    def _set(self, key, value):
        self.settings.setValue(key, value)

    def restore_defaults(self):
        self.settings.clear()

    def get_settings_text(self):
        # Append settings information
        text = f"\n\nSettings location: {self.settings.fileName()}"
        text += "\n--- Settings ---\n"
        keys = self.settings.allKeys()
        if keys:
            for key in keys:
                value = self.settings.value(key)  # access the underlying QSettings
                text += f"{key}: {value}\n"
        else:
            text += "No settings stored.\n"

        return text

    def get_location(self):
        return self.settings.fileName()


    def get_config_dir(self):
        return self._get('configDir')

    # Use the application settings mechanism to store colors over the native solution
    # The QColorDialog was not storing colors across versions
    def save_custom_colors(self):
        for i in range(16):
            color = QColorDialog.customColor(i)
            self.settings.setValue(f"CustomColor{i}", color.name())

    def load_custom_colors(self):
        for i in range(16):
            color_name = self.settings.value(f"CustomColor{i}")
            if color_name:
                QColorDialog.setCustomColor(i, QColor(color_name))

    def pick_left_team_color(self, ui):
        colorSelected = QColorDialog.getColor(self.get_left_team_color(), ui,title = 'Pick Left Team Color')
        self.save_custom_colors()
        if colorSelected.isValid():
            self._set('leftTeamColor', colorSelected)

        return colorSelected

    def get_left_team_color(self):
        return self._get('leftTeamColor')

    def pick_right_team_color(self,ui):
        colorSelected = QColorDialog.getColor(self.get_right_team_color(), ui,title = 'Pick Right Team Color')
        self.save_custom_colors()
        if colorSelected.isValid():
            self._set('rightTeamColor', colorSelected)

        return colorSelected

    def get_right_team_color(self):
        return self._get('rightTeamColor')

    def set_left_team_name(self, name):
        self._set('leftTeamName', name)

    def get_left_team_name(self):
        return self._get('leftTeamName')

    def set_right_team_name(self, name):
        self._set('rightTeamName', name)

    def get_right_team_name(self):
        return self._get('rightTeamName')

    def set_promos_directory(self, path):
        self._set('promosDirectory', path)

    def get_promos_directory(self):
        return self._get('promosDirectory')

    def set_media_directory(self, path):
        self._set('mediaDirectory', path)

    def get_media_directory(self):
        return self._get('mediaDirectory')

    def set_video_directory(self, path):
        self._set('videoDirectory', path)

    def get_video_directory(self):
        return self._get('videoDirectory')

    def set_sound_directory(self, path):
        self._set('soundDirectory', path)

    def get_sound_directory(self):
        return self._get('soundDirectory')

    def set_document_directory(self, path):
        self._set('documentDirectory', path)

    def get_document_directory(self):
        return self._get('documentDirectory')

    def set_slideshow_delay(self, delay: int):
        self._set('slideshowDelay', delay)

    def get_slideshow_delay(self):
        return int(self._get('slideshowDelay'))

    def set_startup_image(self, path):
        self._set('startupImage', path)

    def get_startup_image(self):
        return self._get('startupImage')

    def set_main_location(self, point: QPoint):
        self._set('mainLocation', point)

    def get_main_location(self):
        return self._get('mainLocation') or QPoint(0, 0)

    def set_aux_location(self, point: QPoint):
        self._set('auxLocation', point)

    def get_aux_location(self):
        return self._get('auxLocation') or QPoint(0, 0)

    def set_touch_portal_connect(self, flag: bool):
        self._set('touchPortalConnect', flag)

    def get_touch_portal_connect(self):
        return self._get('touchPortalConnect') in [True, 'true', '1']

    def set_last_hot_button_file(self, path):
        self._set('lastHotButton', path)

    def get_last_hot_button_file(self):
        path = self._get('lastHotButton')
        return path if QFileInfo(path).exists() else self.DEFAULTS['lastHotButton']

    def set_games_file(self, path):
        self._set('gamesFile', path)

    def get_games_file(self):
        path = self._get('gamesFile')
        return path if QFileInfo(path).exists() else self.DEFAULTS['gamesFile']
