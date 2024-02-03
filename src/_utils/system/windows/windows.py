import pygetwindow as gw


EXCLUDE_WINDOWS_LIST = ["Program Manager", "Windows Input Experience"]


class WindowHandler:
    def __init__(self):
        self.exclude_list = EXCLUDE_WINDOWS_LIST
        self.minimized_windows = []

    def hide_windows(self):
        all_windows = gw.getWindowsWithTitle("")
        self.minimized_windows = []
        for win in all_windows:
            if not win.isMinimized and win.title and win.title not in self.exclude_list:
                win.minimize()
                self.minimized_windows.append(win)

    def restore_windows(self):
        for win in self.minimized_windows:
            win.restore()
