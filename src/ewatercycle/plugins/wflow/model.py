"""eWaterCycle wrapper around WFlow BMI."""

import datetime
import logging
import shutil
from pathlib import Path
from typing import Any, ItemsView, Optional

import bmipy
import numpy as np
from grpc4bmi.bmi_memoized import MemoizedBmi
from grpc4bmi.bmi_optionaldest import OptionalDestBmi
from pydantic import PrivateAttr, model_validator

from ewatercycle import CFG
from ewatercycle.base.model import ISO_TIMEFMT, ContainerizedModel
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.container import BmiProxy, ContainerImage, start_container
from ewatercycle.plugins.wflow.forcing import WflowForcing
from ewatercycle.util import CaseConfigParser, get_time, to_absolute_path

logger = logging.getLogger(__name__)


class _SwapXY(BmiProxy):
    """Corrective glasses for Wflow model in container images.

    The models in the images defined in :pt:const:`_version_images` have swapped x and y coordinates.

    At https://bmi.readthedocs.io/en/stable/model_grids.html#model-grids it says that
    that x are columns or longitude and y are rows or latitude.
    While in the image the get_grid_x method returned latitude and get_grid_y method returned longitude.
    """

    def get_grid_x(self, grid: int, x: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_y(grid, x)

    def get_grid_y(self, grid: int, y: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_x(grid, y)


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

    _config: CaseConfigParser = PrivateAttr()
    _work_dir: Path = PrivateAttr()

    @model_validator(mode="after")
    def _initialize_config(self) -> "Wflow":
        """Load config from parameter set and update with forcing info."""
        cfg = CaseConfigParser()
        cfg.read(self.parameter_set.config)

        if self.forcing is not None:
            cfg.set("framework", "netcdfinput", Path(self.forcing.netcdfinput).name)
            cfg.set("inputmapstacks", "Precipitation", self.forcing.Precipitation)
            cfg.set(
                "inputmapstacks",
                "EvapoTranspiration",
                self.forcing.EvapoTranspiration,
            )
            cfg.set("inputmapstacks", "Temperature", self.forcing.Temperature)
            cfg.set("run", "starttime", _iso_to_wflow(self.forcing.start_time))
            cfg.set("run", "endtime", _iso_to_wflow(self.forcing.end_time))
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

        self._config = cfg
        return self

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

    def _make_bmi_instance(self) -> bmipy.Bmi:
        # Override because need to add _SwapXY wrapper
        if self.parameter_set:
            self._additional_input_dirs.append(str(self.parameter_set.directory))
        if self.forcing:
            self._additional_input_dirs.append(str(self.forcing.directory))

        return start_container(
            image=self.bmi_image,
            work_dir=self._cfg_dir,
            input_dirs=self._additional_input_dirs,
            timeout=300,
            wrappers=(_SwapXY, MemoizedBmi, OptionalDestBmi),
        )

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

    @property
    def parameters(self) -> ItemsView[str, Any]:
        return {
            "start_time": _wflow_to_iso(self._config.get("run", "starttime")),
            "end_time": _wflow_to_iso(self._config.get("run", "endtime")),
        }.items()


def _wflow_to_iso(time):
    dt = datetime.datetime.fromisoformat(time)
    return dt.strftime(ISO_TIMEFMT)


def _iso_to_wflow(time):
    dt = get_time(time)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
