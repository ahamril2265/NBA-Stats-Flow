import yaml
import os
from typing import Dict

from src.common.logger import get_logger

logger = get_logger("CONFIG_LOADER")

BASE_CONFIG_PATH = "config/base.yaml"
SCHEMA_CONFIG_PATH = "config/schema_v1.yaml"


def load_yaml(path: str) -> Dict:
    """
    Load a YAML file and return it as a dictionary.
    Fail fast if the file does not exist or is invalid.
    """
    if not os.path.exists(path):
        logger.error(f"Config file not found: {path}")
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file: {path}")
        raise e


def load_config() -> Dict:
    """
    Load base config and schema config together.

    Returns:
        dict: merged configuration dictionary
    """
    logger.info("START | Loading configuration")

    base_config = load_yaml(BASE_CONFIG_PATH)
    schema_config = load_yaml(SCHEMA_CONFIG_PATH)

    config = {
        "base": base_config,
        "schema": schema_config
    }

    logger.info("END | Configuration loaded successfully")
    return config
