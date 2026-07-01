from json import load, dump
from typing import Any
from pathlib import Path

from hints.constants import CONFIG_PATH, DEFAULT_CONFIG

HintsConfig = dict[str, Any]


def merge_configs(source: HintsConfig, destination: HintsConfig) -> HintsConfig:
    """Deepmerge configs recursively.

    :param source: Source config.
    :param destination: Destination config.
    :return: Destination config.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge_configs(value, node)
        else:
            destination[key] = value

    return destination


def load_config() -> HintsConfig:
    """Load Json config file.

    :return: config object.
    """
    config = {}

    try:
        with open(CONFIG_PATH, encoding="utf-8") as _f:
            config = load(_f)
    except FileNotFoundError:
        pass

    return merge_configs(config, DEFAULT_CONFIG)


def save_default_config() -> bool:
    """Create the default config file if it does not exist.

    :return: if config file was created succesfully.
    """
    file_path = Path(CONFIG_PATH)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, "x", encoding="utf-8") as _f:
            dump(DEFAULT_CONFIG, _f, indent=4)
        return True
    except FileExistsError:
        return False
    except (IOError, OSError):
        return False
