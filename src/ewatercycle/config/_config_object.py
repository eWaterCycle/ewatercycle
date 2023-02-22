"""Importable config object."""

import os
import warnings
from io import StringIO
from logging import getLogger
from pathlib import Path
from typing import Dict, Literal, Optional, Set, TextIO, Union

from pydantic import BaseModel, DirectoryPath, FilePath, root_validator
from ruamel.yaml import YAML

from ewatercycle.util import to_absolute_path

logger = getLogger(__name__)


# TODO dont duplicate
# src/ewatercycle/parameter_sets/default.py:ParameterSet
# but fix circular dependency
class ParameterSetConfig(BaseModel):
    # TODO prepend directory with CFG.parameterset_dir
    # and make DirectoryPath type
    directory: Path
    # TODO prepend config with CFG.parameterset_dir and .directory
    # and make FilePath type
    config: Path
    doi: str = "N/A"
    target_model: str = "generic"
    supported_model_versions: Set[str] = set()


class Config(BaseModel):
    """Configuration object.

    Do not instantiate this class directly, but use
    :obj:`ewatercycle.CFG` instead.
    """

    grdc_location: Optional[DirectoryPath]
    container_engine: Literal["docker", "apptainer", "singularity"] = "docker"
    apptainer_dir: Optional[DirectoryPath]
    singularity_dir: Optional[DirectoryPath]
    output_dir: Optional[DirectoryPath]
    parameterset_dir: Optional[DirectoryPath]
    parameter_sets: Dict[str, ParameterSetConfig] = {}
    ewatercycle_config: Optional[FilePath]

    class Config:
        validate_assignment = True

    @root_validator
    def singularity_dir_is_deprecated(cls, values):
        singularity_dir = values.get("singularity_dir")
        apptainer_dir = values.get("apptainer_dir")
        if singularity_dir is not None and apptainer_dir is None:
            file = values.get("ewatercycle_config", "in-memory object")
            warnings.warn(
                f"singularity_dir field has been deprecated please use apptainer_dir in {file}",
                DeprecationWarning,
                stacklevel=2,
            )
            values["apptainer_dir"] = singularity_dir
        return values

    # TODO add more multi property validation like
    # - When container engine is apptainer then apptainer_dir must be set
    # - When parameter_sets is filled then parameterset_dir must be set

    # TODO drop dict methods and use CFG.bla instead of CFG['bla'] everywhere else
    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, key):
        setattr(key, None)

    @classmethod
    def _load_user_config(cls, filename: Union[os.PathLike, str]) -> "Config":
        """Load user configuration from the given file.

        Parameters
        ----------
        filename: pathlike
            Name of the config file, must be yaml format
        """
        mapping = read_config_file(filename)
        return cls(ewatercycle_config=filename, **mapping)

    def load_from_file(self, filename: Union[os.PathLike, str]) -> None:
        """Load user configuration from the given file.

        The config is cleared and updated in-place.
        """
        path = to_absolute_path(str(filename))
        if not path.exists():
            raise FileNotFoundError(f"Cannot find: `{filename}")

        newconfig = Config._load_user_config(path)
        self._overwrite(newconfig)

    def reload(self) -> None:
        """Reload the config file."""
        filename = self.ewatercycle_config
        if filename is None:
            newconfig = self.__class__()
            self._overwrite(newconfig)
        else:
            self.load_from_file(filename)

    def dump_to_yaml(self) -> str:
        """Dumps YAML formatted string of Config object"""
        stream = StringIO()
        self._save_to_stream(stream)
        return stream.getvalue()

    def _save_to_stream(self, stream: TextIO):
        # Exclude own path from dump
        cp = self.dict(exclude={"ewatercycle_config"})

        yaml = YAML(typ="safe")
        yaml.dump(cp, stream)

    def save_to_file(
        self, config_file: Optional[Union[os.PathLike, str]] = None
    ) -> None:
        """Write conf object to a file.

        Args:
            config_file: File to write configuration object to.
                If not given then will try to use `self.ewatercycle_config`
                location and if `self.ewatercycle_config` is not set then will use
                the location in users home directory.
        """
        # Exclude own path from dump
        old_config_file = self.ewatercycle_config

        if config_file is None:
            config_file = (
                USER_HOME_CONFIG if old_config_file is None else old_config_file
            )

        with open(config_file, "w") as f:
            self._save_to_stream(f)

        logger.info(f"Config written to {config_file}")

    def _overwrite(self, other: Config):
        for key in self.dict().keys():
            setattr(self, key, getattr(other, key))


def read_config_file(config_file: Union[os.PathLike, str]) -> dict:
    """Read config user file and store settings in a dictionary."""
    config_file = to_absolute_path(str(config_file))
    if not config_file.exists():
        raise IOError(f"Config file `{config_file}` does not exist.")

    with open(config_file, "r") as file:
        yaml = YAML(typ="safe")
        cfg = yaml.load(file)

    return cfg


def find_user_config(sources: tuple) -> Optional[os.PathLike]:
    """Find user config in list of source directories."""
    for source in sources:
        user_config = source
        if user_config.exists():
            return user_config
    return None


FILENAME = "ewatercycle.yaml"

USER_HOME_CONFIG = (
    Path.home()
    / os.environ.get("XDG_CONFIG_HOME", ".config")
    / "ewatercycle"
    / FILENAME
)
SYSTEM_CONFIG = Path("/etc") / FILENAME

SOURCES = (USER_HOME_CONFIG, SYSTEM_CONFIG)

USER_CONFIG = find_user_config(SOURCES)

CFG_DEFAULT = Config()

if USER_CONFIG:
    CFG = Config._load_user_config(USER_CONFIG)
else:
    CFG = CFG_DEFAULT
