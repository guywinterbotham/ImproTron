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

        # Attempt to load the default settings. try/except logic is used to populate with defaults
        self.load()

    # end init

    def save(self):
        # Write the JSON string to a file. Since certain settings could have special characters, encode
        with open(self._settings['configDir'] + self._defaultConfig, 'w', encoding='utf8') as json_file:
            json.dump(self._settings, json_file, indent=2)

    def load(self):
        configFileInfo = QFileInfo(self._settings['configDir'] + self._defaultConfig)
        if configFileInfo.exists():
            with open(configFileInfo.absoluteFilePath(), 'r') as json_file:
                self._settings = json.load(json_file)

    def setConfigDir(self, configDir):
        configInfo = QDir(configDir)
        if not configInfo.exists():
            success = configInfo.mkpath(configDir)
            if not success:
                print("Failed to create configuration directory: ", configDir)
        self._settings['configDir'] = configDir

    def getConfigDir(self):
        return self._settings['configDir']

    def setLeftTeamColor(self, color):
        self._settings['leftTeamColor'] = "#{:06x}".format(color.rgb())

    def getLeftTeamColor(self):
        try:
            _leftTeamColor = QColor.fromString(self._settings['leftTeamColor'])
        except:
            self.setLeftTeamColor(QColor(Qt.blue))
            _leftTeamColor = QColor.fromString(self._settings['leftTeamColor'])

        return _leftTeamColor

    def setRightTeamColor(self, color):
        self._settings['rightTeamColor'] = "#{:06x}".format(color.rgb())

    def getRightTeamColor(self):
        try:
            _rightTeamColor = QColor.fromString(self._settings['rightTeamColor'])
        except:
            self.setRightTeamColor(QColor(Qt.red))
            _rightTeamColor = QColor.fromString(self._settings['rightTeamColor'])

        return _rightTeamColor

    def setLeftTeamName(self, name):
        self._settings['leftTeamName'] = name

    def getLeftTeamName(self):
        try:
            _leftTeamName = self._settings['leftTeamName']
        except:
            self._settings['leftTeamName']  = _leftTeamName = "Left Team"

        return _leftTeamName

    def setRightTeamName(self, name):
        self._settings['rightTeamName'] = name

    def getRightTeamName(self):
        try:
            _rightTeamName = self._settings['rightTeamName']
        except:
            self._settings['rightTeamName'] = _rightTeamName = "Right Team"

        return _rightTeamName

    def setPromosDirectory(self, name):
        self._settings['promosDirectory'] = name

    def getPromosDirectory(self):
        try:
            _promosDir = self._settings['promosDirectory']
        except:
            self._settings['promosDirectory'] = _promosDir = ""

        return _promosDir

    def setSlideshowDelay(self, value):
        self._settings['slideshowDelay'] = value

    def getSlideshowDelay(self):
        try:
            _slideShowDelay = self._settings['slideshowDelay']
        except:
            self._settings['slideshowDelay'] = _slideShowDelay = 10

        return _slideShowDelay

    def setStartupImage(self, name):
        self._settings['startupImage'] = name

    def getStartupImage(self):
        try:
            _startupImage = self._settings['startupImage']
        except:
            self._settings['startupImage'] = _startupImage = ""

        return _startupImage

    def setMediaDir(self, mediaDir):
        self._settings['mediaDir'] = mediaDir

    def getMediaDir(self):
        try:
            _mediaDir = self._settings['mediaDir']
        except:  # Default Location of Pictures and Gifs
            self._settings['mediaDir'] = _mediaDir = QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0]

        return _mediaDir

    def setVideoDir(self, mediaDir):
        self._settings['videoDir'] = mediaDir

    def getVideoDir(self):
        try:
            _videoDir = self._settings['videoDir']
        except: # Default Videos
            self._settings['videoDir'] = _videoDir = QStandardPaths.standardLocations(QStandardPaths.MoviesLocation)[0]

        return _videoDir

    def setSoundDir(self, mediaDir):
        self._settings['soundDir'] = mediaDir

    def getSoundDir(self):
        try:
            _soundDir = self._settings['soundDir']
        except: # Default Location of Sounds, and SoundFX (Wav Files)
            self._settings['soundDir'] = _soundDir = QStandardPaths.standardLocations(QStandardPaths.MusicLocation)[0]

        return _soundDir

    def setDocumentDir(self, documentDir):
        self._settings['documentDir'] = documentDir

    def getDocumentDir(self):
        try:
            _documentDir = self._settings['documentDir']
        except: # Default Location of text files
            self._settings['documentDir'] = _documentDir = QStandardPaths.standardLocations(QStandardPaths.DocumentsLocation)[0]

        return _documentDir

    def setLastHotButtonFile(self, hotButtonFile):
        self._settings['lastHotButton'] = hotButtonFile

    def getLastHotButtonFile(self):
        try:
            _lastHotButton = self._settings['lastHotButton']
        except:
            # File name of default Hot Button file. This may not exist on install
            self._settings['lastHotButton'] = _lastHotButton = self.getConfigDir()+"/default.hbt"

        _hotButtonFile = QFileInfo(_lastHotButton)
        if _hotButtonFile.exists():

            return _lastHotButton

        return None

    def setMainLocation(self, p):
        self._settings['mainX'] = p.x()
        self._settings['mainY'] = p.y()

    def getMainLocation(self):
        try:
            _mainLocation = QPoint(int(self._settings['mainX']), int(self._settings['mainY']))
        except:
            primaryScreen = QGuiApplication.primaryScreen()
            primaryLocation = primaryScreen.availableGeometry()
            self.setMainLocation(primaryLocation.topLeft())
            _mainLocation = QPoint(int(self._settings['mainX']), int(self._settings['mainY']))

        return _mainLocation

    def setAuxLocation(self, p):
        self._settings['auxX'] = p.x()
        self._settings['auxY'] = p.y()

    def getAuxLocation(self):
        try:
            _auxLocation = QPoint(int(self._settings['auxX']), int(self._settings['auxY']))
        except:
            primaryScreen = QGuiApplication.primaryScreen()
            primaryLocation = primaryScreen.availableGeometry()
            self.setAuxLocation(primaryLocation.topLeft())
            _auxLocation = QPoint(int(self._settings['auxX']), int(self._settings['auxY']))

        return _auxLocation

    def setTouchPortalConnect(self, flag):
        if isinstance(flag, bool):
            self._settings['touchPortalConnect'] = flag #Boolean

    def getTouchPortalConnect(self):
        try:
            _touchPortalConnect = self._settings['touchPortalConnect']
        except:
            self.setTouchPortalConnect(False)
            _touchPortalConnect = self._settings['touchPortalConnect']

        return _touchPortalConnect

    def setGamesFile(self, name):
        self._settings['gamesFile'] = name

    def getGamesFile(self):
        try:
            _promosDir = self._settings['gamesFile']
        except:
            self._settings['gamesFile'] = _promosDir = ""

        return _promosDir
