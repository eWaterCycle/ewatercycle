from dataclasses import asdict, dataclass
import datetime
from pathlib import Path
from typing import Any, Iterable, List, Tuple
import logging

import numpy as np
import scipy.io as sio
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing._marrmot import MarrmotForcing
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.util import get_time, to_absolute_path

logger = logging.getLogger(__name__)


@dataclass
class Solver:
    """Solver, for current implementations see
    `here <https://github.com/wknoben/MARRMoT/tree/master/MARRMoT/Functions/Time%20stepping>`_.
    """
    name: str = 'createOdeApprox_IE'
    resnorm_tolerance: float = 0.1
    resnorm_maxiter: float = 6.0


def _generate_cfg_dir(cfg_dir: Path = None) -> Path:
    """
    Args:
        cfg_dir: If cfg dir is None or does not exist then create sub-directory in CFG['output_dir']
    """
    if cfg_dir is None:
        scratch_dir = CFG['output_dir']
        # TODO this timestamp isnot safe for parallel processing
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        cfg_dir = to_absolute_path(f'marrmot_{timestamp}', parent=Path(scratch_dir))
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


class MarrmotM01(AbstractModel[MarrmotForcing]):
    """eWaterCycle implementation of Marrmot Collie River 1 (traditional bucket) hydrological model.

    It sets MarrmotM01 parameter with an initial value that is the mean value of the range specfied in `model parameter range file <https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Parameter%20range%20files/m_01_collie1_1p_1s_parameter_ranges.m>`_.

    Args:
        version: pick a version for which an ewatercycle grpc4bmi docker image is available.
        forcing: a MarrmotForcing object.
            If forcing file contains parameter and other settings, those are used and can be changed in :py:meth:`setup`.

    Example:
        See examples/marrmotM01.ipynb in `ewatercycle repository <https://github.com/eWaterCycle/ewatercycle>`_
    """
    model_name = "m_01_collie1_1p_1s"
    """Name of model in Matlab code."""
    available_versions = ("2020.11", )
    """Versions for which ewatercycle grpc4bmi docker images are available."""

    def __init__(self, version: str, forcing: MarrmotForcing):
        """Construct MarrmotM01 with initial values. """
        super().__init__(version, forcing=forcing)
        self._parameters = [1000.0]
        self.store_ini = [900.0]
        self.solver = Solver()
        self._check_forcing(forcing)

        self._set_singularity_image()
        self._set_docker_image()

    def _set_docker_image(self):
        images = {
            '2020.11': 'ewatercycle/marrmot-grpc4bmi:2020.11'
        }
        self.docker_image = images[self.version]

    def _set_singularity_image(self):
        images = {
            '2020.11': 'ewatercycle-marrmot-grpc4bmi_2020.11.sif'
        }
        if CFG.get('singularity_dir'):
            self.singularity_image = CFG['singularity_dir'] / images[self.version]

    # unable to subclass with more specialized arguments so ignore type
    def setup(self,  # type: ignore
              maximum_soil_moisture_storage: float = None,
              initial_soil_moisture_storage: float = None,
              start_time: str = None,
              end_time: str = None,
              solver: Solver = None,
              cfg_dir: str = None) -> Tuple[str, str]:
        """Configure model run.

        1. Creates config file and config directory based on the forcing variables and time range
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            maximum_soil_moisture_storage: in mm. Range is specfied in `model parameter range file <https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Parameter%20range%20files/m_01_collie1_1p_1s_parameter_ranges.m>`_.
            initial_soil_moisture_storage: in mm.
            start_time: Start time of model in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing end time is used.
            solver: Solver settings
            cfg_dir: a run directory given by user or created for user.
        Returns:
            Path to config file and path to config directory
        """
        if maximum_soil_moisture_storage:
            self._parameters = [maximum_soil_moisture_storage]
        if initial_soil_moisture_storage:
            self.store_ini = [initial_soil_moisture_storage]
        if solver:
            self.solver = solver
        cfg_dir_as_path = to_absolute_path(cfg_dir) if cfg_dir else None

        cfg_dir_as_path = _generate_cfg_dir(cfg_dir_as_path)
        config_file = self._create_marrmot_config(cfg_dir_as_path, start_time, end_time)

        if CFG['container_engine'].lower() == 'singularity':
            message = f"The singularity image {self.singularity_image} does not exist."
            assert self.singularity_image.exists(), message
            self.bmi = BmiClientSingularity(
                image=str(self.singularity_image),
                work_dir=str(cfg_dir_as_path),
            )
        elif CFG['container_engine'].lower() == 'docker':
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                work_dir=str(cfg_dir_as_path),
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )
        return str(config_file), str(cfg_dir_as_path)

    def _check_forcing(self, forcing):
        """"Check forcing argument and get path, start and end time of forcing data."""
        if isinstance(forcing, MarrmotForcing):
            forcing_dir = to_absolute_path(forcing.directory)
            self.forcing_file = str(forcing_dir / forcing.forcing_file)
            # convert date_strings to datetime objects
            self.forcing_start_time = get_time(forcing.start_time)
            self.forcing_end_time = get_time(forcing.end_time)
        else:
            raise TypeError(
                f"Unknown forcing type: {forcing}. Please supply a MarrmotForcing object."
            )
        # parse start/end time
        forcing_data = sio.loadmat(self.forcing_file, mat_dtype=True)
        if 'parameters' in forcing_data:
            self._parameters = forcing_data['parameters'][0]
        if 'store_ini' in forcing_data:
            self.store_ini = forcing_data['store_ini'][0]
        if 'solver' in forcing_data:
            forcing_solver = forcing_data['solver']
            self.solver.name = forcing_solver['name'][0][0][0]
            self.solver.resnorm_tolerance = forcing_solver['resnorm_tolerance'][0][0][0]
            self.solver.resnorm_maxiter = forcing_solver['resnorm_maxiter'][0][0][0]

    def _create_marrmot_config(self, cfg_dir: Path, start_time_iso: str = None, end_time_iso: str = None) -> Path:
        """Write model configuration file.

        Adds the model parameters to forcing file for the given period
        and writes this information to a model configuration file.

        Args:
            cfg_dir: a run directory given by user or created for user.
            start_time_iso: Start time of model in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing start time is used.
            end_time_iso: End time of model in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing end time is used.

        Returns:
            Path for Marrmot config file
        """
        forcing_data = sio.loadmat(self.forcing_file, mat_dtype=True)

        # overwrite dates if given
        if start_time_iso is not None:
            start_time = get_time(start_time_iso)
            if self.forcing_start_time <= start_time <= self.forcing_end_time:
                forcing_data['time_start'][0][0:6] = [
                    start_time.year,
                    start_time.month,
                    start_time.day,
                    start_time.hour,
                    start_time.minute,
                    start_time.second,
                ]
                self.forcing_start_time = start_time
            else:
                raise ValueError('start_time outside forcing time range')
        if end_time_iso is not None:
            end_time = get_time(end_time_iso)
            if self.forcing_start_time <= end_time <= self.forcing_end_time:
                forcing_data['time_end'][0][0:6] = [
                    end_time.year,
                    end_time.month,
                    end_time.day,
                    end_time.hour,
                    end_time.minute,
                    end_time.second,
                ]
                self.forcing_end_time = end_time
            else:
                raise ValueError('end_time outside forcing time range')

        # combine forcing and model parameters
        forcing_data.update(
            model_name=self.model_name,
            parameters=self._parameters,
            solver=asdict(self.solver),
            store_ini=self.store_ini,
        )

        config_file = cfg_dir / 'marrmot-m01_config.mat'
        sio.savemat(config_file, forcing_data)
        return config_file

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Return the value as xarray object."""
        marrmot_vars = {'S(t)', 'flux_out_Q', 'flux_out_Ea', 'wb'}
        if name not in marrmot_vars:
            raise NotImplementedError(
                "Variable '{}' is not implemented. "
                "Please choose one of {}.".format(name, marrmot_vars))

        # Get time information
        time_units = self.bmi.get_time_units()
        grid = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid)

        # Extract the data and store it in an xarray DataArray
        return xr.DataArray(
            data=np.reshape(self.bmi.get_value(name), shape),
            coords={
                "longitude": self.bmi.get_grid_x(grid),
                "latitude": self.bmi.get_grid_y(grid),
                "time": num2date(self.bmi.get_current_time(), time_units)
            },
            dims=["latitude", "longitude"],
            name=name,
            attrs={"units": self.bmi.get_var_units(name)},
        )

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the parameters for this model."""
        p = [
            ('maximum_soil_moisture_storage', self._parameters[0]),
            ('initial_soil_moisture_storage', self.store_ini[0]),
            ('solver', self.solver),
            ('start time', self.forcing_start_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ('end time', self.forcing_end_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
        ]
        return p


M14_PARAMS = ('maximum_soil_moisture_storage',
              'threshold_flow_generation_evap_change',
              'leakage_saturated_zone_flow_coefficient',
              'zero_deficit_base_flow_speed',
              'baseflow_coefficient',
              'gamma_distribution_chi_parameter',
              'gamma_distribution_phi_parameter')


class MarrmotM14(AbstractModel[MarrmotForcing]):
    """eWaterCycle implementation of Marrmot Top Model hydrological model.

    It sets MarrmotM14 parameter with an initial value that is the mean value of the range specfied in `model parameter range file <https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Parameter%20range%20files/m_14_topmodel_7p_2s_parameter_ranges.m>`_.

    Args:
        version: pick a version for which an ewatercycle grpc4bmi docker image is available.
        forcing: a MarrmotForcing object.
            If forcing file contains parameter and other settings, those are used and can be changed in :py:meth:`setup`.

    Example:
        See examples/marrmotM14.ipynb in `ewatercycle repository <https://github.com/eWaterCycle/ewatercycle>`_
    """
    model_name = "m_14_topmodel_7p_2s"
    """Name of model in Matlab code."""
    available_versions = ("2020.11", )
    """Versions for which ewatercycle grpc4bmi docker images are available."""

    def __init__(self, version: str, forcing: MarrmotForcing):
        """Construct MarrmotM14 with initial values. """
        super().__init__(version, forcing=forcing)
        self._parameters = [1000.0, 0.5, 0.5, 100.0, 0.5, 4.25, 2.5]
        self.store_ini = [900.0, 900.0]
        self.solver = Solver()
        self._check_forcing(forcing)

        self._set_singularity_image()
        self._set_docker_image()

    def _set_docker_image(self):
        images = {
            '2020.11': 'ewatercycle/marrmot-grpc4bmi:2020.11'
        }
        self.docker_image = images[self.version]

    def _set_singularity_image(self):
        images = {
            '2020.11': 'ewatercycle-marrmot-grpc4bmi_2020.11.sif'
        }
        if CFG.get('singularity_dir'):
            self.singularity_image = CFG['singularity_dir'] / images[self.version]

    # unable to subclass with more specialized arguments so ignore type
    def setup(self,  # type: ignore
              maximum_soil_moisture_storage: float = None,
              threshold_flow_generation_evap_change: float = None,
              leakage_saturated_zone_flow_coefficient: float = None,
              zero_deficit_base_flow_speed: float = None,
              baseflow_coefficient: float = None,
              gamma_distribution_chi_parameter: float = None,
              gamma_distribution_phi_parameter: float = None,
              initial_upper_zone_storage: float = None,
              initial_saturated_zone_storage: float = None,
              start_time: str = None,
              end_time: str = None,
              solver: Solver = None,
              cfg_dir: str = None) -> Tuple[str, str]:
        """Configure model run.

        1. Creates config file and config directory based on the forcing variables and time range
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            maximum_soil_moisture_storage: in mm. Range is specfied in `model parameter range file <https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Parameter%20range%20files/m_01_collie1_1p_1s_parameter_ranges.m>`_.
            threshold_flow_generation_evap_change.
            leakage_saturated_zone_flow_coefficient: in mm/d.
            zero_deficit_base_flow_speed: in mm/d.
            baseflow_coefficient: in mm-1.
            gamma_distribution_chi_parameter.
            gamma_distribution_phi_parameter.
            initial_upper_zone_storage: in mm.
            initial_saturated_zone_storage: in mm.
            start_time: Start time of model in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing end time is used.
            solver: Solver settings
            cfg_dir: a run directory given by user or created for user.
        Returns:
            Path to config file and path to config directory
        """
        arguments = vars()
        arguments_subset = {key: arguments[key] for key in M14_PARAMS}
        for index, key in enumerate(M14_PARAMS):
            if arguments_subset[key] is not None:
                self._parameters[index] = arguments_subset[key]
        if initial_upper_zone_storage:
            self.store_ini[0] = initial_upper_zone_storage
        if initial_saturated_zone_storage:
            self.store_ini[1] = initial_saturated_zone_storage
        if solver:
            self.solver = solver
        cfg_dir_as_path = to_absolute_path(cfg_dir) if cfg_dir else None

        cfg_dir_as_path = _generate_cfg_dir(cfg_dir_as_path)
        config_file = self._create_marrmot_config(cfg_dir_as_path, start_time, end_time)

        if CFG['container_engine'].lower() == 'singularity':
            message = f"The singularity image {self.singularity_image} does not exist."
            assert self.singularity_image.exists(), message
            self.bmi = BmiClientSingularity(
                image=str(self.singularity_image),
                work_dir=str(cfg_dir_as_path),
            )
        elif CFG['container_engine'].lower() == 'docker':
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                work_dir=str(cfg_dir_as_path),
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )
        return str(config_file), str(cfg_dir_as_path)

    def _check_forcing(self, forcing):
        """"Check forcing argument and get path, start and end time of forcing data."""
        if isinstance(forcing, MarrmotForcing):
            forcing_dir = to_absolute_path(forcing.directory)
            self.forcing_file = str(forcing_dir / forcing.forcing_file)
            # convert date_strings to datetime objects
            self.forcing_start_time = get_time(forcing.start_time)
            self.forcing_end_time = get_time(forcing.end_time)
        else:
            raise TypeError(
                f"Unknown forcing type: {forcing}. Please supply a MarrmotForcing object."
            )
        # parse start/end time
        forcing_data = sio.loadmat(self.forcing_file, mat_dtype=True)
        if 'parameters' in forcing_data:
            if len(forcing_data['parameters']) == len(self._parameters):
                self._parameters = forcing_data['parameters']
            else:
                message = f"The length of parameters in forcing {self.forcing_file} does not match the length of M14 parameters that is seven."
                logger.warning("%s", message)
        if 'store_ini' in forcing_data:
            if len(forcing_data['store_ini']) == len(self.store_ini):
                self.store_ini = forcing_data['store_ini']
            else:
                message = f"The length of initial stores in forcing {self.forcing_file} does not match the length of M14 iniatial stores that is two."
                logger.warning("%s", message)
        if 'solver' in forcing_data:
            forcing_solver = forcing_data['solver']
            self.solver.name = forcing_solver['name'][0][0][0]
            self.solver.resnorm_tolerance = forcing_solver['resnorm_tolerance'][0][0][0]
            self.solver.resnorm_maxiter = forcing_solver['resnorm_maxiter'][0][0][0]

    def _create_marrmot_config(self, cfg_dir: Path, start_time_iso: str = None, end_time_iso: str = None) -> Path:
        """Write model configuration file.

        Adds the model parameters to forcing file for the given period
        and writes this information to a model configuration file.

        Args:
            cfg_dir: a run directory given by user or created for user.
            start_time_iso: Start time of model in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing start time is used.
            end_time_iso: End time of model in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing end time is used.

        Returns:
            Path for Marrmot config file
        """
        forcing_data = sio.loadmat(self.forcing_file, mat_dtype=True)

        # overwrite dates if given
        if start_time_iso is not None:
            start_time = get_time(start_time_iso)
            if self.forcing_start_time <= start_time <= self.forcing_end_time:
                forcing_data['time_start'][0][0:6] = [
                    start_time.year,
                    start_time.month,
                    start_time.day,
                    start_time.hour,
                    start_time.minute,
                    start_time.second,
                ]
                self.forcing_start_time = start_time
            else:
                raise ValueError('start_time outside forcing time range')
        if end_time_iso is not None:
            end_time = get_time(end_time_iso)
            if self.forcing_start_time <= end_time <= self.forcing_end_time:
                forcing_data['time_end'][0][0:6] = [
                    end_time.year,
                    end_time.month,
                    end_time.day,
                    end_time.hour,
                    end_time.minute,
                    end_time.second,
                ]
                self.forcing_end_time = end_time
            else:
                raise ValueError('end_time outside forcing time range')

        # combine forcing and model parameters
        forcing_data.update(
            model_name=self.model_name,
            parameters=self._parameters,
            solver=asdict(self.solver),
            store_ini=self.store_ini,
        )

        config_file = cfg_dir / 'marrmot-m14_config.mat'
        sio.savemat(config_file, forcing_data)
        return config_file

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Return the value as xarray object."""
        marrmot_vars = {'S(t)', 'flux_out_Q', 'flux_out_Ea', 'wb'}
        if name not in marrmot_vars:
            raise NotImplementedError(
                "Variable '{}' is not implemented. "
                "Please choose one of {}.".format(name, marrmot_vars))

        # Get time information
        time_units = self.bmi.get_time_units()
        grid = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid)

        # Extract the data and store it in an xarray DataArray
        return xr.DataArray(
            data=np.reshape(self.bmi.get_value(name), shape),
            coords={
                "longitude": self.bmi.get_grid_x(grid),
                "latitude": self.bmi.get_grid_y(grid),
                "time": num2date(self.bmi.get_current_time(), time_units)
            },
            dims=["latitude", "longitude"],
            name=name,
            attrs={"units": self.bmi.get_var_units(name)},
        )

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the parameters for this model."""
        p: List[Tuple[str, Any]] = list(zip(M14_PARAMS, self._parameters))
        p += [
            ('initial_upper_zone_storage', self.store_ini[0]),
            ('initial_saturated_zone_storage', self.store_ini[1]),
            ('solver', self.solver),
            ('start time', self.forcing_start_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ('end time', self.forcing_end_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
        ]
        return p
