import logging
import textwrap
from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import Tuple, Iterable, Any, TypeVar, Generic, Optional, ClassVar, Set

import numpy as np
import xarray as xr
from cftime import num2date
from basic_modeling_interface import Bmi

from ewatercycle.forcing import DefaultForcing
from ewatercycle.parameter_sets import ParameterSet

logger = logging.getLogger(__name__)

ForcingT = TypeVar('ForcingT', bound=DefaultForcing)


class AbstractModel(Generic[ForcingT], metaclass=ABCMeta):
    """Abstract class of a eWaterCycle model.

    """
    available_versions: ClassVar[Tuple[str, ...]] = tuple()
    """Versions of model that are available in this class"""

    def __init__(self,
                 version: str,
                 parameter_set: ParameterSet = None,
                 forcing: Optional[ForcingT] = None,
                 ):
        self.version = version
        self.parameter_set = parameter_set
        self.forcing: Optional[ForcingT] = forcing
        self._check_version()
        self._check_parameter_set()
        self.bmi: Bmi = None  # bmi should set in setup() before calling its methods
        """Basic Modeling Interface object"""

    def __del__(self):
        try:
            del self.bmi
        except AttributeError:
            pass

    def __str__(self):
        """Nice formatting of model object."""
        return "\n".join(
            [
                f"eWaterCycle {self.__class__.__name__}",
                "-------------------",
                f"Version = {self.version}",
                "Parameter set = ",
                textwrap.indent(str(self.parameter_set), '  '),
                "Forcing = ",
                textwrap.indent(str(self.forcing), '  '),
            ]
        )

    @abstractmethod
    def setup(self, *args, **kwargs) -> Tuple[str, str]:
        """Performs model setup.

        1. Creates config file and config directory
        2. Start bmi container and store as self.bmi

        Args:
            *args: Positional arguments. Sub class should specify each arg.
            **kwargs: Named arguments. Sub class should specify each arg.

        Returns:
            Path to config file and path to config directory
        """

    def initialize(self, config_file: str) -> None:
        """Initialize the model.

        Args:
            config_file: Name of initialization file.

        """
        self.bmi.initialize(config_file)

    def finalize(self) -> None:
        """Perform tear-down tasks for the model."""
        self.bmi.finalize()
        del self.bmi

    def update(self) -> None:
        """Advance model state by one time step."""
        self.bmi.update()

    def get_value(self, name: str) -> np.ndarray:
        """Get a copy of values of the given variable.

        Args:
            name: Name of variable

        """
        return self.bmi.get_value(name)

    def get_value_at_coords(self, name, lat: Iterable[float], lon: Iterable[float]) -> np.ndarray:
        """Get a copy of values of the given variable at lat/lon coordinates.

        Args:
            name: Name of variable
            lat: Latitudinal value
            lon: Longitudinal value

        """
        indices = self._coords_to_indices(name, lat, lon)
        indices = np.array(indices)
        return self.bmi.get_value_at_indices(name, indices)

    def set_value(self, name: str, value: np.ndarray) -> None:
        """Specify a new value for a model variable.

        Args:
            name: Name of variable
            value: The new value for the specified variable.

        """
        self.bmi.set_value(name, value)

    def set_value_at_coords(self, name: str, lat: Iterable[float], lon: Iterable[float], values: np.ndarray) -> None:
        """Specify a new value for a model variable at at lat/lon coordinates.

        Args:
            name: Name of variable
            lat: Latitudinal value
            lon: Longitudinal value
            values: The new value for the specified variable.

        """
        indices = self._coords_to_indices(name, lat, lon)
        indices = np.array(indices)
        self.bmi.set_value_at_indices(name, indices, values)

    def _coords_to_indices(self, name: str, lat: Iterable[float], lon: Iterable[float]) -> Iterable[int]:
        """Converts lat/lon values to index.

        Args:
            lat: Latitudinal value
            lon: Longitudinal value

        """
        raise NotImplementedError("Method to convert from coordinates to model indices not implemented for this model.")

    @abstractmethod
    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Get a copy values of the given variable as xarray DataArray.

        The xarray object also contains coordinate information and additional
        attributes such as the units.

        Args: name: Name of the variable

        """

    @property
    @abstractmethod
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """Default values for the setup() inputs"""

    @property
    def start_time(self) -> float:
        """Start time of the model."""
        return self.bmi.get_start_time()

    @property
    def end_time(self) -> float:
        """End time of the model."""
        return self.bmi.get_end_time()

    @property
    def time(self) -> float:
        """Current time of the model."""
        return self.bmi.get_current_time()

    @property
    def time_units(self) -> str:
        """Time units of the model. Formatted using UDUNITS standard from Unidata."""
        return str(self.bmi.get_time_units())

    @property
    def time_step(self) -> float:
        """Current time step of the model."""
        return self.bmi.get_time_step()

    @property
    def output_var_names(self) -> Iterable[str]:
        """List of a model's output variables."""
        return self.bmi.get_output_var_names()

    @property
    def start_time_as_isostr(self) -> str:
        """Start time of the model.

        In UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        """
        return self.start_time_as_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def end_time_as_isostr(self) -> str:
        """End time of the model.

        In UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        """
        return self.end_time_as_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def time_as_isostr(self) -> str:
        """Current time of the model.

        In UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        """
        return self.time_as_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def start_time_as_datetime(self) -> datetime:
        """Start time of the model as a datetime object.
        """
        return num2date(self.bmi.get_start_time(),
                        self.bmi.get_time_units(),
                        only_use_cftime_datetimes=False)

    @property
    def end_time_as_datetime(self) -> datetime:
        """End time of the model as a datetime object'.
        """
        return num2date(self.bmi.get_end_time(),
                        self.bmi.get_time_units(),
                        only_use_cftime_datetimes=False)

    @property
    def time_as_datetime(self) -> datetime:
        """Current time of the model as a datetime object'.
        """
        return num2date(self.bmi.get_current_time(),
                        self.bmi.get_time_units(),
                        only_use_cftime_datetimes=False)

    def _check_parameter_set(self):
        if not self.parameter_set:
            # Nothing to check
            return
        model_name = self.__class__.__name__.lower()
        if model_name != self.parameter_set.target_model:
            raise ValueError(f'Parameter set has wrong target model, '
                             f'expected {model_name} got {self.parameter_set.target_model}')
        if self.parameter_set.supported_model_versions == set():
            logger.info(f'Model version {self.version} is not explicitly listed in the supported model versions '
                        f'of this parameter set. This can lead to compatibility issues.')
        elif self.version not in self.parameter_set.supported_model_versions:
            raise ValueError(
                f'Parameter set is not compatible with version {self.version} of model, '
                f'parameter set only supports {self.parameter_set.supported_model_versions}')

    def _check_version(self):
        if self.version not in self.available_versions:
            raise ValueError(f'Supplied version {self.version} is not supported by this model. '
                             f'Available versions are {self.available_versions}.')
