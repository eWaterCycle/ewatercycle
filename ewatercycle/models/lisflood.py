import datetime
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, Tuple, cast

import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing._lisflood import LisfloodForcing
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parameter_sets import ParameterSet
from ewatercycle.parametersetdb.config import AbstractConfig
from ewatercycle.util import find_closest_point, get_time, to_absolute_path

logger = logging.getLogger(__name__)


class Lisflood(AbstractModel[LisfloodForcing]):
    """eWaterCycle implementation of Lisflood hydrological model.

    Args:
      version: pick a version for which an ewatercycle grpc4bmi docker image is available.
      parameter_set: LISFLOOD input files. Any included forcing data will be ignored.
      forcing: a LisfloodForcing object.

    Example:
        See examples/lisflood.ipynb in `ewatercycle repository <https://github.com/eWaterCycle/ewatercycle>`_
    """

    available_versions = ("20.10",)
    """Versions for which ewatercycle grpc4bmi docker images are available."""

    def __init__(
        self,
        version: str,
        parameter_set: ParameterSet,
        forcing: LisfloodForcing,
    ):
        """Construct Lisflood model with initial values."""
        super().__init__(version, parameter_set, forcing)
        self._check_forcing(forcing)
        self.cfg = XmlConfig(parameter_set.config)

    def _set_docker_image(self):
        images = {"20.10": "ewatercycle/lisflood-grpc4bmi:20.10"}
        self.docker_image = images[self.version]

    def _set_singularity_image(self, singularity_dir: Path):
        images = {"20.10": "ewatercycle-lisflood-grpc4bmi_20.10.sif"}
        self.singularity_image = singularity_dir / images[self.version]

    def _get_textvar_value(self, name: str):
        for textvar in self.cfg.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]
            if name == textvar_name:
                return textvar.get("value")
        raise KeyError(f"Name {name} not found in the config file.")

    # unable to subclass with more specialized arguments so ignore type
    def setup(  # type: ignore
        self,
        IrrigationEfficiency: str = None,
        start_time: str = None,
        end_time: str = None,
        MaskMap: str = None,
        cfg_dir: str = None,
    ) -> Tuple[str, str]:
        """Configure model run

        1. Creates config file and config directory based on the forcing variables and time range
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            IrrigationEfficiency: Field application irrigation efficiency max 1, ~0.90 drip irrigation, ~0.75 sprinkling
            start_time: Start time of model in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'. If not given then forcing end time is used.
            MaskMap: Mask map to use instead of one supplied in parameter set.
                Path to a NetCDF or pcraster file with same dimensions as parameter set map files and a boolean variable.
            cfg_dir: a run directory given by user or created for user.

        Returns:
            Path to config file and path to config directory
        """

        # TODO forcing can be a part of parameter_set
        cfg_dir_as_path = to_absolute_path(cfg_dir) if cfg_dir else None
        cfg_dir_as_path = _generate_workdir(cfg_dir_as_path)
        config_file = self._create_lisflood_config(
            cfg_dir_as_path,
            start_time,
            end_time,
            IrrigationEfficiency,
            MaskMap,
        )

        assert self.parameter_set is not None
        input_dirs = [str(self.parameter_set.directory), str(self.forcing_dir)]
        if MaskMap is not None:
            mask_map = to_absolute_path(MaskMap)
            try:
                mask_map.relative_to(self.parameter_set.directory)
            except ValueError:
                # If not relative add dir
                input_dirs.append(str(mask_map.parent))

        if CFG["container_engine"].lower() == "singularity":
            self._set_singularity_image(CFG["singularity_dir"])
            self.bmi = BmiClientSingularity(
                image=str(self.singularity_image),
                input_dirs=input_dirs,
                work_dir=str(cfg_dir_as_path),
            )
        elif CFG["container_engine"].lower() == "docker":
            self._set_docker_image()
            self.bmi = BmiClientDocker(
                image=self.docker_image,
                image_port=55555,
                input_dirs=input_dirs,
                work_dir=str(cfg_dir_as_path),
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )
        return str(config_file), str(cfg_dir_as_path)

    def _check_forcing(self, forcing):
        """ "Check forcing argument and get path, start and end time of forcing data."""
        # TODO check if mask has same grid as forcing files,
        # if not warn users to run reindex_forcings
        if isinstance(forcing, LisfloodForcing):
            self.forcing = forcing
            self.forcing_dir = to_absolute_path(forcing.directory)
            # convert date_strings to datetime objects
            self._start = get_time(forcing.start_time)
            self._end = get_time(forcing.end_time)
        else:
            raise TypeError(
                f"Unknown forcing type: {forcing}. Please supply a LisfloodForcing object."
            )

    def _create_lisflood_config(
        self,
        cfg_dir: Path,
        start_time_iso: str = None,
        end_time_iso: str = None,
        IrrigationEfficiency: str = None,
        MaskMap: str = None,
    ) -> Path:
        """Create lisflood config file"""
        assert self.parameter_set is not None
        assert self.forcing is not None
        # overwrite dates if given
        if start_time_iso is not None:
            start_time = get_time(start_time_iso)
            if self._start <= start_time <= self._end:
                self._start = start_time
            else:
                raise ValueError("start_time outside forcing time range")
        if end_time_iso is not None:
            end_time = get_time(end_time_iso)
            if self._start <= end_time <= self._end:
                self._end = end_time
            else:
                raise ValueError("end_time outside forcing time range")

        settings = {
            "CalendarDayStart": self._start.strftime("%d/%m/%Y 00:00"),
            "StepStart": "1",
            "StepEnd": str((self._end - self._start).days),
            "PathRoot": str(self.parameter_set.directory),
            "PathMeteo": str(self.forcing_dir),
            "PathOut": str(cfg_dir),
        }

        if IrrigationEfficiency is not None:
            settings["IrrigationEfficiency"] = IrrigationEfficiency
        if MaskMap is not None:
            mask_map = to_absolute_path(MaskMap)
            settings["MaskMap"] = str(mask_map.with_suffix(""))

        for textvar in self.cfg.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]

            # general settings
            for key, value in settings.items():
                if key in textvar_name:
                    textvar.set("value", value)

            # input for lisflood
            if "PrefixPrecipitation" in textvar_name:
                textvar.set(
                    "value", Path(self.forcing.PrefixPrecipitation).stem
                )
            if "PrefixTavg" in textvar_name:
                textvar.set("value", Path(self.forcing.PrefixTavg).stem)

            # maps_prefixes dictionary contains lisvap filenames in lisflood config
            maps_prefixes = {
                "E0Maps": {
                    "name": "PrefixE0",
                    "value": Path(self.forcing.PrefixE0).stem,
                },
                "ES0Maps": {
                    "name": "PrefixES0",
                    "value": Path(self.forcing.PrefixES0).stem,
                },
                "ET0Maps": {
                    "name": "PrefixET0",
                    "value": Path(self.forcing.PrefixET0).stem,
                },
            }
            # output of lisvap
            for map_var, prefix in maps_prefixes.items():
                if prefix["name"] in textvar_name:
                    textvar.set("value", prefix["value"])
                if map_var in textvar_name:
                    textvar.set("value", f"$(PathMeteo)/$({prefix['name']})")

        # Write to new setting file
        lisflood_file = cfg_dir / "lisflood_setting.xml"
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
                "time": num2date(self.bmi.get_current_time(), time_units),
            },
            dims=["latitude", "longitude"],
            name=name,
            attrs={"units": self.bmi.get_var_units(name)},
        )

        return da

    def _coords_to_indices(
        self, name: str, lat: Iterable[float], lon: Iterable[float]
    ) -> Iterable[int]:
        """Converts lat/lon values to index.

        Args:
            lat: Latitudinal value
            lon: Longitudinal value

        """
        grid_id = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid_id)  # (len(y), len(x))
        grid_lon = self.bmi.get_grid_x(grid_id)  # x is longitude
        grid_lat = self.bmi.get_grid_y(grid_id)  # y is latitude

        indices = []
        for point_lon, point_lat in zip(lon, lat):
            idx_lon, idx_lat = find_closest_point(
                grid_lon, grid_lat, point_lon, point_lat
            )
            idx_flat = cast(int, np.ravel_multi_index((idx_lat, idx_lon), shape))
            indices.append(idx_flat)

            logger.debug(
                f"Requested point was lon: {point_lon}, lat: {point_lat}; "
                "closest grid point is "
                f"{grid_lon[idx_lon]:.2f}, {grid_lat[idx_lat]:.2f}."
            )

        return indices

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the parameters for this model."""
        assert self.parameter_set is not None
        assert self.forcing is not None
        # TODO fix issue #60
        parameters = [
            (
                "IrrigationEfficiency",
                self._get_textvar_value("IrrigationEfficiency"),
            ),
            ("MaskMap", self._get_textvar_value("MaskMap")),
            ("start_time", self._start.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("end_time", self._end.strftime("%Y-%m-%dT%H:%M:%SZ")),
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


def _generate_workdir(cfg_dir: Path = None) -> Path:
    """

    Args:
        cfg_dir: If cfg dir is None then create sub-directory in CFG['output_dir']

    """
    if cfg_dir is None:
        scratch_dir = CFG["output_dir"]
        # TODO this timestamp isnot safe for parallel processing
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y%m%d_%H%M%S"
        )
        cfg_dir = to_absolute_path(
            f"lisflood_{timestamp}", parent=Path(scratch_dir)
        )
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


class XmlConfig(AbstractConfig):
    """Config container where config is read/saved in xml format"""

    def __init__(self, source):
        super().__init__(source)
        self.tree = ET.parse(source)
        self.config: ET.Element = self.tree.getroot()
        """XML element used to make changes to the config"""

    def save(self, target):
        self.tree.write(target)
