import os
import sys

try:
    os.chdir(sys._MEIPASS)  # type: ignore
except AttributeError:
    pass
