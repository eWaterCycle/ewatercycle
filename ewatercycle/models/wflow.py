import shutil
import time
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


class Wflow(AbstractModel):
    """eWaterCycle implementation of WFLOW hydrological model.

    Attributes
        bmi (Bmi): GRPC4BMI Basic Modeling Interface object
    """
    available_versions = ("2019.1", "2020.1")
    """Show supported WFlow versions in eWaterCycle"""
    def __init__(self,
                 version: str,
                 parameter_set: PathLike,
                 forcing: Optional[PathLike] = None):
        """Create an instance of the Wflow model class.

        Args:
            version: pick a version from :py:attribute:`Wflow.available_versions`
            parameter_set: directory that contains all parameters including a
                default/template config file which must be called "wflow_sbm.ini".
            forcing: for now it is assumed the forcing is part of the parameter_set.
        """

        super().__init__()
        self.version = version
        self.parameter_set = Path(parameter_set)
        self._set_docker_image()
        self._set_singularity_image()
        self._setup_default_config()

        if forcing is not None:
            raise NotImplementedError(
                "Support for custom forcing is not supported yet. "
                "It is assumed that forcing is part of the parameter_set already"
            )

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
        # TODO need to identify cfg_file. For now assume it is present under
        # default name "wflow_sbm.ini"
        config_file = self.parameter_set / "wflow_sbm.ini"

        cfg = CaseConfigParser()
        cfg.read(config_file)
        self.config = cfg

    def setup(self, **kwargs) -> Tuple[PathLike, PathLike]:  # type: ignore
        """Start the model inside a container and return a valid config file.

        Args:
            **kwargs (optional, dict): any settings in the cfg_file that you
            want to overwrite programmatically. Should be passed as a dict, e.g.
            `run = {"starttime": "1995-01-31 00:00:00 GMT"}` where run is the
            section in which the starttime option may be found. To see all
            available settings see `parameters` property.

        Returns:
            Path to config file and working directory
        """
        # TODO think about what to do when a path to a mapfile is changed.
        self._setup_working_directory()
        config_file = self._update_config(**kwargs)
        self._start_container()

        return config_file, self.work_dir,

    def _setup_working_directory(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        working_directory = CFG["output_dir"] / f'wflow_{timestamp}'

        shutil.copytree(src=self.parameter_set, dst=working_directory)

        self.work_dir = working_directory.resolve()

    def _update_config(self, **kwargs) -> PathLike:
        cfg = self.config

        for section, options in kwargs.items():
            for option, value in options.items():
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
