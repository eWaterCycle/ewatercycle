"""eWaterCycle wrapper around Marrmot BMI."""

import datetime
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional

import scipy.io as sio
from pydantic import PrivateAttr, root_validator

from ewatercycle.base.model import ISO_TIMEFMT, ContainerizedModel
from ewatercycle.container import ContainerImage
from ewatercycle.plugins.marrmot.forcing import MarrmotForcing
from ewatercycle.util import get_time, to_absolute_path

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
    bmi_image = ContainerImage("ewatercycle/marrmot-grpc4bmi:2020.11")
    version: str = "2020.11"

    _model_name: str = PrivateAttr("m_01_collie1_1p_1s")
    _parameters: List[float] = PrivateAttr([1000.0])
    _store_ini: List[float] = PrivateAttr([900.0])
    _solver: Solver = PrivateAttr(Solver())
    _model_start_time: str | None = PrivateAttr()
    _model_end_time: str | None = PrivateAttr()

    _forcing_filepath: str = PrivateAttr()
    _forcing_start_time: datetime.datetime = PrivateAttr()
    _forcing_end_time: datetime.datetime = PrivateAttr()

    # TODO: move to proper post_init in pydantic v2
    def _post_init(self):
        """Check forcing argument and get path, start and end time of forcing data."""
        if not hasattr(self, "_forcing_start_time"):
            if isinstance(self.forcing, MarrmotForcing):
                forcing_dir = to_absolute_path(self.forcing.directory)
                self._forcing_filepath = str(forcing_dir / self.forcing.forcing_file)
                # convert date_strings to datetime objects
                self._forcing_start_time = get_time(self.forcing.start_time)
                self._forcing_end_time = get_time(self.forcing.end_time)
            else:
                raise TypeError(
                    f"Unknown forcing type: {self.forcing}. Please supply a "
                    " MarrmotForcing object."
                )
            # parse start/end time
            forcing_data = sio.loadmat(self._forcing_filepath, mat_dtype=True)
            if "parameters" in forcing_data:
                print(forcing_data["parameters"][0])
                self._parameters = forcing_data["parameters"][0]
            if "store_ini" in forcing_data:
                self._store_ini = forcing_data["store_ini"][0]
            if "solver" in forcing_data:
                forcing_solver = forcing_data["solver"]
                self._solver = Solver(
                    name=forcing_solver["name"][0][0][0],
                    resnorm_tolerance=forcing_solver["resnorm_tolerance"][0][0][0],
                    resnorm_maxiter=forcing_solver["resnorm_maxiter"][0][0][0],
                )

    def setup(
        self,
        maximum_soil_moisture_storage: Optional[float] = None,
        initial_soil_moisture_storage: Optional[float] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        solver: Optional[Solver] = None,
        **kwargs,
    ) -> tuple[str, str]:
        """Configure model run.

        1. Creates config file and config directory based on the forcing
           variables and time range
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
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

        Returns:
            Path to config file and path to config directory
        """
        self._post_init()

        if maximum_soil_moisture_storage is not None:
            self._parameters = [maximum_soil_moisture_storage]
        if initial_soil_moisture_storage is not None:
            self._store_ini = [initial_soil_moisture_storage]
        if solver is not None:
            self._solver = solver
        self._model_start_time = start_time
        self._model_end_time = end_time

        return super().setup(**kwargs)

    def _make_cfg_file(self, **kwargs) -> Path:
        """Write model configuration file.

        Adds the model parameters to forcing file for the given period and
        writes this information to a model configuration file.

        Args:
            cfg_dir: a run directory given by user or created for user.

        Returns:
            Path for Marrmot config file
        """
        forcing_data = sio.loadmat(self._forcing_filepath, mat_dtype=True)

        # overwrite dates if given
        if self._model_start_time is not None:
            start_time = get_time(self._model_start_time)
            if self._forcing_start_time <= start_time <= self._forcing_end_time:
                forcing_data["time_start"][0][0:6] = [
                    start_time.year,
                    start_time.month,
                    start_time.day,
                    start_time.hour,
                    start_time.minute,
                    start_time.second,
                ]
                self._forcing_start_time = start_time
            else:
                raise ValueError("start_time outside forcing time range")
        if self._model_end_time is not None:
            end_time = get_time(self._model_end_time)
            if self._forcing_start_time <= end_time <= self._forcing_end_time:
                forcing_data["time_end"][0][0:6] = [
                    end_time.year,
                    end_time.month,
                    end_time.day,
                    end_time.hour,
                    end_time.minute,
                    end_time.second,
                ]
                self._forcing_end_time = end_time
            else:
                raise ValueError("end_time outside forcing time range")

        # combine forcing and model parameters
        forcing_data.update(
            model_name=self._model_name,
            parameters=self._parameters,
            solver=asdict(self._solver),
            store_ini=self._store_ini,
        )

        config_file = self._cfg_dir / "marrmot-m01_config.mat"
        sio.savemat(config_file, forcing_data)
        return config_file

    def get_parameters(self) -> Iterable[tuple[str, Any]]:
        """List the parameters for this model."""
        self._post_init()

        return [
            ("maximum_soil_moisture_storage", self._parameters[0]),
            ("initial_soil_moisture_storage", self._store_ini[0]),
            ("solver", self._solver),
            ("start time", self._forcing_start_time.strftime(ISO_TIMEFMT)),
            ("end time", self._forcing_end_time.strftime(ISO_TIMEFMT)),
        ]


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
    bmi_image = ContainerImage("ewatercycle/marrmot-grpc4bmi:2020.11")
    version: str = "2020.11"

    _model_name: str = PrivateAttr("m_14_topmodel_7p_2s")
    _parameters: List[float] = PrivateAttr([1000.0, 0.5, 0.5, 100.0, 0.5, 4.25, 2.5])
    _store_ini: List[float] = PrivateAttr([900.0, 900.0])
    _solver: Solver = PrivateAttr(Solver())
    _model_start_time: str | None = PrivateAttr()
    _model_end_time: str | None = PrivateAttr()

    _forcing_filepath: str = PrivateAttr()
    _forcing_start_time: datetime.datetime = PrivateAttr()
    _forcing_end_time: datetime.datetime = PrivateAttr()

    # TODO: move to post_init in pydantic v2
    def _post_init(self):
        """Check forcing argument and get path, start and end time of forcing data."""
        if not hasattr(self, "_forcing_start_time"):
            if isinstance(self.forcing, MarrmotForcing):
                forcing_dir = to_absolute_path(self.forcing.directory)
                self._forcing_filepath = str(forcing_dir / self.forcing.forcing_file)
                # convert date_strings to datetime objects
                self._forcing_start_time = get_time(self.forcing.start_time)
                self._forcing_end_time = get_time(self.forcing.end_time)
            else:
                raise TypeError(
                    f"Unknown forcing type: {self.forcing}. "
                    "Please supply a MarrmotForcing object."
                )
            # parse start/end time
            forcing_data = sio.loadmat(self._forcing_filepath, mat_dtype=True)
            if "parameters" in forcing_data:
                if len(forcing_data["parameters"]) == len(self._parameters):
                    self._parameters = forcing_data["parameters"]
                else:
                    message = (
                        "The length of parameters in forcing "
                        f"{self._forcing_filepath} does not match "
                        "the length of M14 parameters that is seven."
                    )
                    logger.warning("%s", message)
            if "store_ini" in forcing_data:
                if len(forcing_data["store_ini"]) == len(self._store_ini):
                    self._store_ini = forcing_data["store_ini"]
                else:
                    message = (
                        "The length of initial stores in forcing "
                        f"{self._forcing_filepath} does not match "
                        "the length of M14 iniatial stores that is two."
                    )
                    logger.warning("%s", message)
            if "solver" in forcing_data:
                forcing_solver = forcing_data["solver"]
                self._solver.name = forcing_solver["name"][0][0][0]
                self._solver.resnorm_tolerance = forcing_solver["resnorm_tolerance"][0][
                    0
                ][0]
                self._solver.resnorm_maxiter = forcing_solver["resnorm_maxiter"][0][0][
                    0
                ]

    def setup(
        self,
        maximum_soil_moisture_storage: Optional[float] = None,
        threshold_flow_generation_evap_change: Optional[float] = None,
        leakage_saturated_zone_flow_coefficient: Optional[float] = None,
        zero_deficit_base_flow_speed: Optional[float] = None,
        baseflow_coefficient: Optional[float] = None,
        gamma_distribution_chi_parameter: Optional[float] = None,
        gamma_distribution_phi_parameter: Optional[float] = None,
        initial_upper_zone_storage: Optional[float] = None,
        initial_saturated_zone_storage: Optional[float] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        solver: Optional[Solver] = None,
        **kwargs,
    ) -> tuple[str, str]:
        """Configure model run.

        1. Creates config file and config directory based on the forcing
           variables and time range
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
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

        Returns:
            Path to config file and path to config directory
        """
        self._post_init()

        arguments = vars()
        arguments_subset = {key: arguments[key] for key in M14_PARAMS}
        for index, key in enumerate(M14_PARAMS):
            if arguments_subset[key] is not None:
                self._parameters[index] = arguments_subset[key]
        if initial_upper_zone_storage is not None:
            self._store_ini[0] = initial_upper_zone_storage
        if initial_saturated_zone_storage is not None:
            self._store_ini[1] = initial_saturated_zone_storage
        if solver is not None:
            self._solver = solver
        self._model_start_time = start_time
        self._model_end_time = end_time

        return super().setup(**kwargs)

    def _make_cfg_file(self, **kwargs) -> Path:
        """Write model configuration file.

        Adds the model parameters to forcing file for the given period
        and writes this information to a model configuration file.

        Returns:
            Path for Marrmot config file
        """
        forcing_data = sio.loadmat(self._forcing_filepath, mat_dtype=True)

        # overwrite dates if given
        if self._model_start_time is not None:
            start_time = get_time(self._model_start_time)
            if self._forcing_start_time <= start_time <= self._forcing_end_time:
                forcing_data["time_start"][0][0:6] = [
                    start_time.year,
                    start_time.month,
                    start_time.day,
                    start_time.hour,
                    start_time.minute,
                    start_time.second,
                ]
                self._forcing_start_time = start_time
            else:
                raise ValueError("start_time outside forcing time range")
        if self._model_end_time is not None:
            end_time = get_time(self._model_end_time)
            if self._forcing_start_time <= end_time <= self._forcing_end_time:
                forcing_data["time_end"][0][0:6] = [
                    end_time.year,
                    end_time.month,
                    end_time.day,
                    end_time.hour,
                    end_time.minute,
                    end_time.second,
                ]
                self._forcing_end_time = end_time
            else:
                raise ValueError("end_time outside forcing time range")

        # combine forcing and model parameters
        forcing_data.update(
            model_name=self._model_name,
            parameters=self._parameters,
            solver=asdict(self._solver),
            store_ini=self._store_ini,
        )

        config_file = self._cfg_dir / "marrmot-m14_config.mat"
        sio.savemat(config_file, forcing_data)
        return config_file

    def get_parameters(self) -> Iterable[tuple[str, Any]]:
        """List the parameters for this model."""
        self._post_init()

        pars: List[tuple[str, Any]] = list(zip(M14_PARAMS, self._parameters))
        pars += [
            ("initial_upper_zone_storage", self._store_ini[0]),
            ("initial_saturated_zone_storage", self._store_ini[1]),
            ("solver", self._solver),
            ("start time", self._forcing_start_time.strftime(ISO_TIMEFMT)),
            ("end time", self._forcing_end_time.strftime(ISO_TIMEFMT)),
        ]
        return pars
