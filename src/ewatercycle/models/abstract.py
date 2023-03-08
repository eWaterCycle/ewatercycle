from datetime import datetime
from importlib.metadata import version
from typing import Any, Iterable, Optional, Protocol, Tuple, runtime_checkable

import numpy as np
import xarray as xr
from basic_modeling_interface import Bmi
from cftime import num2date

from ewatercycle.models.bmi_handles import BmiHandles


@runtime_checkable
class Model(Protocol):
    """Interface for eWaterCycle models."""

    version: str
    bmi: Bmi | None
    parameterset: Optional[Parameterset]
    forcing: Optional[Forcing]
    parameters: Iterable[Tuple[str, Any]]

    def setup(self, *args, **kwargs) -> Tuple[str, str]:
        """Performs model setup.

        1. Creates config file and config directory
        2. Instantiate Bmi object and store in self.bmi.

        Args:
            *args: Positional arguments. Sub class should specify each arg.
            **kwargs: Named arguments. Sub class should specify each arg.

        Returns:
            Path to config file and path to config directory
        """


def check_valid_implementation(model: Model):
    """Check adherence to the eWaterCycle model interface.

    The type annotation in the function signature enables a type check with
    mypy. The function body performs a runtime check, but this is quite shallow.
    """
    assert isinstance(model, Model)

def check_bmi_present_after_setup(model: Model)
    model.setup()
    assert isinstance(model.bmi, Bmi)
    del model


class LocalModel(BmiHandles):

    def __init__(self, bmi: Bmi, **kwargs):
        self.bmi = Bmi()

        # e.g. ewatercycle.model.Bmi --> ewatercycle
        bmi_provider = Bmi.__module__.split('.')[0]
        self.version = version(bmi_provider)

        if "parameterset" in kwargs:
            assert self.version in kwargs["parameterset"].compatible_versions

        if "forcing" in kwargs:
            assert self.version in kwargs["forcing"].compatible_versions

    def _get_bmi(self):
        self.bmi = self._get_bmi()

    def setup(self, **kwargs):
        """Instantiate BMI model from local environment.

        Returns:
            Path to config file and path to temporary working directory.
        """
        work_dir = tempfile.gettempdir()
        config_file = Path(work_dir) / 'defaultmodel_config.yaml'

        with open(config_file, 'w') as file:
            yaml.dump({key: value for key, value in self.parameters}, file)

        return str(config_file), str(work_dir)

class ContainerizedModel(LocalModel):

    def __init__(self, image: str, **kwargs):
        self._image = image

    def from_version(cls, version: str, **kwargs):


    def setup(self, **kwargs):
        config_file, work_dir = super().__init__()
        self.bmi = _start_container(self._image, self.work_dir)

        return str(config_file), str(work_dir)

    def __del__(self):
        """Make sure to destroy container when exiting."""
        try:
            del self.bmi
        except AttributeError:
            pass

    def _start_container(self, image, work_dir):
        # TODO
        return bmi



# available_versions: ClassVar[Tuple[str, ...]] = tuple()
# """Versions of model that are available in this class"""

def _start_container():
    # TODO: implement


if

def _check_parameter_set(self):
    if not self.parameter_set:
        # Nothing to check
        return
    model_name = self.__class__.__name__.lower()
    if model_name != self.parameter_set.target_model:
        raise ValueError(
            f"Parameter set has wrong target model, "
            f"expected {model_name} got {self.parameter_set.target_model}"
        )
    if self.parameter_set.supported_model_versions == set():
        logger.info(
            f"Model version {self.version} is not explicitly listed in the "
            "supported model versions of this parameter set. "
            "This can lead to compatibility issues."
        )
    elif self.version not in self.parameter_set.supported_model_versions:
        raise ValueError(
            "Parameter set is not compatible with version {self.version} of "
            "model, parameter set only supports "
            f"{self.parameter_set.supported_model_versions}."
        )

def _check_version(self):
    if self.version not in self.available_versions:
        raise ValueError(
            f"Supplied version {self.version} is not supported by this model. "
            f"Available versions are {self.available_versions}."
        )



