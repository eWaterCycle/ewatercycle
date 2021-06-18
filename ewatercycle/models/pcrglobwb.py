import time
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple, Union

import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing.pcrglobwb import PCRGlobWBForcing
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import CaseConfigParser
from ewatercycle.util import get_time
from grpc import FutureTimeoutError


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

    def __str__(self):
        """Nice formatting of the parameterset object."""
        return "\n".join(
            [
                "Wflow parameter set",
                "-------------------",
                f"Directory: {self.input_dir}",
                f"Default configuration file: {self.default_config}",
            ]
        )


class PCRGlobWB(AbstractModel):
    """eWaterCycle implementation of PCRGlobWB hydrological model.

    Args:

        version: pick a version from :py:attr:`~available_versions`
        parameter_set: instance of :py:class:`~PCRGlobWBParameterSet`.
        forcing: ewatercycle forcing container;
            see :py:mod:`ewatercycle.forcing`.

    Attributes:

        bmi (Bmi): GRPC4BMI Basic Modeling Interface object
    """

    available_versions = ("setters",)

    def __init__(
        self,
        version: str,
        parameter_set: PCRGlobWBParameterSet,
        forcing: PCRGlobWBForcing,
    ):
        super().__init__()

        self.version = version
        self.parameter_set = parameter_set
        self.forcing = forcing

        self._set_docker_image()

        self._setup_work_dir()
        self._setup_default_config()

    def _set_docker_image(self):
        images = {
            "setters": "ewatercycle/pcrg-grpc4bmi:setters",
        }
        self.docker_image = images[self.version]

    def _setup_work_dir(self):
        # Must exist before setting up default config
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        work_dir = Path(CFG["output_dir"]) / f"pcrglobwb_{timestamp}"
        work_dir.mkdir()
        self.work_dir = work_dir.expanduser().resolve()

    def _setup_default_config(self):
        config_file = self.parameter_set.default_config
        input_dir = self.parameter_set.input_dir

        cfg = CaseConfigParser()
        cfg.read(config_file)
        cfg.set("globalOptions", "inputDir", str(input_dir))
        cfg.set("globalOptions", "outputDir", str(self.work_dir))
        cfg.set(
            "globalOptions",
            "startTime",
            get_time(self.forcing.start_time).strftime("%Y-%m-%d"),
        )
        cfg.set(
            "globalOptions",
            "endTime",
            get_time(self.forcing.start_time).strftime("%Y-%m-%d"),
        )
        cfg.set(
            "meteoOptions",
            "temperatureNC",
            str(
                (Path(self.forcing.directory) / self.forcing.temperatureNC)
                .expanduser()
                .resolve()
            ),
        )
        cfg.set(
            "meteoOptions",
            "precipitationNC",
            str(
                (Path(self.forcing.directory) / self.forcing.precipitationNC)
                .expanduser()
                .resolve()
            ),
        )

        self.config = cfg

    def setup(self, **kwargs) -> Tuple[PathLike, PathLike]:  # type: ignore
        """Start model inside container and return config file and work dir.

        Args:
            additional_input_dirs: By default, the model only has access to
                its working directory, the parameter sets, and the forcing
                directory. This option makes it possible to add other external
                inputs, that can then be configured in the config file.
            **kwargs: Use :py:meth:parameters to see all configurable options for this model,

        Returns: Path to config file and work dir
        """
        self._update_config(**kwargs)

        cfg_file = self._export_config()
        work_dir = self.work_dir

        self._start_container()

        return cfg_file, work_dir

    def _update_config(self, **kwargs):
        cfg = self.config

        if "start_time" in kwargs:
            cfg.set(
                "globalOptions",
                "startTime",
                get_time(kwargs["start_time"]).strftime("%Y-%m-%d"),
            )

        if "end_time" in kwargs:
            cfg.set(
                "globalOptions",
                "endTime",
                get_time(kwargs["end_time"]).strftime("%Y-%m-%d"),
            )

        if "routing_method" in kwargs:
            cfg.set(
                "routingOptions", "routingMethod", kwargs["routing_method"]
            )

        if "dynamic_flood_plain" in kwargs:
            cfg.set(
                "routingOptions",
                "dynamicFloodPlain",
                kwargs["dynamic_flood_plain"],
            )

        if "max_spinups_in_years" in kwargs:
            cfg.set(
                "globalOptions",
                "maxSpinUpsInYears",
                str(kwargs["max_spinups_in_years"]),
            )

    def _export_config(self) -> PathLike:
        new_cfg_file = Path(self.work_dir) / "pcrglobwb_ewatercycle.ini"
        with new_cfg_file.open("w") as filename:
            self.config.write(filename)

        self.cfg_file = new_cfg_file.expanduser().resolve()
        return self.cfg_file

    def _start_container(self):
        additional_input_dirs = [
            str(self.parameter_set.input_dir),
            str(self.forcing.directory),
        ]

        if CFG["container_engine"] == "docker":
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                work_dir=str(self.work_dir),
                input_dirs=additional_input_dirs,
                timeout=10,
            )
        elif CFG["container_engine"] == "singularity":
            try:
                self.bmi = BmiClientSingularity(
                    image=f"docker://{self.docker_image}",
                    work_dir=str(self.work_dir),
                    input_dirs=additional_input_dirs,
                    timeout=15,
                )
            except FutureTimeoutError:
                raise ValueError(
                    "Couldn't spawn the singularity container within allocated"
                    " time limit (15 seconds). You may try building it with "
                    f"`!singularity run docker://{self.docker_image}` and try "
                    "again. Please also inform the system administrator that "
                    "the singularity image was missing."
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
                "time": num2date(self.bmi.get_current_time(), time_units),
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
            (
                "start_time",
                f"{cfg.get('globalOptions', 'startTime')}T00:00:00Z",
            ),
            ("end_time", f"{cfg.get('globalOptions', 'endTime')}T00:00:00Z"),
            ("routing_method", cfg.get("routingOptions", "routingMethod")),
            (
                "max_spinups_in_years",
                cfg.get("globalOptions", "maxSpinUpsInYears"),
            ),
        ]
