import datetime
import logging
import shutil
import types
from typing import Any, Iterable, Optional, Tuple

import numpy as np
import xarray as xr
from basic_modeling_interface import Bmi
from cftime import num2date
from dateutil.parser import parse
from dateutil.tz import UTC
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing._hype import HypeForcing
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parameter_sets import ParameterSet
from ewatercycle.util import geographical_distances, get_time, to_absolute_path

logger = logging.getLogger(__name__)

_version_images = {
    "feb2021": {
        "docker": "ewatercycle/hype-grpc4bmi:feb2021",
        "singularity": "ewatercycle-hype-grpc4bmi_feb2021.sif",
    }
}


class Hype(AbstractModel[HypeForcing]):
    """eWaterCycle implementation of Hype hydrological model.

    Model documentation at http://www.smhi.net/hype/wiki/doku.php .

    Args:
        version: pick a version from :py:attr:`~available_versions`
        parameter_set: instance of
            :py:class:`~ewatercycle.parameter_sets.default.ParameterSet`.
        forcing: ewatercycle forcing container;
            see :py:mod:`ewatercycle.forcing`.

    """

    available_versions = tuple(_version_images.keys())

    def __init__(
        self,
        version: str,
        parameter_set: ParameterSet,
        forcing: Optional[HypeForcing] = None,
    ):
        super().__init__(version, parameter_set, forcing)
        assert version in _version_images
        self._setup_default_config()

    def _setup_default_config(self):
        assert self.parameter_set
        # read config file from parameter_set
        self._cfg = self.parameter_set.config.read_text(encoding="cp437")
        self._start = _get_hype_time(_get_code_in_cfg(self._cfg, "bdate"))
        self._end = _get_hype_time(_get_code_in_cfg(self._cfg, "edate"))
        self._crit = _get_hype_time(_get_code_in_cfg(self._cfg, "cdate"))
        if self._crit is None:
            self._crit = self._start
            self._cfg = _set_code_in_cfg(
                self._cfg, "cdate", self._crit.strftime("%Y-%m-%d %H:%M:%S")
            )
        if self.forcing is not None:
            self._start = get_time(self.forcing.start_time)
            self._cfg = _set_code_in_cfg(
                self._cfg, "bdate", self._start.strftime("%Y-%m-%d %H:%M:%S")
            )
            self._end = get_time(self.forcing.end_time)
            self._cfg = _set_code_in_cfg(
                self._cfg, "edate", self._end.strftime("%Y-%m-%d %H:%M:%S")
            )
            # Also set crit time to start time, it can be overwritten in setup()
            self._crit = self._start
            self._cfg = _set_code_in_cfg(
                self._cfg, "cdate", self._crit.strftime("%Y-%m-%d %H:%M:%S")
            )

    # unable to subclass with more specialized arguments so ignore type
    def setup(  # type: ignore
        self,
        start_time: str = None,
        end_time: str = None,
        crit_time: str = None,
        cfg_dir: str = None,
    ) -> Tuple[str, str]:
        """Configure model run.

        1. Creates config file and config directory
           based on the forcing variables and time range.
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            start_time: Start time of model in UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing end time is used.
            crit_time: Start date for the output of results and calculations of criteria.
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then start_time is used.
            cfg_dir: a run directory given by user or created for user.

        Returns:
            Path to config file and path to config directory
        """
        cfg_dir_as_path = _setup_cfg_dir(cfg_dir)

        # copy parameter set files to cfg_dir
        assert self.parameter_set
        shutil.copytree(
            src=self.parameter_set.directory, dst=cfg_dir_as_path, dirs_exist_ok=True
        )

        # copy forcing files to cfg_dir
        if self.forcing is not None:
            forcing_dir = self.forcing.directory
            shutil.copytree(src=forcing_dir, dst=cfg_dir_as_path, dirs_exist_ok=True)

        # merge args into config object
        if start_time is not None:
            self._start = get_time(start_time)
            self._cfg = _set_code_in_cfg(
                self._cfg, "bdate", self._start.strftime("%Y-%m-%d %H:%M:%S")
            )
        if end_time is not None:
            self._end = get_time(end_time)
            self._cfg = _set_code_in_cfg(
                self._cfg, "edate", self._end.strftime("%Y-%m-%d %H:%M:%S")
            )
        if start_time is not None and crit_time is None:
            # Overwrite cdate to start when no crit is given
            self._crit = self._start
            self._cfg = _set_code_in_cfg(
                self._cfg, "cdate", self._crit.strftime("%Y-%m-%d %H:%M:%S")
            )
        elif crit_time is not None:
            self._crit = get_time(crit_time)
            self._cfg = _set_code_in_cfg(
                self._cfg, "cdate", self._crit.strftime("%Y-%m-%d %H:%M:%S")
            )

        # Set resultdir to . so no sub dirs are needed
        self._cfg = _set_code_in_cfg(self._cfg, "resultdir", "./")

        # write info.txt
        cfg_file = cfg_dir_as_path / "info.txt"
        cfg_file.write_text(self._cfg, encoding="cp437")

        # start container
        work_dir = str(cfg_dir_as_path)
        self.bmi = _start_container(self.version, work_dir)

        since = self._start.strftime("%Y-%m-%dT%H:%M:%SZ")

        # The Hype get_time_units() returns `hours since start of simulation` and get_start_time() returns 0
        # A relative datetime is not very useful, so here we overwrite the get_time_units to return the absolute datetime.
        def get_time_units(_self):
            return f"hours since {since}"

        self.bmi.get_time_units = types.MethodType(get_time_units, self.bmi)

        return str(cfg_file), work_dir

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the parameters for this model."""
        assert self.parameter_set is not None
        return [
            ("start_time", self._start.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("end_time", self._end.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("crit_time", self._crit.strftime("%Y-%m-%dT%H:%M:%SZ")),
        ]

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Get value as xarray

        Args:
            name: Name of value to retrieve.

        Returns:
            Xarray with values for each sub catchment

        """
        raise NotImplementedError("Hype coordinates cannot be mapped to grid")

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
            indices.append(index)

        return indices


def _setup_cfg_dir(cfg_dir: str = None):
    if cfg_dir:
        work_dir = to_absolute_path(cfg_dir)
    else:
        # Must exist before setting up default config
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y%m%d_%H%M%S"
        )
        work_dir = to_absolute_path(f"hype_{timestamp}", parent=CFG["output_dir"])
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


def _start_container(version: str, work_dir: str):
    if CFG["container_engine"].lower() == "singularity":
        image = CFG["singularity_dir"] / _version_images[version]["singularity"]
        return BmiClientSingularity(
            image=str(image),
            work_dir=work_dir,
        )
    elif CFG["container_engine"].lower() == "docker":
        image = _version_images[version]["docker"]
        return BmiClientDocker(
            image=image,
            image_port=55555,  # TODO needed?
            work_dir=work_dir,
        )
    else:
        raise ValueError(
            f"Unknown container technology in CFG: {CFG['container_engine']}"
        )


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
    """Converts `yyyy-mm-dd [HH:MM]` string to datetime object"""
    return parse(value).replace(tzinfo=UTC)
