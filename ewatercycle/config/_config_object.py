"""Importable config object."""

import os
from io import StringIO
from logging import getLogger
from pathlib import Path
from typing import Union, Optional, TextIO

from ruamel.yaml import YAML

from ._validators import _validators
from ._validated_config import ValidatedConfig

from ewatercycle.util import to_absolute_path

logger = getLogger(__name__)


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
    def _load_default_config(cls, filename: Union[os.PathLike, str]) -> 'Config':
        """Load the default configuration."""
        new = cls()
        mapping = read_config_file(filename)
        new.update(mapping)

        return new

    def load_from_file(self, filename: Union[os.PathLike, str]) -> None:
        """Load user configuration from the given file."""
        path = to_absolute_path(str(filename))
        if not path.exists():
            raise FileNotFoundError(f'Cannot find: `{filename}')

        self.clear()
        self.update(CFG_DEFAULT)
        self.update(Config._load_user_config(path))

    def reload(self) -> None:
        """Reload the config file."""
        filename = self.get('ewatercycle_config', DEFAULT_CONFIG)
        self.load_from_file(filename)

    def dump_to_yaml(self) -> str:
        """Dumps YAML formatted string of Config object
        """
        stream = StringIO()
        self._save_to_stream(stream)
        return stream.getvalue()

    def _save_to_stream(self, stream: TextIO):
        cp = self.copy()

        # Exclude own path from dump
        cp.pop("ewatercycle_config", None)

        cp["grdc_location"] = str(cp["grdc_location"])
        cp["singularity_dir"] = str(cp["singularity_dir"])
        cp["output_dir"] = str(cp["output_dir"])
        cp["parameterset_dir"] = str(cp["parameterset_dir"])

        yaml = YAML(typ='safe')
        yaml.dump(cp, stream)

    def save_to_file(self, config_file: Optional[Union[os.PathLike, str]] = None):
        """Write conf object to a file.

        Args:
            config_file: File to write configuration object to.
                If not given then will try to use `CFG['ewatercycle_config']` location
                and if `CFG['ewatercycle_config']` is not set then will use the location in users home directory.
        """
        # Exclude own path from dump
        old_config_file = self.get("ewatercycle_config", None)

        if config_file is None:
            config_file = USER_HOME_CONFIG if old_config_file is None else old_config_file

        if config_file == DEFAULT_CONFIG:
            raise PermissionError(f'Not allowed to write to {config_file}', config_file)

        with open(config_file, "w") as f:
            self._save_to_stream(f)

        logger.info(f"Config written to {config_file}")

        return config_file


def read_config_file(config_file: Union[os.PathLike, str]) -> dict:
    """Read config user file and store settings in a dictionary."""
    config_file = to_absolute_path(str(config_file))
    if not config_file.exists():
        raise IOError(f'Config file `{config_file}` does not exist.')

    with open(config_file, 'r') as file:
        yaml = YAML(typ='safe')
        cfg = yaml.load(file)

    return cfg


def find_user_config(sources: tuple) -> Optional[os.PathLike]:
    """Find user config in list of source directories."""
    for source in sources:
        user_config = source
        if user_config.exists():
            return user_config
    return None


FILENAME = 'ewatercycle.yaml'

USER_HOME_CONFIG = Path.home() / os.environ.get('XDG_CONFIG_HOME', '.config') / 'ewatercycle' / FILENAME
SYSTEM_CONFIG = Path('/etc') / FILENAME

SOURCES = (
    USER_HOME_CONFIG,
    SYSTEM_CONFIG
)

USER_CONFIG = find_user_config(SOURCES)
DEFAULT_CONFIG = Path(__file__).parent / FILENAME

CFG_DEFAULT = Config._load_default_config(DEFAULT_CONFIG)

if USER_CONFIG:
    CFG = Config._load_user_config(USER_CONFIG)
else:
    CFG = CFG_DEFAULT
