import shutil
import time
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple, Union

from dataclasses import dataclass
import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import CaseConfigParser


@dataclass
class PCRGlobWBParameterSet:
    """Parameter set for the PCRGlobWB model class.

    A valid pcrglobwb parameter set consists of a folder with input data files
    and should always include a default configuration file.
    """
    input_dir: Union[str, PathLike]
    """Input folder path."""
    default_config: Union[str, PathLike]
    """Path to (default) model configuration file consistent with `input_data`."""

    def __setattr__(self, name: str, value: Union[str, PathLike]):
        self.__dict__[name] = Path(value).expanduser().resolve()


class PCRGlobWB(AbstractModel):
    """eWaterCycle implementation of PCRGlobWB hydrological model.

    Args:

        version: pick a version from :py:attr:`~available_versions`
        parameter_set: instance of :py:class:`~PCRGlobWBParameterSet`.

    Attributes:

        bmi (Bmi): GRPC4BMI Basic Modeling Interface object
    """
    available_versions = ('setters')
    # TODO add available_versions
    def __init__(self, version: str, parameter_set: PCRGlobWBParameterSet):
        super().__init__()

        self.version=version
        self.parameter_set = parameter_set
        self.additional_input_dirs = []

        self._set_docker_image()
        self._set_singularity_image()

        self._setup_work_dir()
        self._setup_default_config()

    def _set_docker_image(self):
        images = {
            "setters": "ewatercycle/pcrg-grpc4bmi:setters",
        }
        self.docker_image = images[self.version]

    def _set_singularity_image(self):
        # TODO auto detect sif file based on docker image and singularity dir.
        images = {
            "setters": "ewatercycle/pcrg-grpc4bmi:setters",
        }
        self.singularity_image = CFG['singularity_dir'] / images[self.version]

    def _setup_work_dir(self):
        # Must exist before setting up default config
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        work_dir = Path(CFG["output_dir"]) / f'pcrglobwb_{timestamp}'
        work_dir.mkdir()
        self.work_dir = work_dir.expanduser().resolve()

    def _setup_default_config(self):
        config_file = self.parameter_set.default_config
        input_dir = self.parameter_set.input_dir

        cfg = CaseConfigParser()
        cfg.read(config_file)
        cfg.set('globalOptions', 'inputDir', str(input_dir))
        cfg.set('globalOptions', 'outputDir', str(self.work_dir))

        self.config = cfg

    def setup(  # type: ignore
            self,
            **kwargs) -> Tuple[PathLike, PathLike]:
        """Start model inside container and return config file and work dir.

        Args:

            - **kwargs (optional, dict): Should be passed as a dict,
            e.g. `meteoOptions = {"temperatureNC": "era5_tas_1990_2000.nc"}`
            where meteoOptions is the section in which the temperatureNC option
            may be found. See :py:attr:`~parameters` for all available settings.

        Returns: Path to config file and work dir
        """
        work_dir = self.work_dir
        cfg_file = self._update_config(**kwargs)

        self._start_container()

        return cfg_file, work_dir

    def _update_config(self, **kwargs):
        cfg = self.config

        default_input_dir = self.parameter_set.input_dir

        for section, options in kwargs.items():
            if not cfg.has_section(section):
                cfg.add_section(section)

            for option, value in options.items():

                if Path(value).exists():
                    # New data paths must be mounted on the container
                    inputpath = Path(value).expanduser().resolve()
                    if default_input_dir in inputpath.parents:
                        pass
                    elif inputpath.is_dir():
                        self.additional_input_dirs.append(str(inputpath))
                    else:
                        self.additional_input_dirs.append(str(inputpath.parent))
                    cfg.set(section, option, str(inputpath))
                else:
                    cfg.set(section, option, value)

        new_cfg_file = Path(self.work_dir) / "pcrglobwb_ewatercycle.ini"
        with new_cfg_file.open("w") as filename:
            cfg.write(filename)

        self.cfg_file = new_cfg_file.expanduser().resolve()
        return self.cfg_file

    def _start_container(self):
        input_dirs = [self.parameter_set.input_dir] + self.additional_input_dirs

        if CFG["container_engine"] == "docker":
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                work_dir=str(self.work_dir),
                input_dirs=[str(input_dir) for input_dir in input_dirs],
                timeout=10,
            )
        elif CFG["container_engine"] == "singularity":
            message = f"No singularity image found at {image}"
            assert self.singularity_image.exists(), message

            self.bmi = BmiClientSingularity(
                image=str(self.singularity_image),
                work_dir=str(self.work_dir),
                input_dirs=[str(input_path) for input_path in input_dirs],
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
