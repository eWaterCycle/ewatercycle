import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple, Union

import numpy as np
import xarray as xr
from cftime import num2date
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing.wflow import WflowForcing
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import CaseConfigParser
from ewatercycle.util import get_time


@dataclass
class WflowParameterSet:
    """Parameter set for the Wflow model class.

    A valid wflow parameter set consists of a input data files
    and should always include a default configuration file.
    """
    input_data: Union[str, PathLike]
    """Input folder path."""
    default_config: Union[str, PathLike]
    """Path to (default) model configuration file consistent with `input_data`."""
    def __setattr__(self, name: str, value: Union[str, PathLike]):
        self.__dict__[name] = Path(value).expanduser().resolve()

    def __str__(self):
        """Nice formatting of parameter set."""
        return "\n".join([
            "Wflow parameterset",
            "------------------",
            f"Directory: {self.input_data}",
            f"Default configuration file: {self.default_config}",
        ])


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

    available_versions = ("2020.1.1")
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
        self._setup_default_config()

    def _set_docker_image(self):
        images = {
            # "2019.1": "ewatercycle/wflow-grpc4bmi:2019.1", # no good ini file
            "2020.1.1": "ewatercycle/wflow-grpc4bmi:2020.1.1",
        }
        self.docker_image = images[self.version]

    def _setup_default_config(self):
        config_file = self.parameter_set.default_config
        forcing = self.forcing

        cfg = CaseConfigParser()
        cfg.read(config_file)

        cfg.set("framework", "netcdfinput", Path(forcing.netcdfinput).name)
        cfg.set("inputmapstacks", "Precipitation", forcing.Precipitation)
        cfg.set("inputmapstacks", "EvapoTranspiration",
                forcing.EvapoTranspiration)
        cfg.set("inputmapstacks", "Temperature", forcing.Temperature)
        cfg.set("run", "starttime", _iso_to_wflow(forcing.start_time))
        cfg.set("run", "endtime", _iso_to_wflow(forcing.end_time))

        self.config = cfg

    def setup(self, **kwargs) -> Tuple[PathLike, PathLike]:  # type: ignore
        """Start the model inside a container and return a valid config file.

        Args:
            **kwargs (optional, dict): see :py:attr:`~parameters` for all
                configurable model parameters.

        Returns:
            Path to config file and working directory
        """
        self._setup_working_directory()
        cfg = self.config

        if "start_time" in kwargs:
            cfg.set("run", "starttime", _iso_to_wflow(kwargs["start_time"]))
        if "end_time" in kwargs:
            cfg.set("run", "endtime", _iso_to_wflow(kwargs["end_time"]))

        updated_cfg_file = self.work_dir / "wflow_ewatercycle.ini"
        with updated_cfg_file.open("w") as filename:
            cfg.write(filename)

        self._start_container()

        return updated_cfg_file.expanduser().resolve(), self.work_dir,

    def _setup_working_directory(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        working_directory = CFG["output_dir"] / f'wflow_{timestamp}'
        self.work_dir = working_directory.resolve()

        shutil.copytree(src=self.parameter_set.input_data,
                        dst=working_directory)
        shutil.copy(src=self.forcing.netcdfinput, dst=working_directory)

    def _start_container(self):
        if CFG["container_engine"] == "docker":
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                work_dir=str(self.work_dir),
                timeout=10,
            )
        elif CFG["container_engine"] == "singularity":
            try:
                self.bmi = BmiClientSingularity(
                    image=f"docker://{self.docker_image}",
                    work_dir=str(self.work_dir),
                    timeout=15,
                )
            except FutureTimeoutError:
                raise ValueError(
                    "Couldn't spawn the singularity container within allocated"
                    " time limit (15 seconds). You may try building it with "
                    f"`!singularity run docker://{self.docker_image}` and try "
                    "again. Please also inform the system administrator that "
                    "the singularity image was missing.")
        else:
            raise ValueError(
                f"Unknown container technology: {CFG['container_engine']}")

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
        # An opiniated list of configurable parameters.
        cfg = self.config
        return [
            ("start_time", _wflow_to_iso(cfg.get('run', 'starttime'))),
            ("end_time", _wflow_to_iso(cfg.get('run', 'endtime'))),
        ]


def _wflow_to_iso(t):
    dt = datetime.fromisoformat(t)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_to_wflow(t):
    dt = get_time(t)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
