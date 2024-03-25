"""Config

Configuration of eWaterCycle is done via the
:py:class:`~eWaterCycle.config.Configuration` object. The global configuration can be
imported from the :py:mod:`eWaterCycle` module as :py:data:`~ewatercycle.CFG`:

.. code-block:: python

    >>> from ewatercycle import CFG
    >>> CFG
    Configuration(
        grdc_location=PosixPath('.'),
        container_engine='docker',
        apptainer_dir=PosixPath('.'),
        singularity_dir=None,
        output_dir=PosixPath('.'),
        parameterset_dir=PosixPath('.'),
        parameter_sets={},
        ewatercycle_config=None
    )

By default all values have usable values.

:py:data:`~ewatercycle.CFG` is a `Pydantic model <https://docs.pydantic.dev/usage/models/>`_.
This means that values can be updated like this:

.. code-block:: python

    >>> CFG.output_dir = '~/output'
    >>> CFG.output_dir
    PosixPath('/home/user/output')

Notice that :py:data:`~ewatercycle.CFG` automatically converts the path to an
instance of ``pathlib.Path`` and expands the home directory. All values entered
into the config are validated to prevent mistakes, for example, it will warn you
if you make a typo in the key:

.. code-block:: python

    >>> CFG.output_directory = '/output'
    ValidationError: 1 validation error for Configuration
    output_directory
        extra fields not permitted (type=value_error.extra)


Or, if the value entered cannot be converted to the expected type:

.. code-block:: python

    >>> CFG.output_dir = 123
    ValidationError: 1 validation error for Configuration
    output_dir
        value is not a valid path (type=type_error.path)


By default, the config is loaded from the default location (i.e.
``~/.config/ewatercycle/ewatercycle.yaml``). If it does not exist, it falls back
to the default values. to load a different file:

.. code-block:: python

    >>> CFG.load_from_file('~/my-config.yml')

Or to reload the current config:

.. code-block:: python

    >>> CFG.reload()

.. data:: CFG

eWaterCycle configuration object.

The configuration is loaded from:

 1. ``$XDG_CONFIG_HOME/ewatercycle/ewatercycle.yaml``
 2. ``~/.config/ewatercycle/ewatercycle.yaml``
 3. ``/etc/ewatercycle.yaml``
 4. Fall back to empty configuration

The ``ewatercycle.yaml`` is formatted in YAML and could for example look like:

.. code-block:: yaml

    grdc_location: /data/grdc
    container_engine: apptainer
    apptainer_dir: /data/apptainer-images
    output_dir: /scratch
    # Filled apptainer_dir with
    # cd /data/apptainer-images
    # apptainer pull docker://ewatercycle/wflow-grpc4bmi:2020.1.1
"""

import os
import warnings
from io import StringIO
from logging import getLogger
from pathlib import Path
from typing import Annotated, Any, Dict, Literal, Optional, TextIO, Tuple, Union

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    DirectoryPath,
    FilePath,
    ValidationError,
    model_validator,
)
from ruamel.yaml import YAML

from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.util import to_absolute_path

logger = getLogger(__name__)


def _expand_path(v):
    if isinstance(v, str):
        return Path(v).expanduser()
    if isinstance(v, Path):
        return v.expanduser()
    # paths in parameter_sets items is already expanded by ps.make_absolute()
    return v


ContainerEngine = Literal["docker", "apptainer", "singularity"]
ExpandedDirectoryPath = Annotated[DirectoryPath, BeforeValidator(_expand_path)]
ExpandedFilePath = Annotated[FilePath, BeforeValidator(_expand_path)]


