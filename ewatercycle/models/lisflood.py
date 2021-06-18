import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Tuple, Union

import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing.lisflood import LisfloodForcing
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import AbstractConfig
from ewatercycle.util import get_time


@dataclass
class LisfloodParameterSet:
    """Input files specific for parameter_set, model boundaries, and configuration template files

    Example:

    .. code-block::

        parameter_set = LisfloodParameterSet(
            PathRoot='/projects/0/wtrcycle/comparison/lisflood_input/Lisflood01degree_masked',
            MaskMap='/projects/0/wtrcycle/comparison/recipes_auxiliary_datasets/LISFLOOD/model_mask.nc',
            config_template='/projects/0/wtrcycle/comparison/lisflood_input/settings_templates/settings_lisflood.xml',
        )
    """
    PathRoot: Path
    """Directory with input files"""
    MaskMap: Path
    """A NetCDF file with model boundaries"""
    config_template: Path
    """Config file used as template for a lisflood run"""

    def __setattr__(self, name: str, value: Union[str, Path]):
        self.__dict__[name] = Path(value).expanduser().resolve()


class Lisflood(AbstractModel):
    """eWaterCycle implementation of Lisflood hydrological model.

    Args:
      version: pick a version for which an ewatercycle grpc4bmi docker image is available.
      parameter_set: LISFLOOD input files. Any included forcing data will be ignored.
      forcing: a LisfloodForcing object.

    Attributes:
        bmi (Bmi): Basic Modeling Interface object

    Example:
        See examples/lisflood.ipynb in `ewatercycle repository <https://github.com/eWaterCycle/ewatercycle>`_
    """
    available_versions = ["20.10"]
    """Versions for which ewatercycle grpc4bmi docker images are available."""

    def __init__(self, version: str, parameter_set: LisfloodParameterSet, forcing: LisfloodForcing):
        """Construct Lisflood model with initial values. """
        super().__init__()
        self.version = version
        self._check_forcing(forcing)
        self.parameter_set = parameter_set
        self.cfg = XmlConfig(self.parameter_set.config_template)

    def _set_docker_image(self):
        images = {
            '20.10': 'ewatercycle/lisflood-grpc4bmi:20.10'
        }
        self.docker_image = images[self.version]

    def _set_singularity_image(self, singularity_dir: Path):
        images = {
            '20.10': 'ewatercycle-lisflood-grpc4bmi_20.10.sif'
        }
        self.singularity_image = singularity_dir / images[self.version]

    def _get_textvar_value(self, name: str):
        for textvar in self.cfg.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]
            if name == textvar_name:
                return textvar.get('value')
        raise KeyError(
            f'Name {name} not found in the config file.'
        )


    # unable to subclass with more specialized arguments so ignore type
    def setup(self,  # type: ignore
              IrrigationEfficiency: str = None,
              start_time: str = None,
              end_time: str = None,
              work_dir: Path = None) -> Tuple[Path, Path]:
        """Configure model run

        1. Creates config file and config directory based on the forcing variables and time range
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            IrrigationEfficiency: Field application irrigation efficiency max 1, ~0.90 drip irrigation, ~0.75 sprinkling
            start_time: Start time of model in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing end time is used.
            work_dir: a working directory given by user or created for user.

        Returns:
            Path to config file and path to config directory
        """

        #TODO forcing can be a part of parameter_set
        work_dir = _generate_workdir(work_dir)
        config_file = self._create_lisflood_config(work_dir, start_time, end_time, IrrigationEfficiency)

        if CFG['container_engine'].lower() == 'singularity':
            self._set_singularity_image(CFG['singularity_dir'])
            self.bmi = BmiClientSingularity(
                image=str(self.singularity_image),
                input_dirs=[
                    str(self.parameter_set.PathRoot),
                    str(self.parameter_set.MaskMap.parent),
                    str(self.forcing_dir)
                ],
                work_dir=str(work_dir),
            )
        elif CFG['container_engine'].lower() == 'docker':
            self._set_docker_image()
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                input_dirs=[
                    str(self.parameter_set.PathRoot),
                    str(self.parameter_set.MaskMap.parent),
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
        if isinstance(forcing, LisfloodForcing):
            self.forcing = forcing
            self.forcing_dir = Path(forcing.directory).expanduser().resolve()
            # convert date_strings to datetime objects
            self._start = get_time(forcing.start_time)
            self._end = get_time(forcing.end_time)
        else:
            raise TypeError(
                f"Unknown forcing type: {forcing}. Please supply a LisfloodForcing object."
            )

    def _create_lisflood_config(self, work_dir: Path, start_time_iso: str = None, end_time_iso: str = None, IrrigationEfficiency: str = None) -> Path:
        """Create lisflood config file"""
        # overwrite dates if given
        if start_time_iso is not None:
            start_time = get_time(start_time_iso)
            if self._start  <= start_time <= self._end:
                self._start = start_time
            else:
                raise ValueError('start_time outside forcing time range')
        if end_time_iso is not None:
            end_time = get_time(end_time_iso)
            if self._start  <= end_time <= self._end:
                self._end = end_time
            else:
                raise ValueError('end_time outside forcing time range')

        settings = {
            "CalendarDayStart": self._start.strftime("%d/%m/%Y 00:00"),
            "StepStart": "1",
            "StepEnd": str((self._end - self._start).days),
            "PathRoot": f"{self.parameter_set.PathRoot}",
            "MaskMap": f"{self.parameter_set.MaskMap}".rstrip('.nc'),
            "PathMeteo": f"{self.forcing_dir}",
            "PathOut": f"{work_dir}",
        }

        if IrrigationEfficiency is not None:
            settings['IrrigationEfficiency'] = IrrigationEfficiency

        for textvar in self.cfg.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]

            # general settings
            for key, value in settings.items():
                if key in textvar_name:
                    textvar.set("value", value)

            # input for lisflood
            if "PrefixPrecipitation" in textvar_name:
                textvar.set("value", self.forcing.PrefixPrecipitation.rstrip('.nc'))
            if "PrefixTavg" in textvar_name:
                textvar.set("value", self.forcing.PrefixTavg.rstrip('.nc'))

            # maps_prefixes dictionary contains lisvap filenames in lisflood config
            maps_prefixes = {
                'E0Maps': {'name': 'PrefixE0', 'value': f"{self.forcing.PrefixE0.rstrip('.nc')}"},
                'ES0Maps': {'name': 'PrefixES0', 'value': f"{self.forcing.PrefixES0.rstrip('.nc')}"},
                'ET0Maps': {'name': 'PrefixET0', 'value': f"{self.forcing.PrefixET0.rstrip('.nc')}"},
            }
            # output of lisvap
            for map_var, prefix in maps_prefixes.items():
                if prefix['name'] in textvar_name:
                    textvar.set("value", prefix['value'])
                if map_var in textvar_name:
                    textvar.set('value', f"$(PathMeteo)/$({prefix['name']})")

        # Write to new setting file
        lisflood_file = work_dir / "lisflood_setting.xml"
        self.cfg.save(str(lisflood_file))
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

    def _coords_to_indices(self, name: str, lat: Iterable[float], lon: Iterable[float]) -> Iterable[int]:
        """Convert lat, lon coordinates into model indices."""
        grid_id = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid_id) # shape returns (len(y), len(x))
        x_model = self.bmi.get_grid_x(grid_id)
        y_model = self.bmi.get_grid_y(grid_id)

        # Create a grid from coordinates
        x_vectors, y_vectors = np.meshgrid(x_model, y_model)

        indices = []
        coord_converted = []
        coord_user = []
        # in lisflood, x corresponds to lon, and y to lat.
        # this might not be the case for other models!
        for x, y in zip(lon, lat):
            # here we use Euclidean distance, but it is not accurate as we have lon/lat in degrees.
            index = ((x_vectors - x) ** 2 + (y_vectors - y) ** 2).argmin()
            indices.append(index)
            idy, idx = np.unravel_index(index, shape)
            coord_converted.append((round(x_model[idx], 4), round(y_model[idy], 4))) # use 4 digits in round
            coord_user.append((round(x, 4), round(y, 4)))
        # Provide feedback
        print(f"Your coordinates {coord_user} match these model coordinates {coord_converted}.")
        return np.array(indices)

    def _indices_to_coords(self, name: str, indices: Iterable[int]) -> Tuple[Iterable[float], Iterable[float]]:
        """Convert index to lat/lon values."""
        grid_id = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid_id) # shape returns (len(y), len(x))
        indices = np.array(indices)
        idy, idx = np.unravel_index(indices, shape)
        x_model = self.bmi.get_grid_x(grid_id)
        y_model = self.bmi.get_grid_y(grid_id)
        lon = []
        lat = []
        # in lisflood, x corresponds to lon, and y to lat.
        # this might not be the case for other models!
        for x, y in zip(idx, idy):
            lon.append(x_model[x])
            lat.append(y_model[y])
        return np.array(lon), np.array(lat)

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the parameters for this model."""
        #TODO fix issue #60
        parameters = [
            ('IrrigationEfficiency', self._get_textvar_value('IrrigationEfficiency')),
            ('PathRoot', str(self.parameter_set.PathRoot)),
            ('MaskMap', str(self.parameter_set.MaskMap.parent)),
            ('config_template', str(self.parameter_set.config_template)),
            ('start_time', self._start.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ('end_time', self._end.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ('forcing directory',  str(self.forcing_dir)),
        ]
        return parameters

# TODO it needs fix regarding forcing
# def reindex_forcings(mask_map: Path, forcing: LisfloodForcing, output_dir: Path = None) -> Path:
#     """Reindex forcing files to match mask map grid

#     Args:
#         mask_map: Path to NetCDF file used a boolean map that defines model boundaries.
#         forcing: Forcing data from ESMValTool
#         output_dir: Directory where to write the re-indexed files, given by user or created for user

#     Returns:
#         Output dir with re-indexed files.
#     """
#     output_dir = _generate_workdir(output_dir)
#     mask = xr.open_dataarray(mask_map).load()
#     data_files = list(forcing.recipe_output.values())[0].data_files
#     for data_file in data_files:
#         dataset = data_file.load_xarray()
#         out_fn = output_dir / data_file.filename.name
#         var_name = list(dataset.data_vars.keys())[0]
#         encoding = {var_name: {"zlib": True, "complevel": 4, "chunksizes": (1,) + dataset[var_name].shape[1:]}}
#         dataset.reindex(
#                     {"lat": mask["lat"], "lon": mask["lon"]},
#                     method="nearest",
#                     tolerance=1e-2,
#                 ).to_netcdf(out_fn, encoding=encoding)
#     return output_dir


def _generate_workdir(work_dir: Path = None) -> Path:
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
