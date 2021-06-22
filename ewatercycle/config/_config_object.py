"""Importable config object."""

import os
from pathlib import Path
from typing import Union, Optional

from ruamel import yaml

from ._validators import _validators
from ._validated_config import ValidatedConfig


class Config(ValidatedConfig):
    """Configuration object.

    Do not instantiate this class directly, but use
    :obj:`ewatercycle.CFG` instead.
    """

    _validate = _validators

    @classmethod
    def _load_user_config(cls, filename: Union[os.PathLike, str]) -> 'Config':
        """Load user configuration from the given file.

        The config is cleared and updated in-place.

        Parameters
        ----------
        filename: pathlike
            Name of the config file, must be yaml format
        """
        new = cls()

        mapping = read_config_file(filename)
        mapping['ewatercycle_config'] = filename

        new.update(CFG_DEFAULT)
        new.update(mapping)

        return new

    @classmethod
    def _load_default_config(cls, filename: Union[os.PathLike,
                                                  str]) -> 'Config':
        """Load the default configuration."""
        new = cls()

        mapping = read_config_file(filename)
        new.update(mapping)

        return new

    def load_from_file(self, filename: Union[os.PathLike, str]) -> None:
        """Load user configuration from the given file."""
        path = Path(filename).expanduser()
        if not path.exists():
            raise FileNotFoundError(f'Cannot find: `{filename}')

        self.clear()
        self.update(CFG_DEFAULT)
        self.update(Config._load_user_config(path))

    def reload(self) -> None:
        """Reload the config file."""
        filename = self.get('ewatercycle_config', DEFAULT_CONFIG)
        self.load_from_file(filename)


def read_config_file(config_file: Union[os.PathLike, str]) -> dict:
    """Read config user file and store settings in a dictionary."""
    config_file = Path(config_file)
    if not config_file.exists():
        raise IOError(f'Config file `{config_file}` does not exist.')

    with open(config_file, 'r') as file:
        cfg = yaml.safe_load(file)

    return cfg


def find_user_config(sources: tuple, filename: str) -> Optional[os.PathLike]:
    """Find user config in list of source directories."""
    for source in sources:
        user_config = source / filename
        if user_config.exists():
            return user_config
    return None


FILENAME = 'ewatercycle.yaml'

SOURCES = (
    Path.home() / os.environ.get('XDG_CONFIG_HOME', '.config') / '.ewatercycle',
    Path('/etc'),
)

USER_CONFIG = find_user_config(SOURCES, FILENAME)
DEFAULT_CONFIG = Path(__file__).parent / FILENAME

CFG_DEFAULT = Config._load_default_config(DEFAULT_CONFIG)

if USER_CONFIG:
    CFG = Config._load_user_config(USER_CONFIG)
else:
    CFG = CFG_DEFAULT
