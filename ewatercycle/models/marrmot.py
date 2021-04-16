import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple, Union
import scipy.io as sio

import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing.forcing_data import ForcingData
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import AbstractConfig


class Marrmot(AbstractModel):
    """eWaterCycle implementation of Marrmot hydrological models.
    Attributes:
        bmi (Bmi): Basic Modeling Interface object
        work_dir (PathLike): Working directory for the model where it can read/write files
    Example:
        See examples/marrmot.ipynb in `ewatercycle repository <https://github.com/eWaterCycle/ewatercycle>`_
    """

    # unable to subclass with more specialized arguments so ignore type
    def setup(self,  # type: ignore
              forcing: Union[ForcingData, PathLike],
              parameters: Iterable,
              work_dir: PathLike = None) -> Tuple[PathLike, PathLike]:
        """Configure model run
        1. Creates config file and config directory based on the forcing variables and time range
        2. Start bmi container and store as :py:attr:`bmi`
        Args:
            forcing: a forcing directory or a forcing data object.
            parameters: Marrmot parameter values.
            work_dir: a working directory given by user or created for user.
        Returns:
            Path to config file and path to config directory
        """
        singularity_image = CFG['marrmot.singularity_image']
        docker_image = CFG['marrmot.docker_image']
        self._check_work_dir(work_dir)
        self._check_forcing(forcing)
        self.parameters = parameters

        config_file = self._create_marrmot_config()

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
        return Path(config_file), self.work_dir

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
            self.forcing_dir = forcing.expanduser().resolve()
            self.forcing_files = dict()
            for forcing_file in self.forcing_dir.glob('*.nc'):
                dataset = xr.open_dataset(forcing_file)
                # TODO check dataset was created by ESMValTool, to make sure var names are as expected
                var_name = list(dataset.data_vars.keys())[0]
                self.forcing_files[var_name] = forcing_file.name
                # get start and end date of time dimension
                # TODO converting numpy.datetime64 to datetime object is ugly, find better way
                self.start = datetime.utcfromtimestamp(dataset.coords['time'][0].values.astype('O') / 1e9)
                self.end = datetime.utcfromtimestamp(dataset.coords['time'][-1].values.astype('O') / 1e9)
        elif isinstance(forcing, ForcingData):
            # key is cmor var name and value is path to NetCDF file
            self.forcing_files = dict()
            data_files = list(forcing.recipe_output.values())[0].data_files
            for data_file in data_files:
                dataset = data_file.load_xarray()
                var_name = list(dataset.data_vars.keys())[0]
                self.forcing_files[var_name] = data_file.filename.name
                self.forcing_dir = data_file.filename.parent
                # get start and end date of time dimension
                # TODO converting numpy.datetime64 to datetime object is ugly, find better way
                self.start = datetime.utcfromtimestamp(dataset.coords['time'][0].values.astype('O') / 1e9)
                self.end = datetime.utcfromtimestamp(dataset.coords['time'][-1].values.astype('O') / 1e9)
        else:
            raise TypeError(
                f"Unknown forcing type: {forcing}. Please supply either a Path or ForcingData object."
            )

    def _create_marrmot_config(self) -> str:
        """Create marrmot config file"""
        cfg = MatConfig(self.parameterset.config_template)

            (parameters,
        period,
        forcing_file_loc,
        config_file_loc ,
        model_name="m_01_collie1_1p_1s",
        solver={
            "name": "createOdeApprox_IE",
            "resnorm_tolerance": 0.1,
            "resnorm_maxiter": 6.0,
            },
        store_ini=1500.0):
        """Write model configuration file.

        Adds the model parameters to forcing file for the given period
        and catchment including the spinup year and writes this information
        to a model configuration file.
        """
        # get the forcing that was created with ESMValTool
        #forcing_file = f"marrmot-m01_{forcing}_{catchment}_{PERIOD['spinup'].year}_{PERIOD['end'].year}.mat"
        forcing_data = sio.loadmat(forcing_file_loc, mat_dtype=True)

        # select forcing data
        forcing_data["time_end"][0][0:3] = [
            period["end"].year,
            period["end"].month,
            period["end"].day,
        ]

        # combine forcing and model parameters
        forcing_data.update(
            model_name=model_name,
            parameters=parameters,
            solver=solver,
            store_ini=store_ini,
        )

        sio.savemat(config_file_loc, forcing_data)
        return marrmot_file

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
                "longitude": self.bmi.get_grid_y(grid),
                "latitude": self.bmi.get_grid_x(grid),
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
        if self.forcing_dir and self.work_dir:
            return {
                'forcing_dir': self.forcing_dir,
                'work_dir': self.work_dir,
            }.items()
        return []


