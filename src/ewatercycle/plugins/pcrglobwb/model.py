"""eWaterCycle wrapper around PCRGlobWB BMI."""

import datetime
import logging
from os import PathLike
from typing import Any, Optional

from ewatercycle import CFG
from ewatercycle.base.model import ContainerizedModel
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
    bmi_image = ContainerImage("ewatercycle/pcrg-grpc4bmi:setters")

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
        """Perform additional initalization steps."""
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

    def get_latlon_grid(self, name):
        """Grid latitude, longitude and shape for variable.

        Note: deviates from default implementation.
        """
        grid_id = self._bmi.get_var_grid(name)
        shape = self._bmi.get_grid_shape(name)
        grid_lon = self._bmi.get_grid_y(grid_id)
        grid_lat = self._bmi.get_grid_x(grid_id)
        return grid_lat, grid_lon, shape
