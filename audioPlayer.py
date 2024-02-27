# This Python file uses the following encoding: utf-8
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

class AudioPlayer():
    def __init__(self):
        self.birdy_uri = 'spotify:artist:2WX2uTcsvV5OnS0inACecP'
        auth_manager = SpotifyClientCredentials(client_id='4d239da5d87b49a89397a83a773a4cea',
                                  client_secret='0815312d8c7d49c9a0eb7220320331be')
        token = auth_manager.get_access_token()
        self.spotify = spotipy.Spotify(auth=token['access_token'])

#        self.auth_manager=SpotifyOAuth(client_id='4d239da5d87b49a89397a83a773a4cea',
#                                client_secret='0815312d8c7d49c9a0eb7220320331be',
#                                redirect_uri='https://www.example.com/',
#                                scope="user-library-read", cache_path=None, username=None, proxies=None, show_dialog=False, requests_session=True, requests_timeout=None, open_browser=True,)
#        self.spotify = spotipy.Spotify(self.auth_manager)

    def getAlbums(self):
        text = ""
        results = self.spotify.artist_albums(self.birdy_uri, album_type='album')
        albums = results['items']
        while results['next']:
            results = self.spotify.next(results)
            albums.extend(results['items'])

        for album in albums:
            text += album['name'] + '\n'

        return text
