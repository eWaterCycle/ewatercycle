import os
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
# from ewatercycle import CFG
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Tuple, Union, Optional

import xarray as xr
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle.forcing.forcing_data import ForcingData
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import AbstractConfig


@dataclass
class LisfloodParameterSet:
    root: PathLike
    """Directory with input files"""
    mask: PathLike
    """Directory with NetCDF file with model boundaries. NetCDF files should be called model_mask.nc"""
    config_template: PathLike
    """Config file used as template for a lisflood run"""
    lisvap_config_template: Optional[PathLike] = None
    """Config file used as template for a lisvap run"""


# TODO move to docs or example, should not be part of this file as its system specific
parameterset = LisfloodParameterSet(
    # TODO one level down (+ /Lisflood01degree_masked)?
    root=Path('/projects/0/wtrcycle/comparison/lisflood_input'),
    # TODO dir or file (+ /model_mask.nc)?
    mask=Path('/projects/0/wtrcycle/comparison/recipes_auxiliary_datasets/LISFLOOD'),
    config_template=Path('/projects/0/wtrcycle/comparison/lisflood_input/settings_templates/settings_lisflood.xml'),
    lisvap_config_template=Path('/projects/0/wtrcycle/comparison/lisflood_input/settings_templates/settings_lisvap.xml'),
)

# CFG:
CFG = {
    'lisflood.singularity_image': 'ewatercycle-lisflood-grpc4bmi.sif',
    'lisflood.docker_image': 'ewatercycle/lisflood-grpc4bmi:latest',
    # TODO add parameters sets available on system that can be passed to setup()
    'container_engine': 'singularity',
    'scratch_dir': '/scratch/shared/ewatercycle',
}

# mapping lisvap input varnames to cmor varnames
INPUT_NAMES = {
    'TAvgMaps': 'tas',
    'TMaxMaps': 'tasmax',
    'TMinMaps': 'tasmin',
    'EActMaps': 'e',
    'WindMaps': 'sfcWind',
    'RgdMaps': 'rsds',
}

# LISFLOOD settings file reference maps prefixes
# MapsName: {prefix_name, prefix}
MAPS_PREFIXES = {
    'E0Maps': {'name': 'PrefixE0', 'value': 'e0'},
    'ES0Maps': {'name': 'PrefixES0', 'value': 'es0'},
    'ET0Maps': {'name': 'PrefixET0', 'value': 'et0'},
}


class Lisflood(AbstractModel):
    """eWaterCycle implementation of Lisflood hydrological model.

    Attributes
        bmi (Bmi): Basic Modeling Interface object
        parameterset (LisfloodParameterSet): Set of input files for a certain catchment/period
        forcing_dir (PathLike): Directory with meteological input files
    """

    # unable to subclass with more specialized arguments so ignore type
    def setup(self,  # type: ignore
              forcing: Union[ForcingData, PathLike],
              parameterset: LisfloodParameterSet,
              work_dir: PathLike = None) -> Tuple[PathLike, PathLike]:
        """Performs model setup.

        If forcing is missing evaporation files (e0, es0, et0) then the run_lisvap function should be run.

        1. Creates config file and config directory
        2. Start bmi container and store as self.bmi

        Args:
            forcing: a forcing directory or a forcing data object.
            parameterset: LISFLOOD input files. Any included forcing data will be ignored.
            work_dir: a working directory given by user or created for user.

        Returns:
            Path to config file and path to config directory
        """
        singularity_image = CFG['lisflood.singularity_image']
        docker_image = CFG['lisflood.docker_image']
        self._check_work_dir(work_dir)
        self._check_forcing(forcing)
        self.parameterset = parameterset

        config_file = self._create_lisflood_config()

        if CFG['container_engine'].lower() == 'singularity':
            self.bmi = BmiClientSingularity(
                image=singularity_image,
                input_dirs=[
                    str(parameterset.root),
                    str(parameterset.mask),
                    str(self.forcing_dir)
                ],
                work_dir=str(self.work_dir),
            )
        elif CFG['container_engine'].lower() == 'docker':
            self.bmi = BmiClientDocker(
                image=docker_image,
                image_port=55555,
                input_dirs=[
                    parameterset.root,
                    parameterset.mask,
                    self.forcing_dir
                ],
                work_dir=str(self.work_dir),
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )
        return Path(config_file), self.work_dir

    def _check_work_dir(self, work_dir):
        """"""
        self.work_dir = _generate_workdir(work_dir)

    def _check_forcing(self, forcing):
        """"Check forcing argument."""
        # TODO for the future
        if isinstance(forcing, PathLike):
            self.forcing_dir = forcing.expanduser()
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

            # TODO use implementation from wishful notebook
            # self.start = forcing.start_year
            # self.end = forcing.end_year
            # self.dataset = forcing.forcing
            # self.forcing_dir = forcing.location

            # TODO check if mask has same grid as forcing files,
            # if not perform reindex
        else:
            raise TypeError(
                f"Unknown forcing type: {forcing}"
            )

    def _create_lisflood_config(self) -> str:
        """Create lisflood config file"""
        cfg = XmlConfig(self.parameterset.config_template)

        settings = {
            "CalendarDayStart": self.start.strftime("%d/%m/%Y 00:00"),
            "StepStart": "1",
            "StepEnd": str((self.end - self.start).days),
            "PathRoot": f"{self.parameterset.root}/Lisflood01degree_masked",
            "MaskMap": f"{self.parameterset.mask}/model_mask",
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
        # TODO return name
        lisflood_file = f"{self.work_dir}/lisflood_setting_{timestamp}.xml"
        cfg.save(lisflood_file)
        return lisflood_file

    def _create_lisvap_config(self) -> str:
        """Update lisvap setting file"""
        cfg = XmlConfig(self.parameterset.lisvap_config_template)
        # Make a dictionary for settings
        # TODO check if inside directories are needed
        maps = "/data/lisflood_input/Lisflood01degree_masked/maps_netcdf"
        settings = {
            "CalendarDayStart": self.start.strftime("%d/%m/%Y 00:00"),
            "StepStart": self.start.strftime("%d/%m/%Y 00:00"),
            "StepEnd": self.end.strftime("%d/%m/%Y 00:00"),
            "PathOut": "/output",
            "PathBaseMapsIn": maps,
            "MaskMap": "/data/mask/model_mask",
            "PathMeteoIn": "/data/forcing",
        }

        timestamp = f"{self.start.year}_{self.end.year}"

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
        lisvap_file = f"{self.work_dir}/lisvap_setting_{timestamp}.xml"
        cfg.save(lisvap_file)
        return lisvap_file

    # TODO take this out of the class
    def run_lisvap(self, forcing: PathLike) -> Tuple[int, bytes, bytes]:
        """Run lisvap to generate evaporation input files

        Args:
            forcing: Path to re-indexed forcings

        Returns:
            Tuple with exit code, stdout and stderr
        """
        singularity_image = CFG['lisflood.singularity_image']
        docker_image = CFG['lisflood.docker_image']
        self._check_forcing(forcing)
        lisvap_file = self._create_lisvap_config()
        # TODO check if inside directories are needed

        mount_points = {
            f'{self.parameterset.root}': '/data/lisflood_input',
            f'{self.parameterset.mask}': '/data/mask',
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

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the parameters for this model."""
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
        output_dir: Directory where to write the re-indexed files

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
        work_dir: If work dir is None then create sub-directory in CFG['scratch_dir']

    Returns:

    """
    if work_dir is None:
        scratch_dir = CFG['scratch_dir']
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
        self.config = self.tree.getroot()

    def save(self, target):
        self.tree.write(target)
