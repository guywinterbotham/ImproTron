import json
import logging
from PySide6.QtCore import QStandardPaths, QDir, QPoint, QFileInfo, Qt
from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)

class Settings:
    DEFAULT_CONFIG_FILE = '/ImproTron.cfg'
    DEFAULTS = {
        'leftTeamColor': QColor(Qt.blue).name(),
        'rightTeamColor': QColor(Qt.red).name(),
        'leftTeamName': "Left Team",
        'rightTeamName': "Right Team",
        'promosDirectory': "",
        'slideshowDelay': 10,
        'startupImage': "",
        'configDir': QStandardPaths.standardLocations(QStandardPaths.GenericConfigLocation)[0] + "/ImproTron",
        'mediaDirectory': QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0],
        'videoDirectory': QStandardPaths.standardLocations(QStandardPaths.MoviesLocation)[0],
        'soundDirectory': QStandardPaths.standardLocations(QStandardPaths.MusicLocation)[0],
        'documentDirectory': QStandardPaths.standardLocations(QStandardPaths.DocumentsLocation)[0],
        'lastHotButton': "",
        'touchPortalConnect': False,
        'gamesFile': "",
        'mainX': 0,
        'mainY': 0,
        'auxX': 0,
        'auxY': 0,
    }

    def __init__(self):
        self._settings = {}
        configDir = self.get_config_dir()
        config_info = QDir(configDir)
        if not config_info.exists():
            if not config_info.mkpath(configDir):
                logger.critical(f"Failed to create configuration directory: {configDir}")
        self.load()

    def _get(self, key):
        return self._settings.get(key, self.DEFAULTS.get(key))

    def _set(self, key, value):
        self._settings[key] = value

    def load(self):
        config_path = self.get_config_dir() + self.DEFAULT_CONFIG_FILE
        try:
            with open(config_path, 'r', encoding='utf8') as json_file:
                self._settings = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load configuration: {e}. Using defaults.")
            self._settings = self.DEFAULTS.copy()

    def save(self):
        config_path = self.get_config_dir() + self.DEFAULT_CONFIG_FILE
        logger.info(f"Saving config to: {config_path}")
        try:
            json_file = open(config_path, 'w', encoding='utf8')
            json.dump(self._settings, json_file, indent=2)
            json_file.close()
        except IOError as e:
            logger.error(f"Failed to save configuration: {e}")

    def get_config_dir(self):
        return self._get('configDir')

    def set_left_team_color(self, color):
        self._set('leftTeamColor', color.name())

    def get_left_team_color(self):
        return QColor(self._get('leftTeamColor'))

    def set_right_team_color(self, color):
        self._set('rightTeamColor', color.name())

    def get_right_team_color(self):
        return QColor(self._get('rightTeamColor'))

    def set_left_team_name(self, team):
        self._set('leftTeamName', team)

    def get_left_team_name(self):
        return self._get('leftTeamName')

    def set_right_team_name(self, team):
        self._set('rightTeamName', team)

    def get_right_team_name(self):
        return self._get('rightTeamName')

    def set_promos_directory(self, directory):
        self._set('promosDirectory', directory)

    def get_promos_directory(self):
        return self._get('promosDirectory')

    def set_media_directory(self, directory):
        self._set('mediaDirectory', directory)

    def get_media_directory(self):
        return self._get('mediaDirectory')

    def set_video_directory(self, directory):
        self._set('videoDirectory', directory)

    def get_video_directory(self):
        return self._get('videoDirectory')

    def set_sound_directory(self, directory):
        self._set('soundDirectory', directory)

    def get_sound_directory(self):
        return self._get('soundDirectory')

    def set_document_directory(self, directory):
        self._set('documentDirectory', directory)

    def get_document_directory(self):
        return self._get('documentDirectory')

    def set_slideshow_delay(self, delay):
        self._set('slideshowDelay', delay)

    def get_slideshow_delay(self):
        return self._get('slideshowDelay')

    def set_startup_image(self, image):
        self._set('startupImage', image)

    def get_startup_image(self):
        return self._get('startupImage')

    def set_main_location(self, point):
        self._set('mainX', point.x())
        self._set('mainY', point.y())

    def get_main_location(self):
        x = self._get('mainX')
        y = self._get('mainY')
        return QPoint(x, y)

    def set_aux_location(self, point):
        self._set('auxX', point.x())
        self._set('auxY', point.y())

    def get_aux_location(self):
        x = self._get('auxX')
        y = self._get('auxY')
        return QPoint(x, y)

    def set_touch_portal_connect(self, flag):
        if isinstance(flag, bool):
            self._set('touchPortalConnect', flag)

    def get_touch_portal_connect(self):
        return self._get('touchPortalConnect')

    def set_last_hot_button_file(self, file):
        self._set('lastHotButton', file)

    def get_last_hot_button_file(self):
        file_path = self._get('lastHotButton')
        if QFileInfo(file_path).exists():
            return file_path
        return self.DEFAULTS.get('lastHotButton')

    def set_games_file(self, file):
        self._set('gamesFile', file)

    def get_games_file(self):
        file_path = self._get('gamesFile')
        if QFileInfo(file_path).exists():
            return file_path
        return self.DEFAULTS.get('gamesFile')
