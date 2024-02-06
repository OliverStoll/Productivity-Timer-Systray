import yaml
import dotenv
import os
from os import getenv as secret  # noqa: F401

from src._utils.logger import create_logger


log = create_logger("Utils_Common")


ROOT_DIR = os.path.abspath(__file__).split("src")[0]
log.debug(f"Root Directory: {ROOT_DIR}")

ret = dotenv.load_dotenv()  # load .env file to be imported
log.debug(f"At least one env-var in .env: {ret}")
stream = open(f"{ROOT_DIR}config.yml", "r", encoding="utf-8")
config_dict = yaml.safe_load(stream)


def config(key):
    # load the config file as unicode strings
    return config_dict[key]
