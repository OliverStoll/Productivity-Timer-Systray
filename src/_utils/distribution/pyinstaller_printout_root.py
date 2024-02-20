import os
import sys

from src._utils.common import ROOT_DIR
from src._utils.logger import create_logger


log = create_logger("Distribution Helper")


if getattr(sys, "frozen", False):
    log.info(f"Root dir: {ROOT_DIR} - Files in root dir: {os.listdir(ROOT_DIR)}")
