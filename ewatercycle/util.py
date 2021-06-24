from typing import Any, Iterable, Tuple, Dict

import fiona
import numpy as np
import xarray as xr
from datetime import datetime

from cftime import num2date
from dateutil.parser import parse
from esmvalcore.experimental.recipe_output import RecipeOutput
from shapely import geometry

def var_to_xarray(model, variable):
    """Get grid properties from model (x = latitude !!)
    could be speedup, lots of bmi calls are done here that dont change between updates

    This function takes an BMI model object, extracts variable and stores it
    as an xarray object. For this to work, the variable does need to have a propper
    setup grid. See the BMI documentation on grids.
    """
    shape = model.get_grid_shape(model.get_var_grid(variable))
    lat = model.get_grid_x(model.get_var_grid(variable))
    lon = model.get_grid_y(model.get_var_grid(variable))
    time = num2date(model.get_current_time(), model.get_time_units())

    # Get model data for variable at current timestep
    data = model.get_value(variable)
    data = np.reshape(data, shape)

    # Create xarray object
    da = xr.DataArray(data,
                      coords={'longitude': lon, 'latitude': lat, 'time': time},
                      dims=['latitude', 'longitude'],
                      name=variable,
                      attrs={'units': model.get_var_units(variable)}
                      )

    # Masked invalid values on return array:
    return da.where(da != -999)


def lat_lon_to_closest_variable_indices(model, variable, lats, lons):
    """Translate lat, lon coordinates into BMI model
    indices, which are used to get and set variable values.
    """
    # get shape of model grid and lat-lon coordinates of grid
    shape = model.bmi.get_grid_shape(model.bmi.get_var_grid(variable))
    lat_model = model.bmi.get_grid_x(model.bmi.get_var_grid(variable))
    lon_model = model.bmi.get_grid_y(model.bmi.get_var_grid(variable))
    nx = len(lat_model)

    # for each coordinate given, determine where in the grid they fall and
    # calculate 1D indices
    if len(lats) == 1:
        idx = np.abs(lat_model - lats).argmin()
        idy = np.abs(lon_model - lons).argmin()
        output = idx + nx * idy
    else:
        output = []
        for [lat, lon] in [lats, lons]:
            idx = np.abs(lat_model - lat).argmin()
            idy = np.abs(lon_model - lon).argmin()
            output.append(idx + nx * idy)

    return np.array(output)


def lat_lon_boundingbox_to_variable_indices(model, variable, lat_min, lat_max, lon_min, lon_max):
    """Translate bounding boxes of lat, lon coordinates into BMI model
    indices, which are used to get and set variable values.
    """
    # get shape of model grid and lat-lon coordinates of grid
    shape = model.get_grid_shape(model.get_var_grid(variable))
    lat_model = model.get_grid_x(model.get_var_grid(variable))
    lon_model = model.get_grid_y(model.get_var_grid(variable))
    nx = len(lat_model)

    idx = [i for i, v in enumerate(lat_model) if ((v > lat_min) and (v < lat_max))]
    idy = [i for i, v in enumerate(lon_model) if ((v > lon_min) and (v < lon_max))]

    output = []
    for x in idx:
        for y in idy:
            output.append(x + nx * y)

    return np.array(output)


def find_closest_point(grid_longitudes: Iterable[float], grid_latitudes: Iterable[float], point_longitude: float, point_latitude: float) -> Tuple[np.ndarray, int]:
    """Find closest grid cell to a point based on Geographical distances.

    It uses Spherical Earth projected to a plane formula:
    https://en.wikipedia.org/wiki/Geographical_distance
    """
    # Create a grid from coordinates
    lon_vectors, lat_vectors = np.meshgrid(grid_longitudes, grid_latitudes)

    dlon = np.radians(lon_vectors - point_longitude)
    dlat = np.radians(lat_vectors - point_latitude)
    latm = np.radians((lat_vectors + point_latitude) / 2)

    # approximate radius of earth in km
    radius = 6373.0
    distances = radius * np.sqrt(dlat ** 2  + (np.cos(latm) * dlon) ** 2)
    index = distances.argmin()
    return distances, index


# TODO rename to to_utcdatetime
def get_time(time_iso: str) -> datetime:
    """Return a datetime in UTC.

    Convert a date string in ISO format to a datetime
    and check if it is in UTC.
    """
    time = parse(time_iso)
    if not time.tzname() == 'UTC':
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
    shape = fiona.open(shapefile)
    x0, y0, x1, y1 = [
        geometry.shape(p["geometry"]).bounds for p in shape
    ][0]
    x0 = round((x0 - pad), 1)
    y0 = round((y0 - pad), 1)
    x1 = round((x1 + pad), 1)
    y1 = round((y1 + pad), 1)
    return {
        'start_longitude': x0,
        'start_latitude': y0,
        'end_longitude': x1,
        'end_latitude': y1,
    }


def data_files_from_recipe_output(recipe_output: RecipeOutput) -> Tuple[str, Dict[str, str]]:
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
        forcing_files[var_name] = data_file.filename.name
    # TODO simplify (recipe_output.location) when next esmvalcore release is made
    directory = str(data_files[0].filename.parent)
    return directory, forcing_files
