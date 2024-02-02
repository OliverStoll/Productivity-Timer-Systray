import yaml
import dotenv
import os
from os import getenv as secret  # noqa: F401


ROOT_DIR = os.path.abspath(__file__).split("src")[0]

dotenv.load_dotenv()  # load .env file to be imported
stream = open(f"{ROOT_DIR}config.yml", "r", encoding="utf-8")
config_dict = yaml.safe_load(stream)


def config(key):
    # load the config file as unicode strings
    return config_dict[key]
