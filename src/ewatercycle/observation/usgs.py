import os
from datetime import datetime

import xarray as xr
import numpy as np
from pyoos.collectors.usgs.usgs_rest import UsgsRest
from pyoos.parsers.waterml import WaterML11ToPaegan


def get_usgs_data(station_id,
                  start_date,
                  end_date,
                  parameter='00060',
                  cache_dir=None):
    """
    Get river discharge data from the
    `U.S. Geological Survey Water Services <https://waterservices.usgs.gov/>`_ (USGS) rest web service.

    Parameters
    ----------
    station_id : str
        The station id to get
    start_date : str
        String for start date in the format: 'YYYY-MM-dd', e.g. '1980-01-01'
    end_date : str
        String for start date in the format: 'YYYY-MM-dd', e.g. '2018-12-31'
    parameter : str
        The parameter code to get, e.g. ('00060') discharge, cubic feet per second
    cache_dir : str
        Directory where files retrieved from the web service are cached.
        If set to None then USGS_DATA_HOME env var will be used as cache directory.

    Examples
    --------
    >>> from ewatercycle.observation.usgs import get_usgs_data
    >>> data = get_usgs_data('03109500', '2000-01-01', '2000-12-31', cache_dir='.')
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
    """
    if cache_dir is None:
        cache_dir = os.environ['USGS_DATA_HOME']

    # Check if we have the netcdf data
    netcdf = os.path.join(
        cache_dir, "USGS_" + station_id + "_" + parameter + "_" + start_date +
        "_" + end_date + ".nc")
    if os.path.exists(netcdf):
        return xr.open_dataset(netcdf)

    # Download the data if needed
    out = os.path.join(
        cache_dir, "USGS_" + station_id + "_" + parameter + "_" + start_date +
        "_" + end_date + ".wml")
    if not os.path.exists(out):
        collector = UsgsRest()
        collector.filter(
            start=datetime.strptime(start_date, "%Y-%m-%d"),
            end=datetime.strptime(end_date, "%Y-%m-%d"),
            variables=[parameter],
            features=[station_id])
        data = collector.raw()
        with open(out, 'w') as file:
            file.write(data)
        collector.clear()
    else:
        with open(out, 'r') as file:
            data = file.read()

    # Convert the raw data to an xarray
    data = WaterML11ToPaegan(data).feature

    # We expect only 1 station
    if len(data.elements) == 0:
        raise ValueError("Data does not contain any station data")
    else:
        station = data.elements[0]

        # Unit conversion from cubic feet to cubic meter per second
        values = np.array([
            float(point.members[0]['value']) / 35.315
            for point in station.elements
        ],
                          dtype=np.float32)
        times = [point.time for point in station.elements]

        attrs = {
            'units': 'cubic meters per second',
        }

        # Create the xarray dataset
        ds = xr.Dataset({'streamflow': (['time'], values, attrs)},
                        coords={'time': times})

        # Set some nice attributes
        ds.attrs['title'] = 'USGS Data from streamflow data'
        ds.attrs['station'] = station.name
        ds.attrs['stationid'] = station.get_uid()
        ds.attrs['location'] = (station.location.y, station.location.x)

        ds.to_netcdf(netcdf)

        return ds
