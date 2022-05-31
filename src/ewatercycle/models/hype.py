import datetime
import logging
from typing import Any, Iterable, Optional, Tuple, cast

import numpy as np
import xarray as xr
from cftime import num2date

from ewatercycle import CFG
from ewatercycle.forcing._hype import HypeForcing
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parameter_sets import ParameterSet
from ewatercycle.util import to_absolute_path

logger = logging.getLogger(__name__)

_version_images = {
    "feb2021": {
        "docker": "ewatercycle/hype-grpc4bmi:feb2021",
        "singularity": "ewatercycle-hype-grpc4bmi_feb2021.sif",
    }
}


class Hype(AbstractModel[HypeForcing]):
    """eWaterCycle implementation of Hype hydrological model.

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
        # TODO read config file from parameter_set

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

        # TODO copy parameter set files to cfg_dir
        # TODO copy forcing files to cfg_dir

        # TODO merge args into config object

        # TODO write info.txt
        cfg_file = cfg_dir_as_path / "info.txt"

        # TODO start container

        return str(cfg_file), str(cfg_dir_as_path)

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the parameters for this model."""
        assert self.parameter_set is not None
        return [
            # TODO add start_time, end_time, crit_time
        ]

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Get value as xarray

        Args:
            name: Name of value to retrieve.

        Returns:
            Xarray with values for each sub catchment

        """
        """Return the value as xarray object."""
        # Get time information
        time_units = self.bmi.get_time_units()
        grid = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid)

        return xr.DataArray(
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
