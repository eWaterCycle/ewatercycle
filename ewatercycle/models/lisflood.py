import os
import subprocess
import time
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


@dataclass
class LisfloodParameterSet:
    """Input files specific for parameterset, model boundaries, and configuration template files

    Example:

    .. code-block::

        parameterset = LisfloodParameterSet(
            root=Path('/projects/0/wtrcycle/comparison/lisflood_input/Lisflood01degree_masked'),
            mask=Path('/projects/0/wtrcycle/comparison/recipes_auxiliary_datasets/LISFLOOD/model_mask.nc'),
            config_template=Path('/projects/0/wtrcycle/comparison/lisflood_input/settings_templates/settings_lisflood.xml'),
            lisvap_config_template=Path('/projects/0/wtrcycle/comparison/lisflood_input/settings_templates/settings_lisvap.xml'),
        )
    """
    root: PathLike
    """Directory with input files"""
    mask: Path
    """A NetCDF file with model boundaries"""
    config_template: PathLike
    """Config file used as template for a lisflood run"""
    lisvap_config_template: Optional[PathLike] = None
    """Config file used as template for a lisvap run"""


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

    Attributes:
        bmi (Bmi): Basic Modeling Interface object
        work_dir (PathLike): Working directory for the model where it can read/write files

    Example:
        See examples/lisflood.ipynb in `ewatercycle repository <https://github.com/eWaterCycle/ewatercycle>`_
    """

    # unable to subclass with more specialized arguments so ignore type
    def setup(self,  # type: ignore
              forcing: Union[ForcingData, PathLike],
              parameterset: LisfloodParameterSet,
              work_dir: PathLike = None) -> Tuple[PathLike, PathLike]:
        """Configure model run

        If evaporation files (e0, es0, et0) are not included in the forcing, then :py:meth:`run_lisvap` function should be called before setup.

        1. Creates config file and config directory based on the forcing variables and time range
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            forcing: a forcing directory or a forcing data object.
            parameterset: LISFLOOD input files. Any included forcing data will be ignored.
            work_dir: a working directory given by user or created for user.

        Returns:
            Path to config file and path to config directory
        """
        #TODO forcing can be a part of parameterset
        #TODO add a start time argument that must be in forcing time range
        singularity_image = CFG['lisflood.singularity_image']
        docker_image = CFG['lisflood.docker_image']
        self.work_dir = _generate_workdir(work_dir)
        self._check_forcing(forcing)
        self.parameterset = parameterset

        config_file = self._create_lisflood_config()

        if CFG['container_engine'].lower() == 'singularity':
            self.bmi = BmiClientSingularity(
                image=singularity_image,
                input_dirs=[
                    str(parameterset.root),
                    str(parameterset.mask.parent),
                    str(self.forcing_dir)
                ],
                work_dir=str(self.work_dir),
            )
        elif CFG['container_engine'].lower() == 'docker':
            self.bmi = BmiClientDocker(
                image=docker_image,
                image_port=55555,
                input_dirs=[
                    str(parameterset.root),
                    str(parameterset.mask.parent),
                    str(self.forcing_dir)
                ],
                work_dir=str(self.work_dir),
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )
        return Path(config_file), self.work_dir

    def _check_forcing(self, forcing):
        """"Check forcing argument and get path, start and end time of forcing data."""
        # TODO check if mask has same grid as forcing files,
        # if not warn users to run reindex_forcings
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

    def _create_lisflood_config(self) -> str:
        """Create lisflood config file"""
        cfg = XmlConfig(self.parameterset.config_template)

        settings = {
            "CalendarDayStart": self.start.strftime("%d/%m/%Y 00:00"),
            "StepStart": "1",
            "StepEnd": str((self.end - self.start).days),
            "PathRoot": f"{self.parameterset.root}",
            "MaskMap": f"{self.parameterset.mask}".rstrip('.nc'),
            "PathMeteo": f"{self.forcing_dir}",
            "PathOut": f"{self.work_dir}",
        }

        timestamp = f"{self.start.year}_{self.end.year}"

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
                    textvar.set('value', f"$(PathOut)/$({prefix['name']})")

        # Write to new setting file
        lisflood_file = f"{self.work_dir}/lisflood_setting.xml"
        cfg.save(lisflood_file)
        return lisflood_file

    def _create_lisvap_config(self) -> str:
        """Update lisvap setting file"""
        cfg = XmlConfig(self.parameterset.lisvap_config_template)
        # Make a dictionary for settings
        maps = "/data/lisflood_input/maps_netcdf"
        settings = {
            "CalendarDayStart": self.start.strftime("%d/%m/%Y 00:00"),
            "StepStart": self.start.strftime("%d/%m/%Y 00:00"),
            "StepEnd": self.end.strftime("%d/%m/%Y 00:00"),
            "PathOut": "/output",
            "PathBaseMapsIn": maps,
            "MaskMap": "/data/model_mask",
            "PathMeteoIn": "/data/forcing",
        }

        timestamp = f"{self.start.year}_{self.end.year}"

        # Mapping lisvap input varnames to cmor varnames
        INPUT_NAMES = {
            'TAvgMaps': 'tas',
            'TMaxMaps': 'tasmax',
            'TMinMaps': 'tasmin',
            'EActMaps': 'e',
            'WindMaps': 'sfcWind',
            'RgdMaps': 'rsds',
        }
        for textvar in cfg.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]

            # general settings
            for key, value in settings.items():
                if key in textvar_name:
                    textvar.set("value", value)

            # lisvap input files
            for lisvap_var, cmor_var in INPUT_NAMES.items():
                if lisvap_var in textvar_name:
                    filename = self.forcing_files[cmor_var]
                    textvar.set(
                        "value", f"$(PathMeteoIn)/{filename}",
                    )

            # lisvap output files
            for prefix in MAPS_PREFIXES.values():
                if prefix['name'] in textvar_name:
                    textvar.set(
                        "value",
                        f"lisflood_{prefix['value']}_{timestamp}",
                    )

        # Write to new setting file
        lisvap_file = f"{self.work_dir}/lisvap_setting.xml"
        cfg.save(lisvap_file)
        return lisvap_file

    # TODO take this out of the class?
    def run_lisvap(self, forcing: PathLike) -> Tuple[int, bytes, bytes]:
        """Run lisvap to generate evaporation input files

        Args:
            forcing: Path to forcing data

        Returns:
            Tuple with exit code, stdout and stderr
        """
        singularity_image = CFG['lisflood.singularity_image']
        docker_image = CFG['lisflood.docker_image']
        self._check_forcing(forcing)
        lisvap_file = self._create_lisvap_config()

        mount_points = {
            f'{self.parameterset.root}': '/data/lisflood_input',
            f'{self.parameterset.mask}': '/data/model_mask.nc',
            f'{self.forcing_dir}': '/data/forcing',
            f'{self.work_dir}': '/output',
        }

        if CFG['container_engine'].lower() == 'singularity':
            args = [
                "singularity",
                "exec",
            ]
            args += ["--bind", ','.join([hp + ':' + ip for hp, ip in mount_points.items()])]
            args.append(singularity_image)

        elif CFG['container_engine'].lower() == 'docker':
            args = [
                "docker",
                "run -ti",
            ]
            args += ["--volume", ','.join([hp + ':' + ip for hp, ip in mount_points.items()])]
            args.append(docker_image)

        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )

        lisvap_filename = Path(lisvap_file).name
        args += ['python3', '/opt/Lisvap/src/lisvap1.py', f"/output/{lisvap_filename}"]
        container = subprocess.Popen(args, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        exit_code = container.wait()
        stdout, stderr = container.communicate()
        return exit_code, stdout, stderr

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
        if self.forcing_dir and self.work_dir:
            return {
                'forcing_dir': self.forcing_dir,
                'work_dir': self.work_dir,
            }.items()
        return []


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
