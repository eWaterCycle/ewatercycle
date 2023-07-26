"""eWaterCycle wrapper around PCRGlobWB BMI."""

import logging
from os import PathLike
from typing import Optional

from pydantic import PrivateAttr

from ewatercycle.base.model import ContainerizedModel
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.container import ContainerImage
from ewatercycle.plugins.pcrglobwb.forcing import PCRGlobWBForcing
from ewatercycle.util import CaseConfigParser, get_time, to_absolute_path

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
    parameter_set: ParameterSet  # not optional for this model
    bmi_image: ContainerImage = ContainerImage("ewatercycle/pcrg-grpc4bmi:setters")
    _config: CaseConfigParser = PrivateAttr()

    # TODO: move to real post_init in pydantic v2.
    def _post_init(self):
        """Load config from parameter set and update with forcing info."""
        if not hasattr(self, "_config"):
            cfg = CaseConfigParser()
            cfg.read(self.parameter_set.config)
            cfg.set("globalOptions", "inputDir", str(self.parameter_set.directory))

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

            self._config = cfg

    def setup(self, *, cfg_dir: str | None = None, **kwargs) -> tuple[str, str]:
        self._post_init()
        return super().setup(cfg_dir=cfg_dir, **kwargs)

    def get_parameters(self) -> dict:
        self._post_init()
        return {
            "start_time": f"{self._config.get('globalOptions', 'startTime')}T00:00:00Z",
            "end_time": f"{self._config.get('globalOptions', 'endTime')}T00:00:00Z",
            "routing_method": self._config.get("routingOptions", "routingMethod"),
            "max_spinups_in_years": self._config.get(
                "globalOptions", "maxSpinUpsInYears"
            ),
        }

    def _make_cfg_file(self, **kwargs):
        self._update_config(**kwargs)
        return self._export_config()

    def _update_config(self, **kwargs):
        cfg = self._config

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
        self._config.set("globalOptions", "outputDir", str(self._cfg_dir))
        new_cfg_file = to_absolute_path(
            "pcrglobwb_ewatercycle.ini", parent=self._cfg_dir
        )
        with new_cfg_file.open("w") as filename:
            self._config.write(filename)

        return new_cfg_file

    def get_latlon_grid(self, name):
        """Grid latitude, longitude and shape for variable.

        Note: deviates from default implementation.
        """
        grid_id = self._bmi.get_var_grid(name)
        shape = self._bmi.get_grid_shape(name)
        grid_lon = self._bmi.get_grid_y(grid_id)
        grid_lat = self._bmi.get_grid_x(grid_id)
        return grid_lat, grid_lon, shape
