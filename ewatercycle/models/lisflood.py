import os
import subprocess
import time
from pathlib import Path
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple, Union

import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing.forcing_data import ForcingData
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import AbstractConfig
from ewatercycle.util import convert_timearray_to_datetime, get_time


@dataclass
class LisfloodParameterSet:
    """Input files specific for parameter_set, model boundaries, and configuration template files

    Example:

    .. code-block::

        parameter_set = LisfloodParameterSet(
            root='/projects/0/wtrcycle/comparison/lisflood_input/Lisflood01degree_masked',
            mask='/projects/0/wtrcycle/comparison/recipes_auxiliary_datasets/LISFLOOD/model_mask.nc',
            config_template='/projects/0/wtrcycle/comparison/lisflood_input/settings_templates/settings_lisflood.xml',
        )
    """
    root: Path
    """Directory with input files"""
    mask: Path
    """A NetCDF file with model boundaries"""
    config_template: Path
    """Config file used as template for a lisflood run"""

    def __setattr__(self, name: str, value: Union[str, Path]):
        self.__dict__[name] = Path(value).expanduser().resolve()


# Mapping from lisvap output to lisflood input files. MAPS_PREFIXES dictionary
# contains lisvap filenames in lisvap and lisflood config files and their
# equivalent cmor names
MAPS_PREFIXES = {
    'E0Maps': {'name': 'PrefixE0', 'value': 'e0'},
    'ES0Maps': {'name': 'PrefixES0', 'value': 'es0'},
    'ET0Maps': {'name': 'PrefixET0', 'value': 'et0'},
}


class Lisflood(AbstractModel):
    """eWaterCycle implementation of Lisflood hydrological model.

    Args:
    version: pick a version for which an ewatercycle grpc4bmi docker image is available.
    parameter_set: LISFLOOD input files. Any included forcing data will be ignored.
    forcing: a forcing directory or a forcing data object.

    Attributes:
        bmi (Bmi): Basic Modeling Interface object

    Example:
        See examples/lisflood.ipynb in `ewatercycle repository <https://github.com/eWaterCycle/ewatercycle>`_
    """
    available_versions = ["20.10"]
    """Versions for which ewatercycle grpc4bmi docker images are available."""

    def __init__(self, version: str, parameter_set: LisfloodParameterSet, forcing: Union[str, PathLike]):
        """Construct MarrmotM01 with initial values. """
        super().__init__()
        self.version = version
        self._check_forcing(forcing)
        self.parameter_set = parameter_set
        self._set_singularity_image()
        self._set_docker_image()

    def _set_docker_image(self):
        images = {
            '20.10': 'ewatercycle/lisflood-grpc4bmi:20.10'
        }
        self.docker_image = images[self.version]

    def _set_singularity_image(self):
        images = {
            '20.10': 'ewatercycle-lisflood-grpc4bmi_20.10.sif'
        }
        if CFG.get('singularity_dir'):
            self.singularity_image = CFG['singularity_dir'] / images[self.version]

    # unable to subclass with more specialized arguments so ignore type
    def setup(self,  # type: ignore
              parameter_set: LisfloodParameterSet= None,
              start_time: str = None,
              end_time: str = None,
              work_dir: PathLike = None) -> Tuple[PathLike, PathLike]:
        """Configure model run

        If evaporation files (e0, es0, et0) are not included in the forcing, then :py:meth:`run_lisvap` function should be called before setup.

        1. Creates config file and config directory based on the forcing variables and time range
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            parameter_set: LISFLOOD input files. Any included forcing data will be ignored.
            start_time: Start time of model in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing end time is used.
            work_dir: a working directory given by user or created for user.

        Returns:
            Path to config file and path to config directory
        """
        #TODO forcing can be a part of parameter_set
        #TODO add a start time argument that must be in forcing time range
        if parameter_set:
            self.parameter_set = parameter_set

        work_dir = _generate_workdir(work_dir)
        config_file = self._create_lisflood_config(work_dir, start_time, end_time)

        if CFG['container_engine'].lower() == 'singularity':
            self.bmi = BmiClientSingularity(
                image=str(self.singularity_image),
                input_dirs=[
                    str(self.parameter_set.root),
                    str(self.parameter_set.mask.parent),
                    str(self.forcing_dir)
                ],
                work_dir=str(work_dir),
            )
        elif CFG['container_engine'].lower() == 'docker':
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                input_dirs=[
                    str(self.parameter_set.root),
                    str(self.parameter_set.mask.parent),
                    str(self.forcing_dir)
                ],
                work_dir=str(work_dir),
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )
        return config_file, work_dir

    def _check_forcing(self, forcing):
        """"Check forcing argument and get path, start and end time of forcing data."""
        # TODO check if mask has same grid as forcing files,
        # if not warn users to run reindex_forcings
        if isinstance(forcing, (str, PathLike)):
            self.forcing_dir = Path(forcing).expanduser().resolve()
            self.forcing_files = dict()
            for forcing_file in self.forcing_dir.glob('*.nc'):
                dataset = xr.open_dataset(forcing_file)
                # TODO check dataset was created by ESMValTool, to make sure var names are as expected
                var_name = list(dataset.data_vars.keys())[0]
                self.forcing_files[var_name] = forcing_file.name
                # get start and end date of time dimension
                self.forcing_start_time = convert_timearray_to_datetime(dataset.coords['time'][0])
                self.forcing_end_time = convert_timearray_to_datetime(dataset.coords['time'][-1])
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
                self.forcing_start_time = convert_timearray_to_datetime(dataset.coords['time'][0])
                self.forcing_end_time = convert_timearray_to_datetime(dataset.coords['time'][-1])
        else:
            raise TypeError(
                f"Unknown forcing type: {forcing}. Please supply either a Path or ForcingData object."
            )

    def _create_lisflood_config(self, work_dir: Path, start_time_iso: str = None, end_time_iso: str = None) -> Path:
        """Create lisflood config file"""
        cfg = XmlConfig(self.parameter_set.config_template)

        # overwrite dates if given
        if start_time_iso is not None:
            start_time = get_time(start_time_iso)
            if self.forcing_start_time <= start_time <= self.forcing_end_time:
                self.start_time = start_time
            else:
                raise ValueError('start_time outside forcing time range')
        if end_time_iso is not None:
            end_time = get_time(end_time_iso)
            if self.forcing_start_time <= end_time <= self.forcing_end_time:
                self.end_time = end_time
            else:
                raise ValueError('end_time outside forcing time range')

        settings = {
            "CalendarDayStart": self.start_time.strftime("%d/%m/%Y 00:00"),
            "StepStart": "1",
            "StepEnd": str((self.end_time - self.start_time).days),
            "PathRoot": f"{self.parameter_set.root}",
            "MaskMap": f"{self.parameter_set.mask}".rstrip('.nc'),
            "PathMeteo": f"{self.forcing_dir}",
            "PathOut": f"{work_dir}",
        }

        timestamp = f"{self.start_time.year}_{self.end_time.year}"

        for textvar in cfg.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]

            # general settings
            for key, value in settings.items():
                if key in textvar_name:
                    textvar.set("value", value)

            # input for lisflood
            if "PrefixPrecipitation" in textvar_name:
                textvar.set("value", self.forcing_files['pr'].rstrip('.nc'))
            if "PrefixTavg" in textvar_name:
                textvar.set("value", self.forcing_files['tas'].rstrip('.nc'))

            # output of lisvap
            for map_var, prefix in MAPS_PREFIXES.items():
                if prefix['name'] in textvar_name:
                    textvar.set(
                        "value",
                        f"lisflood_{prefix['value']}_{timestamp}",
                    )
                if map_var in textvar_name:
                    textvar.set('value', f"$(PathMeteo)/$({prefix['name']})")

        # Write to new setting file
        lisflood_file = work_dir / "lisflood_setting.xml"
        cfg.save(str(lisflood_file))
        return lisflood_file

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
        #TODO fix issue #60
        parameters = [
            ('Input files specific for parameter_set', str(self.parameter_set.root)),
            ('model boundaries', str(self.parameter_set.mask.parent)),
            ('configuration template', str(self.parameter_set.config_template)),
            ('start time', self.start_time.isoformat()),
            ('end time', self.end_time.isoformat()),
        ]
        if self.forcing_dir:
            parameters += [
                ('forcing directory',  str(self.forcing_dir)),
            ]

        return parameters


