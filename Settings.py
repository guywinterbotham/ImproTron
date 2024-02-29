# This Python file uses the following encoding: utf-8
# The Settings file carries any settings that need to persist
import json
from PySide6.QtCore import Qt, QStandardPaths, QDir, QPoint, QFileInfo
from PySide6.QtGui import QColor, QGuiApplication

class Settings:
    def __init__(self):
        # Create a dictionary of default values
        self._settings = {}
        self.setConfigDir(QStandardPaths.standardLocations(QStandardPaths.GenericConfigLocation)[0]+"/ImproTron")
        self._defaultConfig = '/ImproTron.cfg'

        # Attempt to load the default settings
        if not self.load():

            # Default Location of Pictures, Gifs and Movies
            self.setMediaDir(QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0])

            # Default Location of Sounds, and SoundFX (Wav Files)
            self.setSoundDir(QStandardPaths.standardLocations(QStandardPaths.MusicLocation)[0])

            # Team Colors
            self.setLeftTeamColor(QColor(Qt.blue))
            self.setRightTeamColor(QColor(Qt.red))

            # Screen Locations
            primaryScreen = QGuiApplication.primaryScreen()
            primaryLocation = primaryScreen.availableGeometry()
            self.setMainLocation(primaryLocation.topLeft())
            self.setAuxLocation(primaryLocation.topLeft())

    def save(self):
        # Convert the Python dictionary to a JSON string
        json_data = json.dumps(self._settings, indent=2)

        # Write the JSON string to a file
        with open(self._settings['configDir'] + self._defaultConfig, 'w') as json_file:
            json_file.write(json_data)

    def load(self):
        configFileInfo = QFileInfo(self._settings['configDir'] + self._defaultConfig)
        if configFileInfo.exists():
            with open(configFileInfo.absoluteFilePath(), 'r') as json_file:
                self._settings = json.load(json_file)
                return True

        return False

    def getLeftTeamColor(self):
        return QColor.fromString(self._settings['leftTeamColor'])

    def setLeftTeamColor(self, color):
        self._settings['leftTeamColor'] = "#{:06x}".format(color.rgb())

    def getRightTeamColor(self):
        return QColor.fromString(self._settings['rightTeamColor'])

    def setRightTeamColor(self, color):
        self._settings['rightTeamColor'] = "#{:06x}".format(color.rgb())

    def getConfigDir(self):
        return self._settings['configDir']

    def setConfigDir(self, configDir):
        configInfo = QDir(configDir)
        if not configInfo.exists():
            success = configInfo.mkpath(configDir)
            if not success:
                print("Failed to create configuration directory: ", configDir)
        self._settings['configDir'] = configDir

    def getMediaDir(self):
        return self._settings['mediaDir']

    def setMediaDir(self, mediaDir):
        self._settings['mediaDir'] = mediaDir

    def getSoundDir(self):
        return self._settings['soundDir']

    def setSoundDir(self, mediaDir):
        self._settings['soundDir'] = mediaDir

    def getMainLocation(self):
        return QPoint(-65, -849)
        #return QPoint(int(self._settings['mainX']), int(self._settings['mainY']))

    def setMainLocation(self, p):
        self._settings['mainX'] = p.x()
        self._settings['mainY'] = p.y()

    def getAuxLocation(self):
        return QPoint(-100, -741)
        #return QPoint(int(self._settings['auxX']), int(self._settings['auxY']))

    def setAuxLocation(self, p):
        self._settings['auxX'] = p.x()
        self._settings['auxY'] = p.y()
