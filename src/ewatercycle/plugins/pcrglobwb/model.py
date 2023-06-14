"""eWaterCycle wrapper around PCRGlobWB BMI."""

import datetime
import logging
from os import PathLike
from typing import Any, Iterable, Optional, cast

import numpy as np
import xarray as xr
from cftime import num2date

from ewatercycle import CFG
from ewatercycle.base.model import ContainerizedModel
from ewatercycle.container import ContainerImage
from ewatercycle.plugins.pcrglobwb.forcing import PCRGlobWBForcing
from ewatercycle.util import (
    CaseConfigParser,
    find_closest_point,
    get_time,
    to_absolute_path,
)

logger = logging.getLogger(__name__)


class PCRGlobWB(ContainerizedModel):
    """eWaterCycle implementation of PCRGlobWB hydrological model.

    Args:
        parameter_set: instance of
            :py:class:`~ewatercycle.parameter_sets.default.ParameterSet`.
        forcing: ewatercycle forcing container;
            see :py:mod:`ewatercycle.forcing`.

    """

    forcing: Optional[PCRGlobWBForcing] = None
    bmi_image: ContainerImage("ewatercycle/pcrg-grpc4bmi:setters")

    @property
    def parameters(self) -> dict[str, Any]:
        """The configurable parameters for this model."""
        cfg = self.config
        return {
            "start_time": f"{cfg.get('globalOptions', 'startTime')}T00:00:00Z",
            "end_time": f"{cfg.get('globalOptions', 'endTime')}T00:00:00Z",
            "routing_method": cfg.get("routingOptions", "routingMethod"),
            "max_spinups_in_years": cfg.get("globalOptions", "maxSpinUpsInYears"),
        }

    def __post_init_post_parse__(self):
        super().__post_init_post_parse__()
        self._setup_default_config()

    def _setup_work_dir(self, cfg_dir: Optional[str] = None):
        if cfg_dir:
            self.work_dir = to_absolute_path(cfg_dir)
        else:
            # Must exist before setting up default config
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y%m%d_%H%M%S"
            )
            self.work_dir = to_absolute_path(
                f"pcrglobwb_{timestamp}", parent=CFG.output_dir
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
                    to_absolute_path(  # TODO fix type error
                        self.forcing.temperatureNC,
                        parent=self.forcing.directory,
                    )
                ),
            )
            cfg.set(
                "meteoOptions",
                "precipitationNC",
                str(
                    to_absolute_path(  # TODO fix type error
                        self.forcing.precipitationNC,
                        parent=self.forcing.directory,
                    )
                ),
            )

        self.config = cfg

    def _make_cfg_file(self, **kwargs):
        self._update_config(**kwargs)
        return self._export_config()

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
            cfg.set("routingOptions", "routingMethod", kwargs["routing_method"])

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

        return new_cfg_file

    def _coords_to_indices(
        self, name: str, lat: Iterable[float], lon: Iterable[float]
    ) -> Iterable[int]:
        """Convert lat/lon values to index.

        Args:
            lat: Latitudinal value
            lon: Longitudinal value

        """
        # TODO fix errors about dest argument
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

    # TODO: move coordinate and xarray methods to default implementation
