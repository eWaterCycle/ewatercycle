"""Utility functions for the eWaterCycle package."""

from collections.abc import Iterable
from configparser import ConfigParser
from datetime import datetime
from importlib.metadata import entry_points, version
from pathlib import Path
from typing import Any

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
) -> tuple[int, int]:
    """Find closest grid cell to a point based on Geographical distances.

    Args:
        grid_longitudes: 1d array of model grid longitudes in degrees
        grid_latitudes: 1d array of model grid latitudes in degrees
        point_longitude: longitude in degrees of target coordinate
        point_latitude: latitude in degrees of target coordinate

    Returns:
        Tuple with first index of closest grid point in the original longitude array
        and second the index of closest grid point in the original latitude array.
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
        msg = f"Point {point_longitude, point_latitude} outside model grid."
        raise ValueError(msg)

    return int(idx_lon), int(idx_lat)


def geographical_distances(
    point_longitude: float,
    point_latitude: float,
    lon_vectors: np.ndarray,
    lat_vectors: np.ndarray,
    radius=6373.0,
) -> np.ndarray:
    """Calculate geographical distances.

    It uses Spherical Earth projected to a plane formula:
    https://en.wikipedia.org/wiki/Geographical_distance

    Args:
        point_longitude: longitude in degrees of target coordinate
        point_latitude: latitude in degrees of target coordinate
        lon_vectors: 1d array of longitudes in degrees
        lat_vectors: 1d array of latitudes in degrees
        radius: Radius of a sphere in km. Default is Earths approximate radius.

    Returns:
        Array of geographical distance of point to all vector members.

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
    if time.tzname() != "UTC":
        msg = (
            "The time is not in UTC. The ISO format for a UTC time "
            "is 'YYYY-MM-DDTHH:MM:SSZ'"
        )
        raise ValueError(msg)
    return time


def get_extents(shapefile: Any, pad=0) -> dict[str, float]:
    """Get lat/lon extents from shapefile and add padding.

    Args:
        shapefile: Path to shapfile
        pad: Optional padding

    Returns:
        Dict with `start_longitude`, `start_latitude`, `end_longitude`, `end_latitude`
    """
    shape = fiona.open(to_absolute_path(shapefile))
    x0, y0, x1, y1 = next(geometry.shape(p["geometry"]).bounds for p in shape)
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


def fit_extents_to_grid(extents, step=0.1, offset=0.05, ndigits=2) -> dict[str, float]:
    """Get lat/lon extents fitted to a grid.

    Args:
        extents: Dict with `start_longitude`, `start_latitude`,
            `end_longitude`, `end_latitude`
        step: Distance between to grid cells
        offset: Offset to pad with after rounding extent to step.
        ndigits: Number of digits to return

    Returns:
        Dict with `start_longitude`, `start_latitude`, `end_longitude`, `end_latitude`
    """

    def fit(v, offset):
        return round((round(v / step) * step) + offset, ndigits)

    return {
        "start_longitude": fit(extents["start_longitude"], -offset),
        "start_latitude": fit(extents["start_latitude"], -offset),
        "end_longitude": fit(extents["end_longitude"], offset),
        "end_latitude": fit(extents["end_latitude"], offset),
    }


def _check_coordinates_line_up(datasets: list[xr.Dataset]):
    # First check that the coordinates all line up before merging.
    tolerance = 1e-7
    for coord in ["lat", "lon"]:
        coords = [ds[coord].to_numpy() for ds in datasets]
        if len({c.size for c in coords}) > 1:
            msg = f"The coordinate '{coord}' is not of the same size in every dataset."
            raise ValueError(msg)
        all_coords = np.array(coords)
        if not np.all((all_coords - all_coords.mean(axis=0)) < tolerance):
            msg = f"Coordinate {coord} deviates more than {tolerance}. Merging failed."
            raise ValueError(msg)


def _move_height_to_attrs(ds: xr.Dataset) -> xr.Dataset:
    data_vars = list(ds.data_vars)
    for bnd in ("lat_bnds", "lon_bnds", "time_bnds"):
        if bnd in data_vars:
            data_vars.remove(bnd)
    if len(data_vars) == 1:
        var = data_vars[0]
    else:
        msg = (
            "More than one variable found in dataset. \n"
            "This routine can only handle a single data variable per dataset\n"
        )
        raise ValueError(msg)

    ds[var].attrs.update(
        {
            "height": float(ds["height"]),
            "height_units": ds["height"].attrs["units"],
        }
    )
    return ds.drop_vars(("height",))


