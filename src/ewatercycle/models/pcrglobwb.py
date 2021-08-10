import datetime
import logging
from os import PathLike
from typing import Any, Iterable, Optional, Tuple, cast

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
from ewatercycle.util import find_closest_point, get_time, to_absolute_path

logger = logging.getLogger(__name__)


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
        forcing: Optional[PCRGlobWBForcing] = None,
    ):
        super().__init__(version, parameter_set, forcing)
        self._set_docker_image()
        self._setup_default_config()

    def _set_docker_image(self):
        images = {
            "setters": "ewatercycle/pcrg-grpc4bmi:setters",
        }
        self.docker_image = images[self.version]

    def _singularity_image(self, singularity_dir):
        images = {
            "setters": "ewatercycle-pcrg-grpc4bmi_setters.sif",
        }
        image = singularity_dir / images[self.version]
        return str(image)

    def _setup_work_dir(self, cfg_dir: str = None):
        if cfg_dir:
            self.work_dir = to_absolute_path(cfg_dir)
        else:
            # Must exist before setting up default config
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y%m%d_%H%M%S"
            )
            self.work_dir = to_absolute_path(
                f"pcrglobwb_{timestamp}", parent=CFG["output_dir"]
            )
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def _setup_default_config(self):
        config_file = self.parameter_set.config
        input_dir = self.parameter_set.directory

        cfg = CaseConfigParser()
        cfg.read(config_file)
        cfg.set("globalOptions", "inputDir", str(input_dir))
        if self.forcing:
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
                    to_absolute_path(
                        self.forcing.temperatureNC, parent=self.forcing.directory
                    )
                ),
            )
            cfg.set(
                "meteoOptions",
                "precipitationNC",
                str(
                    to_absolute_path(
                        self.forcing.precipitationNC, parent=self.forcing.directory
                    )
                ),
            )

        self.config = cfg

    def setup(self, cfg_dir: str = None, **kwargs) -> Tuple[str, str]:  # type: ignore
        """Start model inside container and return config file and work dir.

        Args:
            cfg_dir: a run directory given by user or created for user.
            **kwargs: Use :py:meth:`parameters` to see the current values
                configurable options for this model,

        Returns: Path to config file and work dir
        """
        self._setup_work_dir(cfg_dir)

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
                f"build {self._singularity_image(CFG['singularity_dir'])} docker://{self.docker_image}`"
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
        self.config.set("globalOptions", "outputDir", str(self.work_dir))
        new_cfg_file = to_absolute_path(
            "pcrglobwb_ewatercycle.ini", parent=self.work_dir
        )
        with new_cfg_file.open("w") as filename:
            self.config.write(filename)

        self.cfg_file = new_cfg_file
        return self.cfg_file

    def _start_container(self):
        additional_input_dirs = [str(self.parameter_set.directory)]
        if self.forcing:
            additional_input_dirs.append(self.forcing.directory)

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
                image=self._singularity_image(CFG['singularity_dir']),
                work_dir=str(self.work_dir),
                input_dirs=additional_input_dirs,
                timeout=15,
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )

    def _coords_to_indices(
        self, name: str, lat: Iterable[float], lon: Iterable[float]
    ) -> Iterable[int]:
        """Converts lat/lon values to index.

        Args:
            lat: Latitudinal value
            lon: Longitudinal value

        """
        grid_id = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid_id)  # (len(x), len(y))
        grid_lat = self.bmi.get_grid_x(grid_id)  # x is latitude
        grid_lon = self.bmi.get_grid_y(grid_id)  # y is longitude

        indices = []
        for point_lon, point_lat in zip(lon, lat):
            idx_lon, idx_lat = find_closest_point(
                grid_lon, grid_lat, point_lon, point_lat
            )
            idx_flat = cast(int, np.ravel_multi_index((idx_lat, idx_lon), shape))
            indices.append(idx_flat)

            logger.debug(
                f"Requested point was lon: {point_lon}, lat: {point_lat}; "
                "closest grid point is "
                f"{grid_lon[idx_lon]:.2f}, {grid_lat[idx_lat]:.2f}."
            )

        return indices

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
