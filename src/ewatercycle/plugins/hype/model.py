"""eWaterCycle wrapper around Hype BMI."""
import datetime
import logging
import types
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

import bmipy
import xarray as xr
from dateutil.parser import parse
from dateutil.tz import UTC
from pydantic import PrivateAttr, computed_field, model_validator

from ewatercycle.base.model import ISO_TIMEFMT, ContainerizedModel
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.container import ContainerImage
from ewatercycle.plugins.hype.forcing import HypeForcing
from ewatercycle.util import geographical_distances, get_time

logger = logging.getLogger(__name__)


class Hype(ContainerizedModel):
    """eWaterCycle implementation of Hype hydrological model.

    Model documentation at http://www.smhi.net/hype/wiki/doku.php .

    Args:
        parameter_set: instance of
            :py:class:`~ewatercycle.parameter_sets.default.ParameterSet`.
        forcing: ewatercycle forcing container;
            see :py:mod:`ewatercycle.forcing`.

    """

    forcing: Optional[HypeForcing] = None
    parameter_set: ParameterSet  # not optional for this model
    bmi_image: ContainerImage = ContainerImage("ewatercycle/hype-grpc4bmi:feb2021")

    _config: str = PrivateAttr()
    _start: datetime.datetime = PrivateAttr()
    _end: datetime.datetime = PrivateAttr()
    _crit: datetime.datetime = PrivateAttr()

    @model_validator(mode="after")
    def _initialize_config(self):
        """Load config from parameter set and update with forcing info."""
        self._config = self.parameter_set.config.read_text(encoding="cp437")
        self._start = _get_hype_time(_get_code_in_cfg(self._config, "bdate"))
        self._end = _get_hype_time(_get_code_in_cfg(self._config, "edate"))
        self._crit = _get_hype_time(_get_code_in_cfg(self._config, "cdate"))
        if self._crit is None:
            self._crit = self._start
            self._config = _set_code_in_cfg(
                self._config, "cdate", self._crit.strftime("%Y-%m-%d %H:%M:%S")
            )
        if self.forcing is not None:
            self._start = get_time(self.forcing.start_time)
            self._config = _set_code_in_cfg(
                self._config, "bdate", self._start.strftime("%Y-%m-%d %H:%M:%S")
            )
            self._end = get_time(self.forcing.end_time)
            self._config = _set_code_in_cfg(
                self._config, "edate", self._end.strftime("%Y-%m-%d %H:%M:%S")
            )
            # Also set crit time to start time, it can be overwritten in setup()
            self._crit = self._start
            self._config = _set_code_in_cfg(
                self._config, "cdate", self._crit.strftime("%Y-%m-%d %H:%M:%S")
            )

    def _make_cfg_file(self, **kwargs) -> Path:
        """Create a Hype config file and return its path."""
        self._update_config(**kwargs)
        return self._export_config()

    def _update_config(self, **kwargs) -> None:
        cfg = self._config
        if "start_time" in kwargs:
            self._start = get_time(kwargs["start_time"])
            cfg = _set_code_in_cfg(
                cfg, "bdate", self._start.strftime("%Y-%m-%d %H:%M:%S")
            )
        if "end_time" in kwargs:
            self._end = get_time(kwargs["end_time"])
            cfg = _set_code_in_cfg(
                cfg, "edate", self._end.strftime("%Y-%m-%d %H:%M:%S")
            )
        if "start_time" in kwargs and "crit_time" not in kwargs:
            # Overwrite cdate to start when no crit is given
            self._crit = self._start
            cfg = _set_code_in_cfg(
                cfg, "cdate", self._crit.strftime("%Y-%m-%d %H:%M:%S")
            )
        elif "crit_time" in kwargs:
            self._crit = get_time(kwargs["crit_time"])
            cfg = _set_code_in_cfg(
                cfg, "cdate", self._crit.strftime("%Y-%m-%d %H:%M:%S")
            )

        # Set resultdir to . so no sub dirs are needed
        cfg = _set_code_in_cfg(cfg, "resultdir", "./")
        self._config = cfg

    def _export_config(self) -> Path:
        # write info.txt
        cfg_file = self._cfg_dir / "info.txt"
        cfg_file.write_text(self._config, encoding="cp437")

        return cfg_file

    def _make_bmi_instance(self) -> bmipy.Bmi:
        """Make the bmi instance and overwrite 'get_time_units' method."""
        bmi = super()._make_bmi_instance()

        since = self._start.strftime(ISO_TIMEFMT)

        # The Hype get_time_units() returns `hours since start of simulation` and
        #   get_start_time() returns 0.
        # A relative datetime is not very useful, so here we overwrite the
        #   get_time_units to return the absolute datetime.
        def get_time_units(_self):
            return f"hours since {since}"

        bmi.get_time_units = types.MethodType(get_time_units, bmi)

        return bmi

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        raise NotImplementedError("Hype coordinates cannot be mapped to grid")

    def get_latlon_grid(self, name: str) -> tuple[Any, Any, Any]:
        raise NotImplementedError("Hype coordinates cannot be mapped to grid")

    @property
    def parameters(self) -> dict[str, Any]:
        """List the parameters for this model.

        Exposed Lisflood parameters:
            start_time: Start time of model in UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing end time is used.
            crit_time: Start date for the output of results and calculations of criteria.
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then start_time is used.
        """
        return {
            "start_time": self._start.strftime(ISO_TIMEFMT),
            "end_time": self._end.strftime(ISO_TIMEFMT),
            "crit_time": self._crit.strftime(ISO_TIMEFMT),
        }

    def _coords_to_indices(
        self, name: str, lat: Iterable[float], lon: Iterable[float]
    ) -> Iterable[int]:
        grid_id = self.bmi.get_var_grid(name)
        x = self.bmi.get_grid_x(grid_id)
        y = self.bmi.get_grid_y(grid_id)

        indices = []
        for plon, plat in zip(lon, lat):
            dist = geographical_distances(plon, plat, x, y)
            index = dist.argmin()
            indices.append(int(index))

        return indices


def _get_code_in_cfg(content: str, code: str):
    lines = content.splitlines()
    for line in lines:
        if line.startswith(code):
            chunks = line.split()
            chunks.pop(0)  # Only works with code without spaces
            return " ".join(chunks)


def _set_code_in_cfg(content: str, code: str, value: str) -> str:
    lines = content.splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith(code):
            line = f"{code} {value}"
            found = True
        new_lines.append(line)
    if not found:
        new_lines.append(f"{code} {value}")
    new_lines.append("")
    return "\n".join(new_lines)


def _get_hype_time(value: str) -> datetime.datetime:
    """Converts `yyyy-mm-dd [HH:MM]` string to datetime object."""
    return parse(value).replace(tzinfo=UTC)
