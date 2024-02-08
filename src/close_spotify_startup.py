from time import sleep

from src._utils.system.programs_windows import close_window_by_process


def await_and_close_spotify():
    while not close_window_by_process("Spotify.exe"):
        sleep(0.1)


if __name__ == "__main__":
    await_and_close_spotify()
