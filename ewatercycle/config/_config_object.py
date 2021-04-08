"""Importable config object."""

import os
from datetime import datetime
from pathlib import Path
from typing import Union

import yaml

import ewatercycle

from ._config_validators import _validators
from ._validated_config import ValidatedConfig


class Config(ValidatedConfig):
    """Configuration object.

    Do not instantiate this class directly, but use
    :obj:`ewatercycle.CFG` instead.
    """

    _validate = _validators

    @classmethod
    def _load_user_config(cls,
                          filename: Union[os.PathLike, str]=None):
        """Load user configuration from the given file.

        The config is cleared and updated in-place.

        Parameters
        ----------
        filename: pathlike
            Name of the config file, must be yaml format
        """
        new = cls()

        mapping = read_config_file(filename)
        mapping['config_file'] = filename

        new.update(CFG_DEFAULT)
        new.update(mapping)
        new.check_missing()

        return new

    @classmethod
    def _load_default_config(cls, filename: Union[os.PathLike, str]):
        """Load the default configuration."""
        new = cls()

        mapping = read_config_file(filename)
        new.update(mapping)

        return new

    def load_from_file(self, filename: Union[os.PathLike, str]):
        """Load user configuration from the given file."""
        path = Path(filename).expanduser()
        if not path.exists():
            try_path = USER_CONFIG_DIR / filename
            if try_path.exists():
                path = try_path
            else:
                raise FileNotFoundError(f'Cannot find: `{filename}`'
                                        f'locally or in `{try_path}`')

        self.clear()
        self.update(Config._load_user_config(path))

    def reload(self):
        """Reload the config file."""
        filename = self.get('config_file', DEFAULT_CONFIG)
        self.load_from_file(filename)


def read_config_file(config_file: Union[os.PathLike, str]):
    """Read config user file and store settings in a dictionary."""
    config_file = Path(config_file)
    if not config_file.exists():
        raise IOError(f'Config file `{config_file}` does not exist.')

    with open(config_file, 'r') as file:
        cfg = yaml.safe_load(file)

    return cfg


def find_user_config(sources: tuple, filename: str):
    """Find user config in list of source directories."""
    for source in sources:
        user_config = source / filename
        if user_config.exists():
            return user_config


FILENAME = 'ewatercycle.yaml'

SOURCES = (
    Path.home() / '.ewatercycle',
    Path('/etc'),
)

USER_CONFIG = find_user_config(SOURCES, FILENAME)
DEFAULT_CONFIG = Path(ewatercycle.__file__).parents[1] / FILENAME

print(DEFAULT_CONFIG)

# initialize placeholders
CFG_DEFAULT = Config._load_default_config(DEFAULT_CONFIG)
if USER_CONFIG:
    CFG = Config._load_user_config(USER_CONFIG)
else:
    CFG = CFG_DEFAULT
