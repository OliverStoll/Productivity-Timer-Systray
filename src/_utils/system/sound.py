import os
import threading
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "TRUE"
import pygame

from src._utils.common import ROOT_DIR


class SoundHandler:
    def __init__(self, default_volume):
        self.default_volume = default_volume

    def play_sound(self, file_path, volume=None):
        """Play sound in a separate thread"""
        thread = threading.Thread(target=self._play_sound, args=(file_path, volume))
        thread.start()

    def _play_sound(self, file_path, volume=None):
        volume = volume or self.default_volume
        pygame.mixer.init()
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.load(filename=file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue
        pygame.mixer.quit()




if __name__ == '__main__':
    sound_handler = SoundHandler(default_volume=1)
    sound_handler.play_sound(f'{ROOT_DIR}res/start-sound.mp3')
