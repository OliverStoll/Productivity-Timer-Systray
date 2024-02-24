import yaml
import dotenv
import os
from os import getenv as secret  # noqa: F401

from src._utils.logger import create_logger


log = create_logger("Utilities")

ROOT_DIR = os.path.abspath(__file__).split("src")[0]
log.debug(f"Root Directory: {ROOT_DIR}")

dotenv_exists = dotenv.load_dotenv()
log.debug(f".env file {'exists' if dotenv_exists else 'DOES NOT exist'}")

stream = open(f"{ROOT_DIR}config.yml", "r", encoding="utf-8")
config = yaml.safe_load(stream)


def config_entry(key: str):
    """load an entry from the config"""
    return config[key]


def load_env_file(path: str):
    """Load the environment variables from the .env file"""
    dotenv.load_dotenv(dotenv_path=path)
