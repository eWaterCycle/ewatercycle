import os
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from os import PathLike
from pathlib import Path


import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity
from typing import Any, Iterable, Optional, Tuple, Union
import scipy.io as sio

from ewatercycle import CFG
from ewatercycle.forcing.forcing_data import ForcingData
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import AbstractConfig

@dataclass
class Solver:
    name: str = 'createOdeApprox_IE'
    resnorm_tolerance: float = 0.1
    resnorm_maxiter: float = 6.0


class MarrmotM01(AbstractModel):
    """eWaterCycle implementation of Marrmot Collie River 1 (traditional bucket) hydrological model.
    Attributes:
        bmi (Bmi): Basic Modeling Interface object
        work_dir (PathLike): Working directory for the model where it can read/write files
    Example:
        See examples/marrmotM01.ipynb in `ewatercycle repository <https://github.com/eWaterCycle/ewatercycle>`_
    """
    model_name="m_01_collie1_1p_1s"

    def __init__(self):
        super().__init__()
        self.parameters = [1000.0]
        self.store_ini = [900.0]
        self.solver = Solver()

    # unable to subclass with more specialized arguments so ignore type
    def setup(self,  # type: ignore
              forcing: Union[ForcingData, PathLike],
              maximum_soil_moisture_storage: float = 1000.0,
              initial_soil_moisture_storage: float = 900.0,
              start_time: datetime = None,
              end_time: datetime = None,
              solver: Solver = Solver(),
              work_dir: PathLike = None) -> Tuple[PathLike, PathLike]:
        """Configure model run

        1. Creates config file and config directory based on the forcing variables and time range
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            forcing: a forcing file or a forcing data object. See format forcing file in _`model implementation <https://github.com/wknoben/MARRMoT/blob/8f7e80979c2bef941c50f2fb19ce4998e7b273b0/BMI/lib/marrmotBMI_oct.m#L15-L19>`.
            maximum_soil_moisture_storage: in mm. Range is specfied in _`model parameter range file <https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Parameter%20range%20files/m_01_collie1_1p_1s_parameter_ranges.m>`.
            initial_soil_moisture_storage: in mm.
            start_time: Start time of model, if not given then forcing start time is used.
            end_time: End time of model, if not given then forcing end time is used.
            solver: Solver settings
            work_dir: a working directory given by user or created for user.
        Returns:
            Path to config file and path to config directory
        """
        self.parameters = [maximum_soil_moisture_storage]
        self.store_ini = [initial_soil_moisture_storage]
        self.solver = solver
        self.start_time = start_time
        self.end_time = end_time
        self._check_work_dir(work_dir)
        self._check_forcing(forcing)

        config_file = self._create_marrmot_config()

        singularity_image = CFG['marrmot.singularity_image']
        docker_image = CFG['marrmot.docker_image']
        if CFG['container_engine'].lower() == 'singularity':
            self.bmi = BmiClientSingularity(
                image=singularity_image,
                work_dir=str(self.work_dir),
            )
        elif CFG['container_engine'].lower() == 'docker':
            self.bmi = BmiClientDocker(
                image=docker_image,
                image_port=55555,
                work_dir=str(self.work_dir),
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )
        return config_file, self.work_dir

    def _check_work_dir(self, work_dir):
        """
        Args:
            work_dir: If work dir is None then create sub-directory in CFG['output_dir']
        """
        if work_dir is None:
            scratch_dir = CFG['output_dir']
            # TODO this timestamp isnot safe for parallel processing
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            work_dir = Path(scratch_dir) / f'marrmot_{timestamp}'
            work_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir = work_dir

    def _check_forcing(self, forcing):
        """"Check forcing argument and get path, start and end time of forcing data."""
        if isinstance(forcing, PathLike):
            self.forcing_file = forcing
        elif isinstance(forcing, ForcingData):
            self.forcing_file = list(forcing.recipe_output.values())[0].data_files[0].path
        else:
            raise TypeError(
                f"Unknown forcing type: {forcing}. Please supply either a Path or ForcingData object."
            )
        # parse start/end time
        forcing_data = sio.loadmat(self.forcing_file, mat_dtype=True)
        self.forcing_start_time = datetime(*forcing_data["time_start"], tzinfo=timezone.utc)
        self.forcing_end_time = datetime(*forcing_data["time_end"], tzinfo=timezone.utc)

    def _create_marrmot_config(self) -> PathLike:
        """Write model configuration file.

        Adds the model parameters to forcing file for the given period
        and writes this information to a model configuration file.
        """
        # get the forcing that was created with ESMValTool
        forcing_data = sio.loadmat(self.forcing_file, mat_dtype=True)

        # overwrite dates
        if self.start_time is None:
            if self.forcing_start_time <= self.start_time <= self.forcing_end_time:
                forcing_data["time_start"][0:3] = [
                    self.start_time.year,
                    self.start_time.month,
                    self.start_time.day,
                ]
            else:
                raise ValueError('start_time outside forcing time range')
        if self.end_time is None:
            if self.forcing_start_time <= self.end_time <= self.forcing_end_time:
                forcing_data["time_end"][0:3] = [
                    self.end_time.year,
                    self.end_time.month,
                    self.end_time.day,
                ]
            else:
                raise ValueError('start_time outside forcing time range')

        # combine forcing and model parameters
        forcing_data.update(
            model_name=self.model_name,
            parameters=self.parameters,
            solver=asdict(self.solver),
            store_ini=self.store_ini,
        )

        config_file = self.work_dir / 'marrmot-m01_config.mat'
        sio.savemat(config_file, forcing_data)
        return config_file

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Return the value as xarray object."""
        # Get time information
        time_units = self.bmi.get_time_units()
        grid = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid)

        # Extract the data and store it in an xarray DataArray
        da = xr.DataArray(
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
        return da

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the parameters for this model."""
        p = [
            ('maximum_soil_moisture_storage', self.parameters[0]),
            ('initial_soil_moisture_storage', self.store_ini[0]),
            ('solver', self.solver),
        ]
        if self.forcing_file:
            p += [
                ('forcing_file', self.forcing_file),
            ]
        return p
