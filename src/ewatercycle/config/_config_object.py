"""Importable config object."""

import os
import warnings
from io import StringIO
from logging import getLogger
from pathlib import Path
from typing import Dict, Literal, Optional, Set, TextIO, Union

from pydantic import BaseModel, DirectoryPath, FilePath, ValidationError, root_validator
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


ContainerEngine = Literal["docker", "apptainer", "singularity"]


class Configuration(BaseModel):
    """Configuration object.

    Do not instantiate this class directly, but use
    :obj:`ewatercycle.CFG` instead.
    """

    grdc_location: DirectoryPath = Path(".")
    """Where can GRDC observation files (<station identifier>_Q_Day.Cmd.txt) be found."""
    container_engine: ContainerEngine = "docker"
    """Which container engine is used to run the hydrological models."""
    apptainer_dir: DirectoryPath = Path(".")
    """Where the apptainer images files (*.sif) be found."""
    singularity_dir: Optional[DirectoryPath]
    """Where the singularity images files (*.sif) be found. DEPRECATED, use apptainer_dir."""
    output_dir: DirectoryPath = Path(".")
    """Directory in which output of model runs is stored.

    Each model run will generate a sub directory inside output_dir"""
    parameterset_dir: DirectoryPath = Path(".")
    """Root directory for all parameter sets."""
    parameter_sets: Dict[str, ParameterSetConfig] = {}
    """Dictionary of parameter sets.

    Data source for :py:func:`ewatercycle.parameter_sets.available_parameter_sets` and :py:func:`ewatercycle.parameter_sets.get_parameter_set` methods.
    """
    ewatercycle_config: Optional[FilePath]
    """Where is the configuration saved or loaded from."""

    class Config:
        validate_assignment = True

    @root_validator
    def singularity_dir_is_deprecated(cls, values):
        singularity_dir = values.get("singularity_dir")
        if singularity_dir is not None:
            file = values.get("ewatercycle_config", "in-memory object")
            warnings.warn(
                f"singularity_dir field has been deprecated please use apptainer_dir in {file}",
                DeprecationWarning,
                stacklevel=2,
            )
            values["apptainer_dir"] = singularity_dir
            values["singularity_dir"] = None
        return values

    @classmethod
    def _load_user_config(cls, filename: Union[os.PathLike, str]) -> "Configuration":
        """Load user configuration from the given file.

        Parameters
        ----------
        filename: pathlike
            Name of the config file, must be yaml format
        """
        mapping = read_config_file(filename)
        try:
            return Configuration(ewatercycle_config=filename, **mapping)
        except ValidationError as e:
            # Append filename to error locs
            for error in e.errors():
                locs = []
                for loc in error["loc"]:
                    loc = f"{filename}:{loc}"
                    locs.append(loc)
                error["loc"] = tuple(locs)
            raise

    def load_from_file(self, filename: Union[os.PathLike, str]) -> None:
        """Load user configuration from the given file.

        The config is cleared and updated in-place.
        """
        path = to_absolute_path(str(filename))
        if not path.exists():
            raise FileNotFoundError(f"Cannot find: `{filename}")

        newconfig = Configuration._load_user_config(path)
        self.overwrite(newconfig)

    def reload(self) -> None:
        """Reload the config file."""
        filename = self.ewatercycle_config
        if filename is None:
            newconfig = Configuration()
            self.overwrite(newconfig)
        else:
            self.load_from_file(filename)

    def dump_to_yaml(self) -> str:
        """Dumps YAML formatted string of Config object"""
        stream = StringIO()
        self._save_to_stream(stream)
        return stream.getvalue()

    def _save_to_stream(self, stream: TextIO):
        yaml = YAML(typ="safe")
        # TODO use self.dict() instead of ugly py>json>py>yaml chain,
        # tried but returns PosixPath values, which YAML library can not represent
        json_string = self.json(exclude={"ewatercycle_config"}, exclude_none=True)
        yaml_object = yaml.load(json_string)
        yaml.dump(yaml_object, stream)

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

    def overwrite(self, other: "Configuration"):
        """Overwrite own fields by the ones of the other configuration object.

        Args:
            other: The other configuration object.
        """
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

CFG = Configuration()
if USER_CONFIG:
    CFG = Configuration._load_user_config(USER_CONFIG)
