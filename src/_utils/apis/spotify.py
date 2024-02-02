import spotipy
from spotipy.oauth2 import SpotifyOAuth

from src._utils.common import config_dict
from src._utils.common import secret
from src._utils.logger import create_logger


redirect_uri = "http://localhost:7787"


# Set up Spotify client
class SpotifyHandler:
    def __init__(self, device_name: str):
        self.log = create_logger('Spotify')
        self.active = True
        self.device_name = device_name
        self.scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
        self.api = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=secret('SPOTIFY_CLIENT_ID'),
                                                             client_secret=secret('SPOTIFY_CLIENT_SECRET'),
                                                             redirect_uri=redirect_uri,
                                                             scope=self.scope))
        self.device_ids = {device['name']: device['id'] for device in self.api.devices()['devices']}
        self.log.info(f"Found devices: {self.device_ids}")
        assert device_name in self.device_ids.keys(), f"Device '{device_name}' not found"


    def search_track(self, track_name):
        results = self.api.search(q=f'track:{track_name}', type='track')
        items = results['tracks']['items']
        if len(items) > 0:
            return items[0]


    def get_current_playback(self):
        current_playback = self.api.current_user_playing_track()
        if current_playback is None or current_playback['is_playing'] is False:
            return None
        else:
            return current_playback['item']


    def play_track(self, name: str):
        self.log.info(f"Playing track {name} on {self.device_name}")
        search_results = self.api.search(q=f'track:{name}', type='track')['tracks']['items']
        self.api.start_playback(uris=search_results[0]['uri'], device_id=self.device_ids[self.device_name])


    def play_playlist(self, uri: str):
        self.log.info(f"Playing playlist {uri} on {self.device_name}")
        self.api.start_playback(context_uri=uri, device_id=self.device_ids[self.device_name])


    def toggle_playback(self):
        self.log.info("Toggling playback")
        if self.api.current_playback() is None:
            self.api.start_playback()
        else:
            self.api.pause_playback()



if __name__ == '__main__':
    spotify = SpotifyHandler(device_name="PC")
    # spotify.play_track(name=None)
    # spotify.toggle_playback()
    spotify.play_playlist(uri=config_dict['pause_playlist'])
