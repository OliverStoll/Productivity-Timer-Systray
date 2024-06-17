from datetime import datetime
import pygetwindow as gw
import subprocess
import psutil
from time import sleep
from src._utils.logger import create_logger


def close_window_by_process(process_name):
    from pywinauto import Desktop

    windows = Desktop(backend="uia").windows()
    for win in windows:
        pid = win.process_id()
        win_process_name = psutil.Process(pid).name()
        if win_process_name == process_name:
            win.close()
            return True
    return False


def is_program_running(program_name):
    """Check if the program is currently running without showing a console window."""
    try:
        # Set up the startup information for the subprocess
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        # Execute 'tasklist' with the configured startupinfo to hide the console window
        processes = subprocess.check_output(["tasklist"], startupinfo=startupinfo, text=True)
        return program_name in processes
    except subprocess.CalledProcessError:
        return False


def start_program(program_path):
    """Starts the program."""
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen(program_path, startupinfo=startupinfo)
        print(f"Program started: {program_path}")
    except Exception as e:
        print(f"Failed to start the program: {e}")


class WindowHandler:
    def __init__(self, ignore_windows=None):
        self.log = create_logger("Window Handler")
        self.ignore_windows = (
            ["", "Program Manager", "Windows Input Experience", "Settings"]
            if ignore_windows is None
            else ignore_windows
        )
        self.minimized_windows = []

    def get_user_windows(self):
        """Get all open windows"""
        user_windows = []
        windows = gw.getAllWindows()
        for window in windows:
            if window.title not in self.ignore_windows:
                user_windows.append(window)
        return user_windows

    def minimize_open_windows(self):
        all_windows = self.get_user_windows()
        self.minimized_windows = []
        for win in all_windows:
            if win.title not in self.ignore_windows and win.isMinimized is not True:
                window_info = {
                    "window": win,
                    "is_maximised": win.isMaximized,
                    "is_focused": win.isActive,
                }
                self.minimized_windows.append(window_info)
                win.minimize()
                self.log.debug(f"Minimized window: {window_info}")

    def restore_windows(self):
        """Restore the minimized windows, with the focused window restored last"""
        focused_windows = [
            win_info for win_info in self.minimized_windows if win_info["is_focused"]
        ]
        non_focused_windows = [
            win_info for win_info in self.minimized_windows if not win_info["is_focused"]
        ]
        for win_info in non_focused_windows:
            self.log.debug(f"Restoring non-focused window: {win_info['window'].title}")
            win_info["window"].restore()
        for win_info in focused_windows:
            self.log.debug(f"Restoring focused window: {win_info['window'].title}")
            win_info["window"].restore()


if __name__ == "__main__":
    handler = WindowHandler()
    handler.minimize_open_windows()
    print("Windows minimized", handler.minimized_windows)
    sleep(1)
    handler.restore_windows()
