"""eWaterCycle wrapper around Marrmot BMI."""

import datetime
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import scipy.io as sio
from pydantic import PrivateAttr, model_validator

from ewatercycle.base.model import ISO_TIMEFMT, ContainerizedModel
from ewatercycle.container import ContainerImage
from ewatercycle.plugins.marrmot.forcing import MarrmotForcing
from ewatercycle.util import get_time

logger = logging.getLogger(__name__)


@dataclass
class Solver:
    """Container for properties of the solver.

    For current implementations see `here
    <https://github.com/wknoben/MARRMoT/tree/master/MARRMoT/Functions/Time%20stepping>`_.
    """

    name: str = "createOdeApprox_IE"
    resnorm_tolerance: float = 0.1
    resnorm_maxiter: float = 6.0


def get_marrmot_time(config: dict, which: Literal["start", "end"]) -> str:
    """Get the start/end timestamps from the Marrmott config."""
    yr, mn, dy, hr, mi, sc = (int(el) for el in config[f"time_{which}"][0][0:6])
    dt = datetime.datetime(yr, mn, dy, hr, mi, sc)
    return dt.strftime(ISO_TIMEFMT)


def get_solver(config: dict) -> Solver:
    """Return a Solver object, generated from the configuration info."""
    return Solver(
        name=config["solver"]["name"][0][0][0],
        resnorm_tolerance=config["solver"]["resnorm_tolerance"][0][0][0],
        resnorm_maxiter=config["solver"]["resnorm_maxiter"][0][0][0],
    )


def _update_model_time(
    model: "MarrmotM01 | MarrmotM14",
    time: datetime.datetime,
    which: Literal["start", "end"],
) -> None:
    """Update the model start or end time (in-place)."""
    if time < get_time(model.forcing.start_time) or time > get_time(
        model.forcing.end_time
    ):
        raise ValueError(f"{which}_time outside forcing time range")
    model._config[f"time_{which}"][0][0:6] = [
        time.year,
        time.month,
        time.day,
        time.hour,
        time.minute,
        time.second,
    ]


class MarrmotM01(ContainerizedModel):
    """eWaterCycle implementation of Marrmot Collie River 1 (traditional bucket) model.

    It sets MarrmotM01 parameter with an initial value that is the mean value of
    the range specfied in `model parameter range file
    <https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Parameter%20range%20files/m_01_collie1_1p_1s_parameter_ranges.m>`_.

    Args:
        version: pick a version for which an ewatercycle grpc4bmi docker image
            is available. forcing: a MarrmotForcing object. If forcing file contains
            parameter and other settings, those are used and can be changed in
            :py:meth:`setup`.

    Example:
        See examples/marrmotM01.ipynb in `ewatercycle repository
        <https://github.com/eWaterCycle/ewatercycle>`_
    """

    forcing: MarrmotForcing
    bmi_image: ContainerImage = ContainerImage("ewatercycle/marrmot-grpc4bmi:2020.11")

    _model_name: str = PrivateAttr("m_01_collie1_1p_1s")
    _config: dict = PrivateAttr()

    @model_validator(mode="after")
    def _initialize_config(self) -> "MarrmotM01":
        # TODO: remove assertions after refactoring Forcing
        assert self.forcing.directory is not None
        assert self.forcing.forcing_file is not None

        self._config = sio.loadmat(
            str(self.forcing.directory / self.forcing.forcing_file), mat_dtype=True
        )
        return self

    def _make_cfg_file(self, **kwargs) -> Path:
        """Write model configuration file.

        Adds the model parameters to forcing file for the given period and
        writes this information to a model configuration file.

        Args:
            cfg_dir: a run directory given by user or created for user.

        Returns:
            Path for Marrmot config file
        """
        if "start_time" in kwargs:
            _update_model_time(self, get_time(kwargs["start_time"]), which="start")
        else:
            _update_model_time(self, get_time(self.forcing.start_time), which="start")

        if "end_time" in kwargs:
            _update_model_time(self, get_time(kwargs["end_time"]), which="end")
        else:
            _update_model_time(self, get_time(self.forcing.end_time), which="end")

        self._config.update(model_name=self._model_name)
        if "maximum_soil_moisture_storage" in kwargs:
            self._config.update(parameters=[kwargs["maximum_soil_moisture_storage"]])
        if "initial_soil_moisture_storage" in kwargs:
            self._config.update(store_ini=[kwargs["initial_soil_moisture_storage"]])
        if "solver" in kwargs:
            self._config.update(solver=asdict(kwargs["solver"]))

        config_file = self._cfg_dir / "marrmot-m01_config.mat"
        sio.savemat(config_file, self._config)
        return config_file

    @property
    def parameters(self) -> dict[str, Any]:
        """List MarrmotM01's parameters and their values.

        Model parameters:
            maximum_soil_moisture_storage: in mm. Range is specfied in `model
                parameter range file
                <https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Parameter%20range%20files/m_01_collie1_1p_1s_parameter_ranges.m>`_.
            initial_soil_moisture_storage: in mm.
            start_time: Start time of model in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing start time is
                used.
            end_time: End time of model in  UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing end time is used.
            solver: Solver settings
        """
        return {
            "maximum_soil_moisture_storage": self._config["parameters"][0],
            "initial_soil_moisture_storage": self._config["store_ini"][0],
            "solver": get_solver(self._config),
            "start time": get_marrmot_time(self._config, "start"),
            "end time": get_marrmot_time(self._config, "end"),
        }


