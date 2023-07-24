"""Base classes for eWaterCycle models."""

import abc
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Type, cast

import bmipy
import numpy as np
import pydantic
import xarray as xr
import yaml
from cftime import num2date
from grpc4bmi.bmi_optionaldest import OptionalDestBmi
from grpc4bmi.reserve import reserve_values, reserve_values_at_indices

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.config import CFG
from ewatercycle.container import ContainerImage, start_container
from ewatercycle.util import find_closest_point, to_absolute_path

logger = logging.getLogger(__name__)


ISO_TIMEFMT = r"%Y-%m-%dT%H:%M:%SZ"


class BaseModel(pydantic.BaseModel, abc.ABC):
    """Base functionality for eWaterCycle models.

    Children need to specify how to make their BMI instance: in a container or
    local python environment.
    """

    forcing: DefaultForcing | None
    parameter_set: ParameterSet | None
    parameters: dict[str, Any] = {}

    _bmi: OptionalDestBmi = pydantic.PrivateAttr()

    @abc.abstractmethod
    def _make_bmi_instance(self) -> OptionalDestBmi:
        """Attach a BMI instance to self._bmi."""

    @pydantic.validator("parameter_set")
    def _check_parameter_set(cls, parameter_set):
        model_name = cls.__name__.lower()
        if model_name != parameter_set.target_model:
            raise ValueError(
                f"Parameter set has wrong target model, "
                f"expected {model_name} got {parameter_set.target_model}"
            )

        # TODO: check version as well. Was present before, and can now make use
        # of new ContainerImage class.
        return parameter_set

    def setup(self, *, cfg_dir: str | None = None, **kwargs) -> tuple[str, str]:
        """Perform model setup.

        1. Creates config file and config directory
        2. Start bmi instance and store as self._bmi

        Args:
            cfg_dir: Optionally specify path to use as config dir. Will be
                created if it doesn't exist yet. Behaviour follows PyMT
                documentation
                (https://pymt.readthedocs.io/en/latest/usage.html#model-setup).
                Only difference is that we don't create a temporary directory,
                but rather a time-stamped folder inside
                ewatercycle.CFG['output_dir'].
            *args: Positional arguments. Sub class should specify each arg.
            **kwargs: Named arguments. Sub class should specify each arg.

        Returns:
            Path to config file and path to config directory
        """
        self.cfg_dir: Path = self._make_cfg_dir(cfg_dir)
        self.cfg_file: Path = self._make_cfg_file(**kwargs)
        self._bmi = self._make_bmi_instance()

        return str(self.cfg_file), str(self.cfg_dir)

    def _make_cfg_dir(self, cfg_dir):
        if cfg_dir is not None:
            cfg_dir = to_absolute_path(cfg_dir)
        else:
            tz = timezone.utc
            timestamp = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
            cfg_dir = to_absolute_path(
                f"ewatercycle_{timestamp}", parent=CFG.output_dir
            )

        cfg_dir.mkdir(parents=True, exist_ok=True)

        return cfg_dir

    def _make_cfg_file(self, **kwargs):
        """Create new config file and return its path."""
        cfg_file = self.cfg_dir / "config.yaml"
        self.parameters.update(**kwargs)
        with cfg_file.open(mode="w") as file:
            yaml.dump({k: v for k, v in self.parameters}, file)

        return cfg_file

    def __del__(self):
        """Shutdown bmi before removing self."""
        try:
            del self._bmi
        except AttributeError:
            pass

    def __repr_args__(self):
        """Pass arguments to repr."""
        # Ignore bmi and internal state from subclasses
        return [
            ("parameter_set", self.parameter_set),
            ("forcing", self.forcing),
        ]

    # BMI methods
    def initialize(self, config_file: str) -> None:
        """Initialize the model.

        Args:
            config_file: Name of initialization file.
        """
        self._bmi.initialize(config_file)

    def finalize(self) -> None:
        """Perform tear-down tasks for the model."""
        self._bmi.finalize()
        del self._bmi

    def update(self) -> None:
        """Advance model state by one time step."""
        self._bmi.update()

    def get_value(self, name: str) -> np.ndarray:
        """Get a copy of values of the given variable.

        Args:
            name: Name of variable
        """
        if isinstance(self._bmi, OptionalDestBmi):
            return self._bmi.get_value(name)
        dest = reserve_values(self._bmi, name)
        return self._bmi.get_value(name, dest)

    def get_value_at_coords(
        self, name, lat: Iterable[float], lon: Iterable[float]
    ) -> np.ndarray:
        """Get a copy of values of the given variable at lat/lon coordinates.

        Args:
            name: Name of variable
            lat: Latitudinal value
            lon: Longitudinal value
        """
        indices = self._coords_to_indices(name, lat, lon)
        indices = np.array(indices)
        if isinstance(self._bmi, OptionalDestBmi):
            return self._bmi.get_value_at_indices(name, indices)
        dest = reserve_values_at_indices(self._bmi, name, indices)
        return self._bmi.get_value_at_indices(name, dest, indices)

    def set_value(self, name: str, value: np.ndarray) -> None:
        """Specify a new value for a model variable.

        Args:
            name: Name of variable
            value: The new value for the specified variable.
        """
        self._bmi.set_value(name, value)

    def set_value_at_coords(
        self, name: str, lat: Iterable[float], lon: Iterable[float], values: np.ndarray
    ) -> None:
        """Specify a new value for a model variable at at lat/lon coordinates.

        Args:
            name: Name of variable
            lat: Latitudinal value
            lon: Longitudinal value
            values: The new value for the specified variable.
        """
        indices = self._coords_to_indices(name, lat, lon)
        indices = np.array(indices)
        self._bmi.set_value_at_indices(name, indices, values)

    def _coords_to_indices(
        self, name: str, lat: Iterable[float], lon: Iterable[float]
    ) -> Iterable[int]:
        """Convert lat/lon values to index.

        Args:
            lat: Latitudinal value
            lon: Longitudinal value
        """
        grid_lat, grid_lon, shape = self.get_latlon_grid(name)

        indices = []
        for point_lon, point_lat in zip(lon, lat):
            idx_lon, idx_lat = find_closest_point(
                grid_lon, grid_lat, point_lon, point_lat
            )
            idx_flat = cast(int, np.ravel_multi_index((idx_lat, idx_lon), shape))
            indices.append(idx_flat)

            message = f"""
                Requested point was lon: {point_lon}, lat: {point_lat};
                closest grid point is
                {grid_lon[idx_lon]:.2f}, {grid_lat[idx_lat]:.2f}."""

            logger.debug(message)

        return indices

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Get a copy values of the given variable as xarray DataArray.

        The xarray object also contains coordinate information and additional
        attributes such as the units.

        Args:
            name: Name of the variable
        """
        time_units = self.bmi.get_time_units()
        lat, lon, shape = self.get_latlon_grid(name)

        # Extract the data and store it in an xarray DataArray
        da = xr.DataArray(
            data=np.reshape(self.get_value(name), shape),
            coords={
                "longitude": lon,
                "latitude": lat,
                "time": num2date(self.bmi.get_current_time(), time_units),
            },
            dims=["latitude", "longitude"],
            name=name,
            attrs={"units": self.bmi.get_var_units(name)},
        )

        return da.where(da != -999)

    @property
    def bmi(self) -> bmipy.Bmi:
        """Bmi class wrapped by the model."""
        return self._bmi

    @property
    def start_time(self) -> float:
        """Start time of the model."""
        return self._bmi.get_start_time()

    @property
    def end_time(self) -> float:
        """End time of the model."""
        return self._bmi.get_end_time()

    @property
    def time(self) -> float:
        """Current time of the model."""
        return self._bmi.get_current_time()

    @property
    def time_units(self) -> str:
        """Time units of the model.

        Formatted using UDUNITS standard from Unidata.
        """
        return str(self._bmi.get_time_units())

    @property
    def time_step(self) -> float:
        """Current time step of the model."""
        return self._bmi.get_time_step()

    @property
    def output_var_names(self) -> Iterable[str]:
        """List of a model's output variables."""
        return self._bmi.get_output_var_names()

    @property
    def start_time_as_isostr(self) -> str:
        """Start time of the model.

        In UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        """
        return self.start_time_as_datetime.strftime(ISO_TIMEFMT)

    @property
    def end_time_as_isostr(self) -> str:
        """End time of the model.

        In UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        """
        return self.end_time_as_datetime.strftime(ISO_TIMEFMT)

    @property
    def time_as_isostr(self) -> str:
        """Current time of the model.

        In UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        """
        return self.time_as_datetime.strftime(ISO_TIMEFMT)

    @property
    def start_time_as_datetime(self) -> datetime:
        """Start time of the model as a datetime object."""
        return num2date(
            self._bmi.get_start_time(),
            self._bmi.get_time_units(),
            only_use_cftime_datetimes=False,
        )

    @property
    def end_time_as_datetime(self) -> datetime:
        """End time of the model as a datetime object'."""
        return num2date(
            self._bmi.get_end_time(),
            self._bmi.get_time_units(),
            only_use_cftime_datetimes=False,
        )

    @property
    def time_as_datetime(self) -> datetime:
        """Current time of the model as a datetime object'."""
        return num2date(
            self._bmi.get_current_time(),
            self._bmi.get_time_units(),
            only_use_cftime_datetimes=False,
        )

    def get_latlon_grid(self, name) -> tuple[Any, Any, Any]:
        """Grid latitude, longitude and shape for variable.

        The default implementation takes Bmi's x as longitude and y as latitude.
        See bmi.readthedocs.io/en/stable/model_grids.html#structured-grids.

        Some models may deviate from this default. They can provide their own
        implementation.

        Args:
            name: Name of the variable
        """
        grid_id = self._bmi.get_var_grid(name)
        shape = self._bmi.get_grid_shape(name)
        grid_lon = self._bmi.get_grid_x(grid_id)
        grid_lat = self._bmi.get_grid_y(grid_id)
        return grid_lat, grid_lon, shape


class LocalModel(BaseModel):
    """eWaterCycle model running in a local Python environment.

    Mostly intended for development purposes.
    """

    bmi_class: Type[bmipy.Bmi]

    def _make_bmi_instance(self):
        return OptionalDestBmi(self.bmi_class())


class ContainerizedModel(BaseModel):
    """eWaterCycle model running inside a container.

    This is the recommended method for sharing eWaterCycle models.
    """

    bmi_image: ContainerImage

    _additional_input_dirs: list[str] = pydantic.PrivateAttr()

    def _make_bmi_instance(self) -> bmipy.Bmi:
        self._additional_input_dirs = []
        if self.parameter_set:
            self._additional_input_dirs.append(str(self.parameter_set.directory))
        if self.forcing:
            self._additional_input_dirs.append(str(self.forcing.directory))

        return start_container(
            image=self.bmi_image,
            work_dir=self.cfg_dir,
            input_dirs=self._additional_input_dirs,
            timeout=300,
        )