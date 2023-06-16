"""eWaterCycle wrapper around PCRGlobWB BMI."""

import datetime
import logging
from os import PathLike
from typing import Optional

from pydantic import PrivateAttr, root_validator

from ewatercycle import CFG
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
    bmi_image = ContainerImage("ewatercycle/pcrg-grpc4bmi:setters")
    _config: CaseConfigParser = PrivateAttr()

    @root_validator
    def _parse_config(cls, values):
        """Load config from parameter set and update with forcing info."""
        ps = values.get("parameter_set")

        cfg = CaseConfigParser()
        cfg.read(ps.config)
        cfg.set("globalOptions", "inputDir", str(ps.directory))

        forcing = values.get("forcing")
        if forcing:
            cfg.set(
                "globalOptions",
                "startTime",
                get_time(forcing.start_time).strftime("%Y-%m-%d"),
            )
            cfg.set(
                "globalOptions",
                "endTime",
                get_time(forcing.start_time).strftime("%Y-%m-%d"),
            )
            cfg.set(
                "meteoOptions",
                "temperatureNC",
                str(
                    to_absolute_path(  # TODO fix type error
                        forcing.temperatureNC,
                        parent=forcing.directory,
                    )
                ),
            )
            cfg.set(
                "meteoOptions",
                "precipitationNC",
                str(
                    to_absolute_path(  # TODO fix type error
                        forcing.precipitationNC,
                        parent=forcing.directory,
                    )
                ),
            )

        values.update(_config=cfg)
        return values

    @root_validator
    def _update_parameters(cls, values):
        cfg = values.get("_config")
        values.get("parameters").update(
            {
                "start_time": f"{cfg.get('globalOptions', 'startTime')}T00:00:00Z",
                "end_time": f"{cfg.get('globalOptions', 'endTime')}T00:00:00Z",
                "routing_method": cfg.get("routingOptions", "routingMethod"),
                "max_spinups_in_years": cfg.get("globalOptions", "maxSpinUpsInYears"),
            }
        )
        return values

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
        self._config.set("globalOptions", "outputDir", str(self.work_dir))
        new_cfg_file = to_absolute_path(
            "pcrglobwb_ewatercycle.ini", parent=self.work_dir
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
