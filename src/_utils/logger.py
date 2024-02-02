import logging
import sys
import os

# Set up logging, locally and in the cloud
is_cloud = os.getenv("IS_CLOUD", False)

if is_cloud:
    import google.cloud.logging

    client = google.cloud.logging.Client()
    client.get_default_handler()
    client.setup_logging()
    format_str = "%(levelname)s | %(name)s   -   %(message)s"
else:
    format_str = "[%(asctime)s]  %(levelname)s | %(name)s   -   %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"


def create_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(format_str, datefmt=date_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
