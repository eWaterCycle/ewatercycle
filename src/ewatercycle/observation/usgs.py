from datetime import datetime

import numpy as np
import pandas as pd
import xarray as xr
from pyoos.collectors.usgs.usgs_rest import UsgsRest
from pyoos.parsers.waterml import WaterML11ToPaegan


def get_usgs_data(
    station_id: str, start_date: str, end_date: str, parameter: str = "00060"
) -> xr.Dataset:
    """Get river discharge data from the USGS REST web service.

    See `U.S. Geological Survey Water Services
    <https://waterservices.usgs.gov/>`_ (USGS)

    Args:
        station_id: The station id to get
        start_date: String for start date in the format: 'YYYY-MM-dd', e.g. '1980-01-01'
        end_date: String for start date in the format: 'YYYY-MM-dd', e.g. '2018-12-31'
        parameter: The parameter code to get, e.g. ('00060') discharge, cubic feet per second

    Returns:
        Xarray dataset with the streamflow data

    Examples:

    >>> from ewatercycle.observation.usgs import get_usgs_data
    >>> data = get_usgs_data('03109500', '2000-01-01', '2000-12-31')
    >>> data
        <xarray.Dataset>
        Dimensions:     (time: 8032)
        Coordinates:
          * time        (time) datetime64[ns] 2000-01-04T05:00:00 ... 2000-12-23T04:00:00
        Data variables:
            Streamflow  (time) float32 8.296758 10.420501 ... 10.647034 11.694747
        Attributes:
            title:      USGS Data from streamflow data
            station:    Little Beaver Creek near East Liverpool OH
            stationid:  03109500
            location:   (40.6758974, -80.5406244)
    """  # noqa: E501

    collector = UsgsRest()
    collector.filter(
        start=datetime.strptime(start_date, "%Y-%m-%d"),
        end=datetime.strptime(end_date, "%Y-%m-%d"),
        variables=[parameter],
        features=[station_id],
    )
    wml_data = collector.raw()
    collector.clear()

    # Convert the raw data to an xarray
    data = WaterML11ToPaegan(wml_data).feature

    # We expect only 1 station
    if len(data.elements) == 0:
        raise ValueError("Data does not contain any station data")
    else:
        station = data.elements[0]

        # Unit conversion from cubic feet to cubic meter per second
        values = np.array(
            [float(point.members[0]["value"]) / 35.315 for point in station.elements],
            dtype=np.float32,
        )
        times = pd.to_datetime([point.time for point in station.elements])

        attrs = {
            "units": "cubic meters per second",
        }

        # Create the xarray dataset
        ds = xr.Dataset(
            {"streamflow": (["time"], values, attrs)}, coords={"time": times}
        )

        # Set some nice attributes
        ds.attrs["title"] = "USGS Data from streamflow data"
        ds.attrs["station"] = station.name
        ds.attrs["stationid"] = station.get_uid()
        ds.attrs["location"] = (station.location.y, station.location.x)

        return ds
