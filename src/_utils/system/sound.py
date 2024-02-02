import os
import threading
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "TRUE"
import pygame

from src._utils.common import ROOT_DIR


def play_sound(file_path='res/start-sound.mp3', volume=0.5):
    def play_sound_thread_fn():
        pygame.mixer.init()
        pygame.mixer.music.load(ROOT_DIR + file_path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue

    # start the thread
    threading.Thread(target=play_sound_thread_fn).start()


if __name__ == '__main__':
    play_sound('res/start-sound.mp3')