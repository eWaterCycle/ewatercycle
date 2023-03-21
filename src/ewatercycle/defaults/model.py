"""Abstract class of a eWaterCycle model."""
import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Iterable, Optional, Tuple, Type

from bmipy import Bmi
from pydantic import BaseModel

from ewatercycle.forcing._default import DefaultForcing
from ewatercycle.defaults.bmi_handles import BmiHandles
from ewatercycle.parameter_set import ParameterSet

logger = logging.getLogger(__name__)


class AbstractModel(BaseModel, ABC):
    """Abstract class of a eWaterCycle model."""

    version: str
    bmi: Optional[
        Type[Bmi]
    ] = None  # bmi should set in setup() before calling its methods
    parameter_set: Optional[ParameterSet] = None
    forcing: Optional[Type[DefaultForcing]] = None
    parameters: Iterable[Tuple[str, Any]] = ()

    available_versions: ClassVar[Tuple[str, ...]] = tuple()
    """Versions of model that are available in this class"""

    # self._check_version()  # TODO: add validator
    # self._check_parameter_set()  # TODO: add validator

    def __del__(self):
        try:
            del self.bmi
        except AttributeError:
            pass

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


class DefaultModel(AbstractModel, BmiHandles):
    """Default implementation for ewatercycle models."""


# def _check_parameter_set(self):
#     if not self.parameter_set:
#         # Nothing to check
#         return
#     model_name = self.__class__.__name__.lower()
#     if model_name != self.parameter_set.target_model:
#         raise ValueError(
#             f"Parameter set has wrong target model, "
#             f"expected {model_name} got {self.parameter_set.target_model}"
#         )
#     if self.parameter_set.supported_model_versions == set():
#         logger.info(
#             f"Model version {self.version} is not explicitly listed in the "
#             "supported model versions of this parameter set. "
#             "This can lead to compatibility issues."
#         )
#     elif self.version not in self.parameter_set.supported_model_versions:
#         raise ValueError(
#             "Parameter set is not compatible with version {self.version} of "
#             "model, parameter set only supports "
#             f"{self.parameter_set.supported_model_versions}."
#         )

# def _check_version(self):
#     if self.version not in self.available_versions:
#         raise ValueError(
#             f"Supplied version {self.version} is not supported by this model. "
#             f"Available versions are {self.available_versions}."
#         )