M14_PARAMS = (
    "maximum_soil_moisture_storage",
    "threshold_flow_generation_evap_change",
    "leakage_saturated_zone_flow_coefficient",
    "zero_deficit_base_flow_speed",
    "baseflow_coefficient",
    "gamma_distribution_chi_parameter",
    "gamma_distribution_phi_parameter",
)


class MarrmotM14(ContainerizedModel):
    """eWaterCycle implementation of Marrmot Top Model hydrological model.

    It sets MarrmotM14 parameter with an initial value that is the mean value of
    the range specfied in `model parameter range file
    <https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Parameter%20range%20files/m_14_topmodel_7p_2s_parameter_ranges.m>`_.

    Args:
        version: pick a version for which an ewatercycle grpc4bmi docker image
            is available.
        forcing: a MarrmotForcing object.
            If forcing file contains parameter and other settings, those are used
            and can be changed in :py:meth:`setup`.

    Example:
        See examples/marrmotM14.ipynb in `ewatercycle repository
        <https://github.com/eWaterCycle/ewatercycle>`_
    """

    forcing: MarrmotForcing
    bmi_image: ContainerImage = ContainerImage("ewatercycle/marrmot-grpc4bmi:2020.11")

    _model_name: str = PrivateAttr("m_14_topmodel_7p_2s")

    _default_parameters: list[float] = [1000.0, 0.5, 0.5, 100.0, 0.5, 4.25, 2.5]
    _default_store_ini: list[float] = [900.0, 900.0]

    @model_validator(mode="after")
    def _initialize_config(self) -> "MarrmotM14":
        assert self.forcing.directory is not None
        assert self.forcing.forcing_file is not None

        forcing_filepath = str(self.forcing.directory / self.forcing.forcing_file)
        self._config = sio.loadmat(forcing_filepath, mat_dtype=True)

        if "parameters" in self._config:
            if len(self._config["parameters"] != 7):
                self._config["parameters"] = self._default_parameters
                message = (
                    "The length of parameters in forcing "
                    f"{forcing_filepath} does not match "
                    "the length of M14 parameters that is seven."
                )
                logger.warning("%s", message)
                self._config["parameters"] = self._default_parameters
        else:
            self._config["parameters"] = self._default_parameters

        if "store_ini" in self._config:
            if len(self._config["store_ini"]) != 2:
                message = (
                    "The length of initial stores in forcing "
                    f"{forcing_filepath} does not match "
                    "the length of M14 iniatial stores that is two."
                )
                logger.warning("%s", message)
                self._config["store_ini"] = self._default_store_ini
        else:
            self._config["store_ini"] = self._default_store_ini

        return self

    def _make_cfg_file(self, **kwargs) -> Path:
        """Write model configuration file.

        Adds the model parameters to forcing file for the given period and
        writes this information to a model configuration file.

        Args:
            cfg_dir: a run directory given by user or created for user.

        Returns:
            Path for Marrmot config file
        """
        if "start_time" in kwargs:
            _update_model_time(self, get_time(kwargs["start_time"]), which="start")
        else:
            _update_model_time(self, get_time(self.forcing.start_time), which="start")

        if "end_time" in kwargs:
            _update_model_time(self, get_time(kwargs["end_time"]), which="end")
        else:
            _update_model_time(self, get_time(self.forcing.end_time), which="end")

        self._config.update(model_name=self._model_name)
        if "solver" in kwargs:
            self._config.update(solver=asdict(kwargs["solver"]))
        if "initial_upper_zone_storage" in kwargs:
            self._config["store_ini"][0] = kwargs["initial_upper_zone_storage"]
        if "initial_saturated_zone_storage" in kwargs:
            self._config["store_ini"][1] = kwargs["initial_saturated_zone_storage"]

        for index, key in enumerate(M14_PARAMS):
            if key in kwargs:
                self._config["parameters"][index] = kwargs[key]

        config_file = self._cfg_dir / "marrmot-m14_config.mat"
        sio.savemat(config_file, self._config)
        return config_file

    @property
    def parameters(self) -> dict[str, Any]:
        """List the parameters for this model.

        Exposed Marrmot M14 parameters:
            maximum_soil_moisture_storage: in mm. Range is specfied in `model
                parameter range file
                <https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Parameter%20range%20files/m_01_collie1_1p_1s_parameter_ranges.m>`_.
                threshold_flow_generation_evap_change.
            leakage_saturated_zone_flow_coefficient: in mm/d.
            zero_deficit_base_flow_speed: in mm/d.
            baseflow_coefficient: in mm-1.
            gamma_distribution_chi_parameter.
            gamma_distribution_phi_parameter.
            initial_upper_zone_storage: in mm.
            initial_saturated_zone_storage: in mm.
            start_time: Start time of model in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing start time is
                used.
            end_time: End time of model in  UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing end time is used.
                solver: Solver settings
        """
        pars: dict[str, Any] = dict(zip(M14_PARAMS, self._config["parameters"]))
        pars.update(
            {
                "initial_upper_zone_storage": self._config["store_ini"][0],
                "initial_saturated_zone_storage": self._config["store_ini"][1],
                "solver": get_solver(self._config),
                "start time": get_marrmot_time(self._config, "start"),
                "end time": get_marrmot_time(self._config, "end"),
            }
        )
        return pars
