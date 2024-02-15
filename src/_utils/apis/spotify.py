import spotipy
from spotipy.oauth2 import SpotifyOAuth

from src._utils.logger import create_logger


# Set up Spotify client
class SpotifyHandler:
    def __init__(
        self, device_name: str, client_id: str, client_secret: str, redirect_uri: str, scope: str
    ):
        """Spotify client to interact with the Spotify API.

        Takes a specific device name to play music on."""
        self.log = create_logger("Spotify")
        self.active = True
        self.device_name = device_name
        self.api = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scope,
            ),
            retries=0,
            requests_timeout=1,
        )
        self.device_ids = {device["name"]: device["id"] for device in self.api.devices()["devices"]}
        self.log.info(f"Initialised and found devices: {self.device_ids.keys()}")
        assert device_name in self.device_ids.keys(), f"Device '{device_name}' not found"

    def search_track(self, track_name):
        """Search for a track via its name and return the first result"""
        results = self.api.search(q=f"track:{track_name}", type="track")
        items = results["tracks"]["items"]
        if len(items) > 0:
            return items[0]

    def get_current_playback(self):
        """Get the current track item that is playing, or None if nothing is playing"""
        current_playback = self.api.current_user_playing_track()
        if current_playback is None or current_playback["is_playing"] is False:
            return None
        else:
            return current_playback["item"]

    def play_track(self, track_name: str):
        """Play a track using its name, by searching it and playing it"""
        self.log.debug(f"Playing track {track_name} on {self.device_name}")
        search_result = self.search_track(track_name)
        self.api.start_playback(
            uris=search_result["uri"], device_id=self.device_ids[self.device_name]
        )

    def play_playlist(self, playlist_uri: str):
        """Play a playlist using its uri"""
        self.log.debug(f"Playing playlist {playlist_uri} on {self.device_name}")
        try:
            self.api.start_playback(
                context_uri=playlist_uri, device_id=self.device_ids[self.device_name]
            )
        except Exception as e:
            self.log.error(f"Failed to play playlist: {e}")

    def toggle_playback(self):
        """Toggle playback (might behave unexpectedly if nothing is playing)"""
        self.log.debug("Toggling playback")
        if self.api.current_playback() is None:
            self.api.start_playback()
        else:
            self.api.pause_playback()


if __name__ == "__main__":
    pass
    # spotify = SpotifyHandler(device_name="PC", )
    # spotify.play_track(name=None)
    # spotify.toggle_playback()
    # spotify.play_playlist(playlist_uri=config_dict["pause_playlist"])
