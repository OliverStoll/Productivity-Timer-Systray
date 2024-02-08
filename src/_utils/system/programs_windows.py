import pygetwindow as gw
import subprocess
from pywinauto import Desktop
import psutil


def close_window_by_process(process_name):
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
    def __init__(self):
        self.exclude_list = ["Program Manager", "Windows Input Experience"]
        self.minimized_windows = []

    def minimize_open_windows(self):
        all_windows = gw.getWindowsWithTitle("")
        self.minimized_windows = []
        for win in all_windows:
            if not win.isMinimized and win.title and win.title not in self.exclude_list:
                win.minimize()
                self.minimized_windows.append(win)

    def restore_windows(self):
        for win in self.minimized_windows:
            win.restore()
