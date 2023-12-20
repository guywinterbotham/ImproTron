# This Python file uses the following encoding: utf-8
from PySide6 import QtCore
from PySide6 import QtWidgets
import spotipy
from spotipy.oauth2 import SpotifyOAuth

class AudioPlayer(QtWidgets.QWidget):
    def __init__(self):
        scope = "user-library-read"

        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

        results = sp.current_user_saved_tracks()
        for idx, item in enumerate(results['items']):
            track = item['track']
            print(idx, track['artists'][0]['name'], " – ", track['name'])
