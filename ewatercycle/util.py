from os import PathLike
from typing import Any, Iterable, Tuple, Dict
from pathlib import Path

import fiona
import numpy as np
from datetime import datetime

from dateutil.parser import parse
from esmvalcore.experimental.recipe_output import RecipeOutput
from shapely import geometry


def find_closest_point(
    grid_longitudes: Iterable[float],
    grid_latitudes: Iterable[float],
    point_longitude: float,
    point_latitude: float,
) -> Tuple[int, int]:
    """Find closest grid cell to a point based on Geographical distances.

    It uses Spherical Earth projected to a plane formula:
    https://en.wikipedia.org/wiki/Geographical_distance

    args:
        grid_longitudes: 1d array of model grid longitudes in degrees
        grid_latitudes: 1d array of model grid latitudes in degrees
        point_longitude: longitude in degrees of target coordinate
        point_latitude: latitude in degrees of target coordinate

    returns:
        idx_lon: index of closest grid point in the original longitude array
        idx_lat: index of closest grid point in the original latitude array
    """
    # Create a grid from coordinates (shape will be (nlat, nlon))
    lon_vectors, lat_vectors = np.meshgrid(grid_longitudes, grid_latitudes)

    dlon = np.radians(lon_vectors - point_longitude)
    dlat = np.radians(lat_vectors - point_latitude)
    latm = np.radians((lat_vectors + point_latitude) / 2)

    # approximate radius of earth in km
    radius = 6373.0
    distances = radius * np.sqrt(dlat ** 2 + (np.cos(latm) * dlon) ** 2)
    idx_lat, idx_lon = np.unravel_index(distances.argmin(), distances.shape)
    distance = distances.min()

    # Rough check to see if point is in or near the grid
    dx = np.diff(grid_longitudes).max() * 111  # (1 degree ~ 111km)
    dy = np.diff(grid_latitudes).max() * 111  # (1 degree ~ 111km)
    if distance > max(dx, dy) * 2:
        raise ValueError(
            f"Point {point_longitude, point_latitude} outside model grid."
        )

    return idx_lon, idx_lat


# TODO rename to to_utcdatetime
def get_time(time_iso: str) -> datetime:
    """Return a datetime in UTC.

    Convert a date string in ISO format to a datetime
    and check if it is in UTC.
    """
    time = parse(time_iso)
    if not time.tzname() == "UTC":
        raise ValueError(
            f"The time is not in UTC. The ISO format for a UTC time is 'YYYY-MM-DDTHH:MM:SSZ'"
        )
    return time


def get_extents(shapefile: Any, pad=0) -> Dict[str, float]:
    """Get lat/lon extents from shapefile and add padding.

    Args:
        shapefile: Path to shapfile
        pad: Optional padding

    Returns:
        Dict with `start_longitude`, `start_latitude`, `end_longitude`, `end_latitude`
    """
    shape = fiona.open(to_absolute_path(shapefile))
    x0, y0, x1, y1 = [geometry.shape(p["geometry"]).bounds for p in shape][0]
    x0 = round((x0 - pad), 1)
    y0 = round((y0 - pad), 1)
    x1 = round((x1 + pad), 1)
    y1 = round((y1 + pad), 1)
    return {
        "start_longitude": x0,
        "start_latitude": y0,
        "end_longitude": x1,
        "end_latitude": y1,
    }


def data_files_from_recipe_output(
    recipe_output: RecipeOutput,
) -> Tuple[str, Dict[str, str]]:
    """Get data files from a ESMVaLTool recipe output

    Expects first diagnostic task to produce files with single var each.

    Args:
        recipe_output: ESMVaLTool recipe output

    Returns:
        Tuple with directory of files and a
        dict where key is cmor short name and value is relative path to NetCDF file
    """
    data_files = list(recipe_output.values())[0].data_files
    forcing_files = {}
    for data_file in data_files:
        dataset = data_file.load_xarray()
        var_name = list(dataset.data_vars.keys())[0]
        dataset.close()
        forcing_files[var_name] = data_file.path.name
    # TODO simplify (recipe_output.location) when next esmvalcore release is made
    directory = str(data_files[0].path.parent)
    return directory, forcing_files


def to_absolute_path(input_path: str, parent: Path = None, must_exist: bool = False, must_be_in_parent=True) -> Path:
    """Parse input string as :py:class:`pathlib.Path` object.

    Args:
        input_path: Input string path that can be a relative or absolute path.
        parent: Optional parent path of the input path
        must_exist: Optional argument to check if the input path exists.
        must_be_in_parent: Optional argument to check if the input path is subpath of parent path

    Returns:
        The input path that is an absolute path and a :py:class:`pathlib.Path` object.
    """
    pathlike = Path(input_path)
    if parent:
        pathlike = parent.joinpath(pathlike)
        if must_be_in_parent:
            try:
                pathlike.relative_to(parent)
            except ValueError:
                raise ValueError(f"Input path {input_path} is not a subpath of parent {parent}")

    return pathlike.expanduser().resolve(strict=must_exist)
