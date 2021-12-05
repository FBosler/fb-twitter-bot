import os
from yaml import load, CLoader as Loader
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'production.yml')

    try:
        with open(config_path) as config_file:
            return load(config_file, Loader)
    except FileNotFoundError:
        logger.error(f'You probably forgot to create a production.yml, as we could not find {config_path}')
        raise


def get_post_data():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'post_data.yml')
    with open(data_path) as config_file:
        return load(config_file, Loader)