def reindex_forcings(mask_map: PathLike, forcing: ForcingData, output_dir: PathLike = None) -> PathLike:
    """Reindex forcing files to match mask map grid

    Args:
        mask_map: Path to NetCDF file used a boolean map that defines model boundaries.
        forcing: Forcing data from ESMValTool
        output_dir: Directory where to write the re-indexed files, given by user or created for user

    Returns:
        Output dir with re-indexed files.
    """
    output_dir = _generate_workdir(output_dir)
    mask = xr.open_dataarray(mask_map).load()
    data_files = list(forcing.recipe_output.values())[0].data_files
    for data_file in data_files:
        dataset = data_file.load_xarray()
        out_fn = output_dir / data_file.filename.name
        var_name = list(dataset.data_vars.keys())[0]
        encoding = {var_name: {"zlib": True, "complevel": 4, "chunksizes": (1,) + dataset[var_name].shape[1:]}}
        dataset.reindex(
                    {"lat": mask["lat"], "lon": mask["lon"]},
                    method="nearest",
                    tolerance=1e-2,
                ).to_netcdf(out_fn, encoding=encoding)
    return output_dir


def _generate_workdir(work_dir: PathLike = None) -> PathLike:
    """

    Args:
        work_dir: If work dir is None then create sub-directory in CFG['output_dir']

    """
    if work_dir is None:
        scratch_dir = CFG['output_dir']
        # TODO this timestamp isnot safe for parallel processing
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        work_dir = Path(scratch_dir) / f'lisflood_{timestamp}'
        work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


class XmlConfig(AbstractConfig):
    """Config container where config is read/saved in xml format"""

    def __init__(self, source):
        super().__init__(source)
        self.tree = ET.parse(source)
        self.config: ET.Element = self.tree.getroot()
        """XML element used to make changes to the config"""

    def save(self, target):
        self.tree.write(target)
