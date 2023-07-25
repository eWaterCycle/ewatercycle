"""eWaterCycle wrapper around Hype BMI."""
import datetime
import logging
import shutil
import types
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

import bmipy
import xarray as xr
from dateutil.parser import parse
from dateutil.tz import UTC
from pydantic import PrivateAttr, root_validator

from ewatercycle import CFG
from ewatercycle.base.model import ISO_TIMEFMT, ContainerizedModel
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.container import ContainerImage
from ewatercycle.plugins.hype.forcing import HypeForcing
from ewatercycle.util import (
    geographical_distances,
    get_time,
    to_absolute_path,
)

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

    @root_validator
    def _parse_config(cls, values: dict) -> dict:
        """Load config from parameter set and update with forcing info."""
        ps: ParameterSet = values.get("parameter_set")
        assert isinstance(ps, ParameterSet)  # pydantic doesn't do its job reliably
        forcing = values.get("forcing")

        cfg = ps.config.read_text(encoding="cp437")
        start = _get_hype_time(_get_code_in_cfg(cfg, "bdate"))
        end = _get_hype_time(_get_code_in_cfg(cfg, "edate"))
        crit = _get_hype_time(_get_code_in_cfg(cfg, "cdate"))
        if crit is None:
            crit = start
            cfg = _set_code_in_cfg(cfg, "cdate", crit.strftime("%Y-%m-%d %H:%M:%S"))
        if forcing is not None:
            start = get_time(forcing.start_time)
            cfg = _set_code_in_cfg(cfg, "bdate", start.strftime("%Y-%m-%d %H:%M:%S"))
            end = get_time(forcing.end_time)
            cfg = _set_code_in_cfg(cfg, "edate", end.strftime("%Y-%m-%d %H:%M:%S"))
            # Also set crit time to start time, it can be overwritten in setup()
            crit = start
            cfg = _set_code_in_cfg(cfg, "cdate", crit.strftime("%Y-%m-%d %H:%M:%S"))

        cls._config = cfg
        cls._start = start
        cls._end = end
        cls._crit = crit
        return values

    def setup(self, **kwargs) -> Tuple[str, str]:
        """Configure model run.

        1. Creates config file and config directory
           based on the forcing variables and time range.
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            cfg_dir: a run directory given by user or created for user.
            start_time: Start time of model in UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing end time is used.
            crit_time: Start date for the output of results and calculations of criteria.
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then start_time is used.

        Returns:
            Path to config file and path to config directory
        """
        return super().setup(**kwargs)

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

    def _make_cfg_dir(self, cfg_dir: Optional[Path] = None) -> Path:
        if cfg_dir:
            cfg_dir = to_absolute_path(cfg_dir)
        else:
            # Must exist before setting up default config
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y%m%d_%H%M%S"
            )
            cfg_dir = to_absolute_path(
                f"hype_{timestamp}", parent=CFG.output_dir
            )
        cfg_dir.mkdir(parents=True, exist_ok=True)

        # copy parameter set files to cfg_dir
        assert self.parameter_set
        shutil.copytree(
            src=self.parameter_set.directory, dst=cfg_dir, dirs_exist_ok=True
        )

        # copy forcing files to cfg_dir
        if self.forcing is not None and self.forcing.directory is not None:
            forcing_dir = self.forcing.directory
            shutil.copytree(src=forcing_dir, dst=cfg_dir, dirs_exist_ok=True)

        return cfg_dir

    def _make_bmi_instance(self) -> bmipy.Bmi:
        """Make the bmi instance and overwrite 'get_time_units' method."""
        bmi = super()._make_bmi_instance()

        since = self._start.strftime(ISO_TIMEFMT)

        # The Hype get_time_units() returns `hours since start of simulation` and get_start_time() returns 0
        # A relative datetime is not very useful, so here we overwrite the get_time_units to return the absolute datetime.
        def get_time_units(_self):
            return f"hours since {since}"

        bmi.get_time_units = types.MethodType(get_time_units, bmi)

        return bmi

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Get value as xarray

        Args:
            name: Name of value to retrieve.

        Returns:
            Xarray with values for each sub catchment

        """
        raise NotImplementedError("Hype coordinates cannot be mapped to grid")

    def get_latlon_grid(self, name: str) -> tuple[Any, Any, Any]:
        raise NotImplementedError("Hype coordinates cannot be mapped to grid")

    def get_parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the parameters for this model."""
        assert self.parameter_set is not None
        return [
            ("start_time", self._start.strftime(ISO_TIMEFMT)),
            ("end_time", self._end.strftime(ISO_TIMEFMT)),
            ("crit_time", self._crit.strftime(ISO_TIMEFMT)),
        ]

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