class Configuration(BaseModel):
    """Configuration object.

    Do not instantiate this class directly, but use
    :obj:`ewatercycle.CFG` instead.
    """

    grdc_location: ExpandedDirectoryPath = Path(".")
    """Where can GRDC observation files (<station identifier>_Q_Day.Cmd.txt) be found."""
    container_engine: ContainerEngine = "docker"
    """Which container engine is used to run the hydrological models."""
    apptainer_dir: ExpandedDirectoryPath = Path(".")
    """Where the apptainer images files (.sif) be found."""
    singularity_dir: Optional[DirectoryPath] = None
    """Where the singularity images files (.sif) be found.

    DEPRECATED, use apptainer_dir."""
    output_dir: ExpandedDirectoryPath = Path(".")
    """Directory in which output of model runs is stored.

    Each model run will generate a sub directory inside output_dir"""
    parameterset_dir: ExpandedDirectoryPath = Path(".")
    """Root directory for all parameter sets."""
    parameter_sets: Dict[str, ParameterSet] = {}
    """Dictionary of parameter sets.

    Data source for :py:func:`ewatercycle.parameter_sets.available_parameter_sets` and
    :py:func:`ewatercycle.parameter_sets.get_parameter_set` methods.
    """
    ewatercycle_config: Optional[ExpandedFilePath] = None
    """Where is the configuration saved or loaded from.

    If None then the configuration was not loaded from a file."""
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def singularity_dir_is_deprecated(cls, data: Any) -> Any:
        if data.get("singularity_dir", None) is not None:
            file = data.get("ewatercycle_config", "in-memory object")
            warnings.warn(
                "singularity_dir field has been deprecated. "
                f"Please use apptainer_dir in ewatercycle config ({file})",
                DeprecationWarning,
                stacklevel=2,
            )
            data["apptainer_dir"] = data["singularity_dir"]
            data["singularity_dir"] = None
        return data

    @model_validator(mode="after")
    def _localize_parametersets(self):
        """Make parameter set directories relative to root."""
        parameter_sets = self.parameter_sets
        parameterset_dir = self.parameterset_dir
        for ps_name, ps in parameter_sets.items():
            if isinstance(ps, dict):
                # TODO is this explicit parsing necessary?
                ps = ParameterSet(**ps)
            if isinstance(ps, ParameterSet) and parameterset_dir:
                ps.name = ps_name
                ps.make_absolute(parameterset_dir)

                if not ps.directory.exists():
                    warnings.warn(
                        f"Parameter set {ps.name} loaded in config but "
                        f"{ps.directory} does not seem to exist."
                    )
                if not ps.config.exists():
                    warnings.warn(
                        f"Parameter set {ps.name} loaded in config but "
                        f"{ps.config} does not seem to exist."
                    )
        return self

    @classmethod
    def _load_user_config(cls, filename: os.PathLike[str] | str) -> "Configuration":
        """Load user configuration from the given file.

        Parameters
        ----------
        filename: pathlike
            Name of the config file, must be yaml format
        """
        mapping = _read_config_file(filename)
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

    def load_from_file(self, filename: os.PathLike[str] | str) -> None:
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
            self.reset()
        else:
            self.load_from_file(filename)

    def reset(self) -> None:
        """Reset to empty configuration."""
        newconfig = Configuration()
        self.overwrite(newconfig)

    def dump_to_yaml(self) -> str:
        """Dumps YAML formatted string of Config object"""
        stream = StringIO()
        self._save_to_stream(stream)
        return stream.getvalue()

    def _save_to_stream(self, stream: TextIO):
        yaml = YAML(typ="safe")
        # TODO make paths in parameter_sets relative again
        # TODO use self.model_dump() instead of ugly py>json>py>yaml chain,
        # tried but returns PosixPath values, which YAML library can not represent
        json_string = self.model_dump_json(
            exclude={"ewatercycle_config"}, exclude_none=True
        )
        yaml_object = yaml.load(json_string)
        yaml.dump(yaml_object, stream)

    def save_to_file(self, config_file: os.PathLike[str] | str | None = None) -> None:
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
        for key in self.model_dump().keys():
            setattr(self, key, getattr(other, key))


def _read_config_file(config_file: Union[os.PathLike, str]) -> dict:
    """Read config user file and store settings in a dictionary."""
    config_file = to_absolute_path(str(config_file))
    if not config_file.exists():
        raise IOError(f"Config file `{config_file}` does not exist.")

    with open(config_file, "r") as file:
        yaml = YAML(typ="safe")
        cfg = yaml.load(file)

    return cfg


def _find_user_config(sources: Tuple[Path, ...]) -> Optional[os.PathLike]:
    """Find user config in list of source directories."""
    for source in sources:
        user_config = source
        if user_config.exists():
            return user_config
    return None


_FILENAME = "ewatercycle.yaml"

USER_HOME_CONFIG = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    / "ewatercycle"
    / _FILENAME
)
SYSTEM_CONFIG = Path("/etc") / _FILENAME

_SOURCES = (USER_HOME_CONFIG, SYSTEM_CONFIG)

USER_CONFIG = _find_user_config(_SOURCES)

CFG = Configuration()
if USER_CONFIG:
    CFG = Configuration._load_user_config(USER_CONFIG)
