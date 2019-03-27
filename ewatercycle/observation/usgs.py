import os
from datetime import datetime

import xarray as xr
import numpy as np
from osgeo import osr
from pyoos.collectors.usgs.usgs_rest import UsgsRest
from pyoos.parsers.waterml import WaterML11ToPaegan


def download_usgs_data(station_id, start_date, end_date, parameter='00060', cache_dir=None):
    """
    Download data from the USGS

    Parameters
    ----------
    station_id : str
        The station id to get
    start_date : str
        String for start date in the format: 'YYYY-MM-dd', e.g. '1980-01-01'
    end_date : str
        String for start date in the format: 'YYYY-MM-dd', e.g. '2018-12-31'
    parameter : str
        The parameter code to download, e.g. ('00060') discharge, cubic feet per second

    Examples
    --------
    >>> from ewatercycle.observation.usgs import download_usgs_data
    >>> data = download_usgs_data('03109500', '2000-01-01', '2000-12-31', cache_dir='.')
    >>> data
        <xarray.Dataset>
        Dimensions:     (time: 8032)
        Coordinates:
        * time        (time) datetime64[ns] 2000-01-04T05:00:00 ... 2000-12-23T04:00:00
        Data variables:
            Streamflow  (time) float32 8.296758 10.420501 ... 10.647034 11.694747
        Attributes:
            title:      USGS Data from streamflow data
            crs:        GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,29...
            station:    Little Beaver Creek near East Liverpool OH
            stationid:  03109500
        location:   (40.6758974, -80.5406244)
    """
    if cache_dir is None:
        cache_dir = os.environ['USGS_DATA_HOME']

    # Check if we have the netcdf data
    netcdf = os.path.join(cache_dir, station_id + ".nc")
    if os.path.exists(netcdf):
        return xr.open_dataset(netcdf)

    # Download the data if needed
    out = os.path.join(cache_dir, station_id + ".wml")
    if not os.path.exists(out):
        collector = UsgsRest()
        collector.filter(
            start=datetime.fromisoformat(start_date),
            end=datetime.fromisoformat(end_date),
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

        values = np.array([
            float(point.members[0]['value']) / 35.315
            for point in station.elements
        ],
                          dtype=np.float32)
        times = [point.time for point in station.elements]

        # I'm assuming it always has EPSG:4326
        p1 = osr.SpatialReference()
        p1.ImportFromEPSG(4326)

        attrs = {
            'units': 'cubic meters per second',
        }

        # Create the xarray dataset
        ds = xr.Dataset({'Streamflow': (['time'], values, attrs)},
                        coords={'time': times})

        # Set some nice attributes
        ds.attrs['title'] = 'USGS Data from streamflow data'
        ds.attrs['crs'] = p1.ExportToWkt()
        ds.attrs['station'] = station.name
        ds.attrs['stationid'] = station.get_uid()
        ds.attrs['location'] = (station.location.y, station.location.x)

        ds.to_netcdf(os.path.join(cache_dir, station.get_uid() + '.nc'))

        return ds
