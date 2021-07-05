import time
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Tuple

import numpy as np
import xarray as xr
from cftime import num2date
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing._pcrglobwb import PCRGlobWBForcing
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parameter_sets import ParameterSet
from ewatercycle.parametersetdb.config import CaseConfigParser
from ewatercycle.util import get_time


class PCRGlobWB(AbstractModel[PCRGlobWBForcing]):
    """eWaterCycle implementation of PCRGlobWB hydrological model.

    Args:

        version: pick a version from :py:attr:`~available_versions`
        parameter_set: instance of :py:class:`~ewatercycle.parameter_sets.default.ParameterSet`.
        forcing: ewatercycle forcing container;
            see :py:mod:`ewatercycle.forcing`.

    """

    available_versions = ("setters",)

    def __init__(
        self,
        version: str,
        parameter_set: ParameterSet,
        forcing: PCRGlobWBForcing,
    ):
        super().__init__(version, parameter_set, forcing)
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
        config_file = self.parameter_set.config
        input_dir = self.parameter_set.directory

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

    def setup(self, **kwargs) -> Tuple[str, str]:  # type: ignore
        """Start model inside container and return config file and work dir.

        Args:
            **kwargs: Use :py:meth:`parameters` to see the current values
                configurable options for this model,

        Returns: Path to config file and work dir
        """
        self._update_config(**kwargs)

        cfg_file = self._export_config()
        work_dir = self.work_dir

        try:
            self._start_container()
        except FutureTimeoutError:
            # https://github.com/eWaterCycle/grpc4bmi/issues/95
            # https://github.com/eWaterCycle/grpc4bmi/issues/100
            raise ValueError(
                "Couldn't spawn container within allocated time limit "
                "(15 seconds). You may try pulling the docker image with"
                f" `docker pull {self.docker_image}` or call `singularity "
                f"exec docker://{self.docker_image} run-bmi-server -h`"
                "if you're using singularity, and then try again."
            )

        return str(cfg_file), str(work_dir)

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
            str(self.parameter_set.directory),
            str(self.forcing.directory),
        ]

        if CFG["container_engine"] == "docker":
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                work_dir=str(self.work_dir),
                input_dirs=additional_input_dirs,
                timeout=15,
            )
        elif CFG["container_engine"] == "singularity":
            self.bmi = BmiClientSingularity(
                image=f"docker://{self.docker_image}",
                work_dir=str(self.work_dir),
                input_dirs=additional_input_dirs,
                timeout=15,
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