def merge_esvmaltool_datasets(datasets: list[xr.Dataset]) -> xr.Dataset:
    """Merge the separate output datasets from an ESMValTool recipe into one dataset.

    ESMValTool has bad management of floating point precision in coordinates. Every
    CMORized file can have different rounding errors in the values of its coordinates.
    This will prevent easy merging with xarray's open_mfdataset, or combine_by_coords.
    By rounding to the 7th decimal place, more than sufficient precision is preserved
    ('waldo-on-a-page' precision)[1], while solving the floating point inprecision
    issue.

    References:
        [1] Randall Monroe, 2019. xkcd: Coordinate Precision. https://xkcd.com/2170/
    """
    datasets = [ds.copy(deep=True) for ds in datasets]

    _check_coordinates_line_up(datasets)

    removed = {
        "lat_bnds": False,
        "lon_bnds": False,
    }
    for i in range(len(datasets)):
        # Bounds are not aligned, and can be missing in derived vars,
        #  so we remove all except the first lat/lon bounds we encounter.
        for coord in ["lat_bnds", "lon_bnds"]:
            if coord in datasets[i]:
                if removed[coord]:
                    datasets[i] = datasets[i].drop_vars(coord)
                removed[coord] = True

        # xr.align doesn't work for lumped forcing. this works for both lumped and dist:
        for coord in ["lat", "lon"]:
            datasets[i][coord] = datasets[0][coord]

        # the time coordinates are messed up for some files, see:
        #   https://github.com/eWaterCycle/infra/issues/157
        #   the following is a workaround.
        if "time_bnds" in datasets[i] and xr.infer_freq(datasets[i]["time"]) == "D":
            datasets[i]["time"] = datasets[i]["time_bnds"].isel(
                bnds=0
            ) + np.timedelta64(12, "h")
            datasets[i] = datasets[i].drop_vars("time_bnds")

        # A "height" coordinate can be present, which will result in conflicts.
        #   Instead, we move it to the variable's attributes.
        if "height" in datasets[i].variables:
            datasets[i] = _move_height_to_attrs(datasets[i])

    return xr.combine_by_coords(datasets, combine_attrs="drop_conflicts")  # type: ignore[return-value]


def to_absolute_path(
    input_path: str | Path,
    parent: Path | None = None,
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
            except ValueError as e:
                msg = f"Input path {input_path} is not a subpath of parent {parent}"
                raise ValueError(msg) from e

    return pathlike.expanduser().resolve(strict=must_exist)


def reindex(source_file: str, var_name: str, mask_file: str, target_file: str):
    """Conform the input file onto the indexes of a mask file.

    Writing the results to the target file.

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
        indexers = {"lat": mask["lat"].to_numpy(), "lon": mask["lon"].to_numpy()}
    except KeyError:
        try:
            indexers = {
                "latitude": mask["latitude"].to_numpy(),
                "longitude": mask["longitude"].to_numpy(),
            }
        except KeyError:
            try:
                indexers = {"y": mask["y"].to_numpy(), "x": mask["x"].to_numpy()}
            except KeyError as err:
                msg = (
                    "Bad naming of dimensions in source_file and mask_file."
                    "The dimensions should be either (x, y), or (lon, lat), "
                    "or (longitude, latitude)."
                )
                raise ValueError(msg) from err

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
    """Case sensitive config parser.

    See https://stackoverflow.com/questions/1611799/preserve-case-in-configparser
    """

    def optionxform(self, optionstr):
        """Do not convert option names to lowercase."""
        return optionstr


def extract_package_name(value: str) -> str:
    """Extract package name from entry point value.

    E.g. "ewatercycle_HBV.model:HBV" will return
    "ewatercycle_HBV".
    """
    source = value.split(":")[0]
    return source.split(".")[0]


def get_package_versions() -> dict[str, str]:
    """Get the version numbers of the ewatercycle package and its plugins."""
    eps = [ep for ep in entry_points() if "ewatercycle" in ep.group]
    packages = {extract_package_name(ep.value) for ep in eps}

    package_versions = {}
    package_versions["ewatercycle"] = version("ewatercycle")
    package_versions["grpc4bmi"] = version("grpc4bmi")
    package_versions["remotebmi"] = version("remotebmi")
    package_versions.update({pkg: version(pkg) for pkg in packages})
    return package_versions
