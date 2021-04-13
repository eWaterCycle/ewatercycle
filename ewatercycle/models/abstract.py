from abc import abstractmethod, ABCMeta
from os import PathLike
from typing import Tuple, Iterable, Any

import numpy as np
from basic_modeling_interface import Bmi


class AbstractModel(metaclass=ABCMeta):
    """Abstract class of a eWaterCycle model.

    Attributes
        bmi (Bmi): Basic Modeling Interface object
    """
    def __init__(self):
        self.bmi: Bmi = None  # bmi should set in setup() before calling its methods

    @abstractmethod
    def setup(self, *args, **kwargs) -> Tuple[PathLike, PathLike]:
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
        # TODO terminate container if running?

    def update(self) -> None:
        """Advance model state by one time step."""
        self.bmi.update()

    def get_value(self, name: str) -> np.ndarray:
        """Get a copy of values of the given variable.

        Args:
            name: Name of variable

        """
        return self.bmi.get_value(name)

    def set_value(self, name: str, value: np.ndarray) -> None:
        """Specify a new value for a model variable.

        Args:
            name: Name of variable
            value: The new value for the specified variable.

        """
        self.bmi.set_value(name, value)

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
