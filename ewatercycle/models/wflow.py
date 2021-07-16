import datetime
import logging
import shutil
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple, cast

import numpy as np
import xarray as xr
from cftime import num2date
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing._wflow import WflowForcing
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parameter_sets import ParameterSet
from ewatercycle.parametersetdb.config import CaseConfigParser
from ewatercycle.util import find_closest_point, get_time, to_absolute_path

logger = logging.getLogger(__name__)


class Wflow(AbstractModel[WflowForcing]):
    """Create an instance of the Wflow model class.

    Args:
        version: pick a version from :py:attr:`~available_versions`
        parameter_set: instance of :py:class:`~ewatercycle.parameter_sets.default.ParameterSet`.
        forcing: instance of :py:class:`~WflowForcing` or None.
            If None, it is assumed that forcing is included with the parameter_set.
    """

    available_versions = ("2020.1.1",)
    """Show supported WFlow versions in eWaterCycle"""

    def __init__(
        self,
        version: str,
        parameter_set: ParameterSet,
        forcing: Optional[WflowForcing] = None,
    ):

        super().__init__(version, parameter_set, forcing)
        self._set_docker_image()
        self._setup_default_config()

    def _set_docker_image(self):
        images = {
            # "2019.1": "ewatercycle/wflow-grpc4bmi:2019.1", # no good ini file
            "2020.1.1": "ewatercycle/wflow-grpc4bmi:2020.1.1",
        }
        self.docker_image = images[self.version]

    def _singularity_image(self, singularity_dir):
        images = {
            "2020.1.1": "ewatercycle-wflow-grpc4bmi_2020.1.1.sif",
        }
        image = singularity_dir / images[self.version]
        return str(image)

    def _setup_default_config(self):
        config_file = self.parameter_set.config
        forcing = self.forcing

        cfg = CaseConfigParser()
        cfg.read(config_file)

        if forcing:
            cfg.set("framework", "netcdfinput", Path(forcing.netcdfinput).name)
            cfg.set("inputmapstacks", "Precipitation", forcing.Precipitation)
            cfg.set(
                "inputmapstacks",
                "EvapoTranspiration",
                forcing.EvapoTranspiration,
            )
            cfg.set("inputmapstacks", "Temperature", forcing.Temperature)
            cfg.set("run", "starttime", _iso_to_wflow(forcing.start_time))
            cfg.set("run", "endtime", _iso_to_wflow(forcing.end_time))
        if self.version == "2020.1.1":
            if not cfg.has_section("API"):
                logger.warning(
                    "Config file from parameter set is missing API section, adding section"
                )
                cfg.add_section("API")
            if not cfg.has_option("API", "RiverRunoff"):
                logger.warning(
                    "Config file from parameter set is missing RiverRunoff option in API section, "
                    "added it with value '2, m/s option'"
                )
                cfg.set("API", "RiverRunoff", "2, m/s")

        self.config = cfg

    def setup(self, cfg_dir: str = None, **kwargs) -> Tuple[str, str]:  # type: ignore
        """Start the model inside a container and return a valid config file.

        Args:
            cfg_dir: a run directory given by user or created for user.
            **kwargs (optional, dict): see :py:attr:`~parameters` for all
                configurable model parameters.

        Returns:
            Path to config file and working directory
        """
        self._setup_working_directory(cfg_dir)
        cfg = self.config

        if "start_time" in kwargs:
            cfg.set("run", "starttime", _iso_to_wflow(kwargs["start_time"]))
        if "end_time" in kwargs:
            cfg.set("run", "endtime", _iso_to_wflow(kwargs["end_time"]))

        updated_cfg_file = to_absolute_path(
            "wflow_ewatercycle.ini", parent=self.work_dir
        )
        with updated_cfg_file.open("w") as filename:
            cfg.write(filename)

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

        return (
            str(updated_cfg_file),
            str(self.work_dir),
        )

    def _setup_working_directory(self, cfg_dir: str = None):
        if cfg_dir:
            self.work_dir = to_absolute_path(cfg_dir)
        else:
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y%m%d_%H%M%S"
            )
            self.work_dir = to_absolute_path(
                f"wflow_{timestamp}", parent=CFG["output_dir"]
            )
        # Make sure parents exist
        self.work_dir.parent.mkdir(parents=True, exist_ok=True)

        assert self.parameter_set
        shutil.copytree(src=self.parameter_set.directory, dst=self.work_dir)
        if self.forcing:
            forcing_path = to_absolute_path(
                self.forcing.netcdfinput, parent=self.forcing.directory
            )
            shutil.copy(src=forcing_path, dst=self.work_dir)

    def _start_container(self):
        if CFG["container_engine"] == "docker":
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                work_dir=str(self.work_dir),
                timeout=10,
            )
        elif CFG["container_engine"] == "singularity":
            self.bmi = BmiClientSingularity(
                image=self._singularity_image(CFG['singularity_dir']),
                work_dir=str(self.work_dir),
                timeout=15,
            )
        else:
            raise ValueError(f"Unknown container technology: {CFG['container_engine']}")

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
            ("start_time", _wflow_to_iso(cfg.get("run", "starttime"))),
            ("end_time", _wflow_to_iso(cfg.get("run", "endtime"))),
        ]


def _wflow_to_iso(t):
    dt = datetime.datetime.fromisoformat(t)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_to_wflow(t):
    dt = get_time(t)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
