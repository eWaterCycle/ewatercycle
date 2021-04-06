"""Importable config object."""

import os
from datetime import datetime
from pathlib import Path
from typing import Union

import yaml

import esmvalcore

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
                          filename: Union[os.PathLike, str]):
        """Load user configuration from the given file.

        The config is cleared and updated in-place.

        Parameters
        ----------
        filename: pathlike
            Name of the config file, must be yaml format
        """
        new = cls()

        try:
            mapping = _read_config_file(filename)
            mapping['config_file'] = filename
        except IOError:
            if raise_exception:
                raise
            mapping = {}

        new.update(CFG_DEFAULT)
        new.update(mapping)
        new.check_missing()

        return new

    @classmethod
    def _load_default_config(cls, filename: Union[os.PathLike, str]):
        """Load the default configuration."""
        new = cls()

        mapping = _read_config_file(filename)
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


def _read_config_file(config_file):
    """Read config user file and store settings in a dictionary."""
    config_file = Path(config_file)
    if not config_file.exists():
        raise IOError(f'Config file `{config_file}` does not exist.')

    with open(config_file, 'r') as file:
        cfg = yaml.safe_load(file)

    return cfg


FILENAME = 'ewatercycle.yaml'

# ewatercycle / FILENAME
# /etc/ FILENAME
# /home/.ewatercycle / FILENAME

DEFAULT_CONFIG_DIR = Path(ewatercycle.__file__).parent
DEFAULT_CONFIG = DEFAULT_CONFIG_DIR / 'defaults.yml'

USER_CONFIG_DIR = Path.home() / '.ewatercycle' / 'ewatercycle.yaml'
USER_CONFIG = USER_CONFIG_DIR / 'ewatercycle.yaml'

# initialize placeholders
CFG = Config._load_user_config(USER_CONFIG, raise_exception=False)
