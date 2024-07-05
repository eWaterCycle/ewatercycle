"""Module to retrieve river discharge data from the USGS REST web service."""
import numpy as np
import pandas as pd
import xarray as xr
from pyoos.collectors.usgs.usgs_rest import UsgsRest
from pyoos.parsers.waterml import WaterML11ToPaegan

from ewatercycle.util import get_time


def _xml_to_xarray(waterml_data: str) -> xr.Dataset:
    # Convert the raw data to an xarray
    data = WaterML11ToPaegan(waterml_data).feature

    # We expect only 1 station
    if len(data.elements) == 0:
        raise ValueError("Data does not contain any station data")

    station = data.elements[0]

    # Unit conversion from cubic feet per second to cubic meter per second
    values = np.array(
        [float(point.members[0]["value"]) / 35.315 for point in station.elements],
        dtype=np.float32,
    )
    # Convert the time to a numpy array of datetime64 without timezone
    times = pd.to_datetime([point.time for point in station.elements]).to_numpy(
        dtype="datetime64[ns]"
    )
    attrs = {"units": "m3/s"}

    # Create the xarray dataset
    ds = xr.Dataset({"streamflow": (["time"], values, attrs)}, coords={"time": times})

    # Set some nice attributes
    ds.attrs["title"] = "USGS Data from streamflow data"
    ds.attrs["station"] = station.name
    ds.attrs["stationid"] = station.get_uid()
    ds.attrs["location"] = (station.location.y, station.location.x)

    return ds


def _download_usgs_data(
    station_id: str,
    start_time: str,
    end_time: str,
):
    discharge_parameter = "00060"
    collector = UsgsRest()
    collector.filter(
        start=get_time(start_time),
        end=get_time(end_time),
        variables=[discharge_parameter],
        features=[station_id],
    )
    return collector.raw()


def get_usgs_data(
    station_id: str,
    start_time: str,
    end_time: str,
) -> xr.Dataset:
    """Get river discharge data from the USGS REST web service.

    See `U.S. Geological Survey Water Services
    <https://waterservices.usgs.gov/>`_ (USGS)

    Args:
        station_id: The station id to get
        start_time: Start time of model in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of model in  UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.

    Returns:
        Xarray dataset with the streamflow data
        with unit and other metadata in the variable and global attributes.

    Examples:

        To get observations from the Little Beaver Creek.

        >>> from ewatercycle.observation.usgs import get_usgs_data
        >>> data = get_usgs_data('03109500', '2000-01-01T00:00:00Z', '2000-12-31T00:00:00Z')
        >>> data
        <xarray.Dataset> Size: 96kB
        Dimensions:     (time: 8032)
        Coordinates:
          * time        (time) datetime64[ns] 64kB 2000-01-04T05:00:00 ... 2000-12-23...
        Data variables:
            streamflow  (time) float32 32kB 8.297 10.42 17.58 ... 8.552 10.65 11.69
        Attributes:
            title:      USGS Data from streamflow data
            station:    Little Beaver Creek near East Liverpool OH
            stationid:  03109500
            location:   (np.float64(40.6758974), np.float64(-80.5406244))
    """  # noqa: E501
    wml_data = _download_usgs_data(station_id, start_time, end_time)
    return _xml_to_xarray(wml_data)
