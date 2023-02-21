"""Importable config object."""

import os
from io import StringIO
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Set, TextIO, Union

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

    @root_validator
    def _deprecate_singularity_dir(cls, values):
        singularity_dir = values.get("singularity_dir")
        apptainer_dir = values.get("apptainer_dir")
        if singularity_dir is not None and apptainer_dir is None:
            logger.warning(
                "singularity_dir has been deprecated please use apptainer_dir"
            )
            values["apptainer_dir"] = singularity_dir
        return values

    # TODO add more cross property validation like
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

        The config is cleared and updated in-place.

        Parameters
        ----------
        filename: pathlike
            Name of the config file, must be yaml format
        """
        new: Dict[str, Any] = {}
        mapping = read_config_file(filename)
        mapping["ewatercycle_config"] = filename

        new.update(CFG_DEFAULT)
        new.update(mapping)

        return cls(**new)

    @classmethod
    def _load_default_config(cls, filename: Union[os.PathLike, str]) -> "Config":
        """Load the default configuration."""
        mapping = read_config_file(filename)

        return cls(**mapping)

    def load_from_file(self, filename: Union[os.PathLike, str]) -> None:
        """Load user configuration from the given file."""
        path = to_absolute_path(str(filename))
        if not path.exists():
            raise FileNotFoundError(f"Cannot find: `{filename}")

        newconfig = Config._load_user_config(path)
        # TODO assign newconfig props to self

    def reload(self) -> None:
        """Reload the config file."""
        filename = self.ewatercycle_config
        if filename is None:
            newconfig = self.__class__()
            # TODO assign newconfig props to self
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

    def save_to_file(self, config_file: Optional[Union[os.PathLike, str]] = None):
        """Write conf object to a file.

        Args:
            config_file: File to write configuration object to.
                If not given then will try to use `CFG['ewatercycle_config']`
                location and if `CFG['ewatercycle_config']` is not set then will use
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

        return config_file


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
