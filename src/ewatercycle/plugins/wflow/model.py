"""eWaterCycle wrapper around WFlow BMI."""

import datetime
import logging
import shutil
from pathlib import Path
from typing import Optional

from pydantic import PrivateAttr, root_validator

from ewatercycle import CFG
from ewatercycle.base.model import ISO_TIMEFMT, ContainerizedModel
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.container import ContainerImage
from ewatercycle.plugins.wflow.forcing import WflowForcing
from ewatercycle.util import CaseConfigParser, get_time, to_absolute_path

logger = logging.getLogger(__name__)


class Wflow(ContainerizedModel):
    """Create an instance of the Wflow model class.

    Args:
        parameter_set: instance of
            :py:class:`~ewatercycle.parameter_sets.default.ParameterSet`.
        forcing: instance of :py:class:`~WflowForcing` or None.
            If None, it is assumed that forcing is included with the parameter_set.
    """

    forcing: Optional[WflowForcing] = None
    parameter_set: ParameterSet  # not optional for this model
    bmi_image: ContainerImage = ContainerImage("ewatercycle/wflow-grpc4bmi:2020.1.3")
    version: str = "2020.1.3"

    _config: CaseConfigParser = PrivateAttr()
    _work_dir: Path = PrivateAttr()

    # TODO: move to post_init in pydantic v2.
    @root_validator
    def _parse_config(cls, values):
        """Load config from parameter set and update with forcing info."""
        ps = values.get("parameter_set")
        assert isinstance(ps, ParameterSet)  # pydantic doesn't do its job reliably

        cfg = CaseConfigParser()
        cfg.read(ps.config)

        forcing = values.get("forcing")
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
        if not cfg.has_section("API"):
            logger.warning(
                "Config file from parameter set is missing API section, "
                "adding section"
            )
            cfg.add_section("API")
        if not cfg.has_option("API", "RiverRunoff"):
            logger.warning(
                "Config file from parameter set is missing RiverRunoff "
                "option in API section, added it with value '2, m/s option'"
            )
            cfg.set("API", "RiverRunoff", "2, m/s")

        cls._config = cfg
        return values

    # TODO: create setup with custom docstring to explain extra kwargs
    # (start_time, end_time)

    def _make_cfg_file(self, **kwargs) -> Path:
        """Create a new wflow config file and return its path."""
        if "start_time" in kwargs:
            self._config.set("run", "starttime", _iso_to_wflow(kwargs["start_time"]))
        if "end_time" in kwargs:
            self._config.set("run", "endtime", _iso_to_wflow(kwargs["end_time"]))

        cfg_file = to_absolute_path("wflow_ewatercycle.ini", parent=self._work_dir)
        with cfg_file.open("w") as filename:
            self._config.write(filename)

        return cfg_file

    def _make_cfg_dir(self, cfg_dir: Optional[str] = None, **kwargs) -> Path:
        """Create working directory for parameter sets, forcing and wflow config."""
        if cfg_dir:
            self._work_dir = to_absolute_path(cfg_dir)
        else:
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y%m%d_%H%M%S"
            )
            self._work_dir = to_absolute_path(
                f"wflow_{timestamp}", parent=CFG.output_dir
            )
        # Make sure parents exist
        self._work_dir.parent.mkdir(parents=True, exist_ok=True)

        assert self.parameter_set
        shutil.copytree(src=self.parameter_set.directory, dst=self._work_dir)
        if self.forcing:
            forcing_path = to_absolute_path(
                self.forcing.netcdfinput, parent=self.forcing.directory
            )
            shutil.copy(src=forcing_path, dst=self._work_dir)

        return self._work_dir

    def get_parameters(self):
        self._post_init()
        return {
            "start_time": _wflow_to_iso(self._config.get("run", "starttime")),
            "end_time": _wflow_to_iso(self._config.get("run", "endtime")),
        }

    def get_latlon_grid(self, name):
        """Grid latitude, longitude and shape for variable.

        Note: deviates from default implementation.
        """
        grid_id = self._bmi.get_var_grid(name)
        shape = self._bmi.get_grid_shape(name)
        grid_lon = self._bmi.get_grid_y(grid_id)
        grid_lat = self._bmi.get_grid_x(grid_id)
        return grid_lat, grid_lon, shape


def _wflow_to_iso(time):
    dt = datetime.datetime.fromisoformat(time)
    return dt.strftime(ISO_TIMEFMT)


def _iso_to_wflow(time):
    dt = get_time(time)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
