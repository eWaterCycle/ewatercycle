import numpy as np
import xarray as xr
from datetime import datetime
from dateutil.parser import parse

from ewatercycle.models.abstract import AbstractModel


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
                      coords = {'longitude': lon, 'latitude': lat, 'time': time},
                      dims = ['latitude', 'longitude'],
                      name = variable,
                      attrs = {'units': model.get_var_units(variable)}
                      )

    # Masked invalid values on return array:
    return da.where(da != -999)


def lat_lon_to_closest_variable_indices(model, variable, lats, lons):
    """Translate lat, lon coordinates into BMI model
    indices, which are used to get and set variable values.
    """
    #get shape of model grid and lat-lon coordinates of grid
    shape = model.bmi.get_grid_shape(model.bmi.get_var_grid(variable))
    latModel = model.bmi.get_grid_x(model.bmi.get_var_grid(variable))
    lonModel = model.bmi.get_grid_y(model.bmi.get_var_grid(variable))
    nx = len(latModel)

    #for each coordinate given, determine where in the grid they fall and
    #calculate 1D indeces
    if len(lats) == 1:
        idx = np.abs(latModel - lats).argmin()
        idy = np.abs(lonModel - lons).argmin()
        output = idx+nx*idy
    else:
        output=[]
        for [lat,lon] in [lats, lons]:
            idx = np.abs(latModel - lat).argmin()
            idy = np.abs(lonModel - lon).argmin()
            output.append(idx+nx*idy)

    return np.array(output)


def lat_lon_boundingbox_to_variable_indices(model, variable, latMin, latMax, lonMin, lonMax):
    """Translate bounding boxes of lat, lon coordinates into BMI model
    indices, which are used to get and set variable values.
    """
    # get shape of model grid and lat-lon coordinates of grid
    shape = model.get_grid_shape(model.get_var_grid(variable))
    latModel = model.get_grid_x(model.get_var_grid(variable))
    lonModel = model.get_grid_y(model.get_var_grid(variable))
    nx = len(latModel)

    idx = [i for i,v in enumerate(latModel) if ((v > latMin) and (v < latMax))]
    idy = [i for i,v in enumerate(lonModel) if ((v > lonMin) and (v < lonMax))]

    output = []
    for x in idx:
        for y in idy:
            output.append(x + nx*y)

    return np.array(output)


def convert_timearray_to_datetime(timearray: xr.DataArray) -> datetime:
    """Convert an array of datetimes into an datetime objetct.

    First convert an array of datetimes into a string.
    Then, convert a string in ISO format to a datetime.
    """
    datetime_as_string = np.datetime_as_string(timearray, timezone='UTC')
    return parse(datetime_as_string)


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
