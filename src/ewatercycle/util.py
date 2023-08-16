from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple, Union

import fiona
import numpy as np
import xarray as xr
from dateutil.parser import parse
from shapely import geometry


def find_closest_point(
    grid_longitudes: Iterable[float],
    grid_latitudes: Iterable[float],
    point_longitude: float,
    point_latitude: float,
) -> Tuple[int, int]:
    """Find closest grid cell to a point based on Geographical distances.

    args:
        grid_longitudes: 1d array of model grid longitudes in degrees
        grid_latitudes: 1d array of model grid latitudes in degrees
        point_longitude: longitude in degrees of target coordinate
        point_latitude: latitude in degrees of target coordinate

    returns:
        idx_lon: index of closest grid point in the original longitude array
        idx_lat: index of closest grid point in the original latitude array
    """
    grid_longitudes_array = np.array(grid_longitudes)
    grid_latitudes_array = np.array(grid_latitudes)

    # Create a grid from coordinates (shape will be (nlat, nlon))
    lon_vectors, lat_vectors = np.meshgrid(grid_longitudes_array, grid_latitudes_array)

    distances = geographical_distances(
        point_longitude, point_latitude, lon_vectors, lat_vectors
    )
    idx_lat, idx_lon = np.unravel_index(distances.argmin(), distances.shape)
    distance = distances.min()

    # Rough check to see if point is in or near the grid
    dx = np.diff(grid_longitudes_array).max() * 111  # (1 degree ~ 111km)
    dy = np.diff(grid_latitudes_array).max() * 111  # (1 degree ~ 111km)
    if distance > max(dx, dy) * 2:
        raise ValueError(f"Point {point_longitude, point_latitude} outside model grid.")

    return int(idx_lon), int(idx_lat)


def geographical_distances(
    point_longitude: float,
    point_latitude: float,
    lon_vectors: np.ndarray,
    lat_vectors: np.ndarray,
    radius=6373.0,
) -> np.ndarray:
    """It uses Spherical Earth projected to a plane formula:
    https://en.wikipedia.org/wiki/Geographical_distance

    args:
        point_longitude: longitude in degrees of target coordinate
        point_latitude: latitude in degrees of target coordinate
        lon_vectors: 1d array of longitudes in degrees
        lat_vectors: 1d array of latitudes in degrees
        radius: Radius of a sphere in km. Default is Earths approximate radius.

    returns:
        distances: array of geographical distance of point to all vector members

    """
    dlon = np.radians(lon_vectors - point_longitude)
    dlat = np.radians(lat_vectors - point_latitude)
    latm = np.radians((lat_vectors + point_latitude) / 2)
    return radius * np.sqrt(dlat**2 + (np.cos(latm) * dlon) ** 2)


# TODO rename to to_utcdatetime
def get_time(time_iso: str) -> datetime:
    """Return a datetime in UTC.

    Convert a date string in ISO format to a datetime
    and check if it is in UTC.
    """
    time = parse(time_iso)
    if not time.tzname() == "UTC":
        raise ValueError(
            "The time is not in UTC. The ISO format for a UTC time "
            "is 'YYYY-MM-DDTHH:MM:SSZ'"
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


def fit_extents_to_grid(extents, step=0.1, offset=0.05, ndigits=2) -> Dict[str, float]:
    """Get lat/lon extents fitted to a grid.

    Args:
        extents: Dict with `start_longitude`, `start_latitude`, `end_longitude`, `end_latitude`
        step: Distance between to grid cells
        offset: Offset to pad with after rounding extent to step.
        ndigits: Number of digits to return

    Returns:
        Dict with `start_longitude`, `start_latitude`, `end_longitude`, `end_latitude`
    """
    fit = lambda v, offset: round((round(v / step) * step) + offset, ndigits)
    return {
        "start_longitude": fit(extents["start_longitude"], -offset),
        "start_latitude": fit(extents["start_latitude"], -offset),
        "end_longitude": fit(extents["end_longitude"], offset),
        "end_latitude": fit(extents["end_latitude"], offset),
    }


def to_absolute_path(
    input_path: Union[str, Path],
    parent: Optional[Path] = None,
    must_exist: bool = False,
    must_be_in_parent=True,
) -> Path:
    """Parse input string as :py:class:`pathlib.Path` object.

    Args:
        input_path: Input string path that can be a relative or absolute path.
        parent: Optional parent path of the input path
        must_exist: Optional argument to check if the input path exists.
        must_be_in_parent: Optional argument to check if the input path is
            subpath of parent path

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
                raise ValueError(
                    f"Input path {input_path} is not a subpath of parent {parent}"
                )

    return pathlike.expanduser().resolve(strict=must_exist)


def reindex(source_file: str, var_name: str, mask_file: str, target_file: str):
    """Conform the input file onto the indexes of a mask file, writing the
    results to the target file.

    Args:
        source_file: Input string path of the file that needs to be reindexed.
        var_name: Variable name in the source_file dataset.
        mask_file: Input string path of the mask file.
        target_file: Output string path of the
        file that is reindexed.
    """
    # TODO this returns PerformanceWarning, see if it can be fixed.
    data = xr.open_dataset(source_file, chunks={"time": 1})
    mask = xr.open_dataset(mask_file)

    try:
        indexers = {"lat": mask["lat"].values, "lon": mask["lon"].values}
    except KeyError:
        try:
            indexers = {
                "latitude": mask["latitude"].values,
                "longitude": mask["longitude"].values,
            }
        except KeyError:
            try:
                indexers = {"y": mask["y"].values, "x": mask["x"].values}
            except KeyError as err:
                raise ValueError(
                    "Bad naming of dimensions in source_file and mask_file."
                    "The dimensions should be either (x, y), or (lon, lat), "
                    "or (longitude, latitude)."
                ) from err

    reindexed_data = data.reindex(
        indexers,
        method="nearest",
        tolerance=1e-2,
    )

    reindexed_data.to_netcdf(
        target_file,
        encoding={
            var_name: {
                "zlib": True,
                "complevel": 4,
                "chunksizes": (1,) + reindexed_data[var_name].shape[1:],
            }
        },
    )


class CaseConfigParser(ConfigParser):
    """Case sensitive config parser
    See https://stackoverflow.com/questions/1611799/preserve-case-in-configparser
    """

    def optionxform(self, optionstr):
        return optionstr
