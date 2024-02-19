import os

from src._utils.common import ROOT_DIR


def print_root_files():
    print(f"Root dir: {ROOT_DIR}")
    for file in os.listdir(ROOT_DIR):
        print(file)

    return [file in os.listdir(ROOT_DIR)]
