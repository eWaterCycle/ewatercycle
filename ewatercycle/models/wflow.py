import shutil
import time
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import CaseConfigParser


@dataclass
class WflowForcing:
    """Forcing data for the Wflow model class.

    Default variable names follow CMOR standards.

    Example:

        To run the example case `wflow_rhine_sbm_nc <https://github.com/openstreams/wflow/tree/master/examples/wflow_rhine_sbm_nc>`_ one would use:

    .. code-block::

        forcing = WflowForcing(
            netcdfinput=Path('inmaps.nc'),
            Precipitation = "/P",
            EvapoTranspiration = "/PET",
            Temperature = "/TEMP",
        )
    """
    netcdfinput: PathLike
    """Input file path."""
    Precipitation: str = "/pr"
    """Variable name of Precipitation data in input file."""
    EvapoTranspiration: str = "/pet"
    """Variable name of EvapoTranspiration data in input file."""
    Temperature: str = "/tas"
    """Variable name of Temperature data in input file."""
    Inflow: Optional[str] = None
    """Variable name of Inflow data in input file."""


@dataclass
class WflowParameterSet:
    """Parameter set for the Wflow model class.

    A valid wflow parameter set consists of a input data files
    and should always include a default configuration file.
    """
    input_data: PathLike
    """Input folder path."""
    default_config: PathLike
    """Path to (default) model configuration file consistent with `input_data`."""


class Wflow(AbstractModel):
    """Create an instance of the Wflow model class.

    Args:
        version: pick a version from :py:attr:`~available_versions`
        parameter_set: instance of :py:class:`~WflowParameterSet`.
        forcing: instance of :py:class:`~WflowForcing` or None.
            If None, it is assumed that forcing is included with the parameter_set.

    Attributes:
        bmi (Bmi): GRPC4BMI Basic Modeling Interface object
    """

    available_versions = ("2019.1", "2020.1")
    """Show supported WFlow versions in eWaterCycle"""
    def __init__(self,
                 version: str,
                 parameter_set: WflowParameterSet,
                 forcing: Optional[WflowForcing] = None):

        super().__init__()
        self.version = version
        self.parameter_set = parameter_set
        self.forcing = forcing

        self._set_docker_image()
        self._set_singularity_image()
        self._setup_default_config()
        self._parse_forcing()

    def _set_docker_image(self):
        images = {
            "2019.1": "ewatercycle/wflow-grpc4bmi:latest",
            "2020.1": "ewatercycle/wflow-grpc4bmi:latest",
        }
        self.docker_image = images[self.version]

    def _set_singularity_image(self):
        images = {
            "2019.1": "ewatercycle-wflow-grpc4bmi.sif",
            "2020.1": "ewatercycle-wflow-grpc4bmi.sif",
        }
        self.singularity_image = CFG['singularity_dir'] / images[self.version]

    def _setup_default_config(self):
        config_file = self.parameter_set.default_config

        cfg = CaseConfigParser()
        cfg.read(config_file)
        self.config = cfg

    def _parse_forcing(self):
        if self.forcing is None:
            return

        cfg = self.config
        forcing = self.forcing
        cfg.set("framework", "netcdfinput", forcing.netcdfinput.name)
        cfg.set("inputmapstacks", "Precipitation", forcing.Precipitation)
        cfg.set("inputmapstacks", "EvapoTranspiration",
                forcing.EvapoTranspiration)
        cfg.set("inputmapstacks", "Temperature", forcing.Temperature)

    def setup(self, **kwargs) -> Tuple[PathLike, PathLike]:  # type: ignore
        """Start the model inside a container and return a valid config file.

        Args:
            **kwargs (optional, dict): see :py:attr:`~parameters` for all
                available settings. It is possible to overwrite paths. If an
                absolute path is given, it will be converted to a path relative
                to the working directory, and the content will be copied there.

        Returns:
            Path to config file and working directory
        """
        self._setup_working_directory()
        config_file = self._update_config(**kwargs)
        self._start_container()

        return config_file, self.work_dir,

    def _setup_working_directory(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        working_directory = CFG["output_dir"] / f'wflow_{timestamp}'
        self.work_dir = working_directory.resolve()

        shutil.copytree(src=self.parameter_set.input_data,
                        dst=working_directory)
        if self.forcing is not None:
            shutil.copy(src=self.forcing.netcdfinput, dst=working_directory)

    def _update_config(self, **kwargs) -> PathLike:
        cfg = self.config

        for section, options in kwargs.items():
            if not cfg.has_section(section):
                cfg.add_section(section)

            for option, value in options.items():
                if Path(value).exists():
                    # Absolute paths must be copied to work dir
                    if Path(value).is_file():
                        shutil.copy(value, self.work_dir)
                    else:
                        shutil.copytree(value, self.work_dir)
                    cfg.set(section, option, Path(value).name)
                else:
                    cfg.set(section, option, value)

        updated_cfg_file = self.work_dir / "wflow_ewatercycle.ini"
        with updated_cfg_file.open("w") as filename:
            cfg.write(filename)

        return updated_cfg_file.resolve()

    def _start_container(self):
        if CFG["container_engine"] == "docker":
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                work_dir=str(self.work_dir),
                timeout=10,
            )
        elif CFG["container_engine"] == "singularity":
            message = f"No singularity image found at {image}"
            assert self.singularity_image.exists(), message

            self.bmi = BmiClientSingularity(
                image=str(self.singularity_image),
                work_dir=str(self.work_dir),
                timeout=10,
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Return the value as xarray object."""
        # Get time information
        time_units = self.bmi.get_time_units()
        grid = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid)

        # Extract the data and store it in an xarray DataArray
        da = xr.DataArray(
            data=np.reshape(self.bmi.get_value(name), shape),
            coords={
                "longitude": self.bmi.get_grid_y(grid),
                "latitude": self.bmi.get_grid_x(grid),
                "time": num2date(self.bmi.get_current_time(), time_units)
            },
            dims=["latitude", "longitude"],
            name=name,
            attrs={"units": self.bmi.get_var_units(name)},
        )

        return da.where(da != -999)

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the configurable parameters for this model."""
        return [(section, dict(self.config[section]))
                for section in self.config.sections()]
