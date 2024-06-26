"""Module to retrieve river discharge data from the caravan dataset."""

import xarray as xr

from ewatercycle._forcings.caravan import CaravanForcing, crop_ds


def get_caravan_data(
    basin_id: str,
    start_time: str,
    end_time: str,
) -> xr.Dataset:
    """Get river discharge data from the caravan dataset.

    The caravan dataset is an already prepared set by Frederik Kratzert,
    (see https://doi.org/10.1038/s41597-023-01975-w).

    This retrieves it from the OpenDAP server of 4TU,
    (see https://doi.org/10.4121/bf0eaf7c-f2fa-46f6-b8cd-77ad939dd350.v4).

    Parameters:
        basin_id: The ID of the desired basin. Data sets can be explored using
                :py:func:`ewatercycle._forcings.caravan.CaravanForcing.get_dataset`
                or :py:func:`ewatercycle._forcings.caravan.CaravanForcing.get_basin_id`
                For more information do `help(CaravanForcing.get_basin_id)` or see
                https://www.ewatercycle.org/caravan-map/.
        start_time: Start time of observations in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of observations in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.

    Returns:
        Xarray dataset with the streamflow data in the variable 'streamflow'.
        The basin and gauge meta data is available on the basin_id dimension.

    Examples:

        To get observations from the French Broad River at Rosman in the USA.

        >>> from ewatercycle.observation.caravan import get_caravan_data
        >>> basin_id = 'camels_03439000'
        >>> start_time = '1981-01-01T00:00:00Z'
        >>> end_time = '1981-01-03T00:00:00Z'
        >>> data = get_caravan_data(basin_id, start_time, end_time)
        >>> data
        <xarray.Dataset> Size: 316B
        Dimensions:     (time: 3)
        Coordinates:
        * time        (time) datetime64[ns] 24B 1981-01-01 1981-01-02 1981-01-03
            basin_id    |S64 64B b'camels_03439000'
        Data variables:
            timezone    |S64 64B ...
            name        |S64 64B ...
            country     |S64 64B ...
            lat         float64 8B ...
            lon         float64 8B ...
            area        float64 8B ...
            streamflow  (time) float32 12B ...
        Attributes:
            history:        Wed Mar 27 16:11:00 2024: /usr/bin/ncap2 -s time=double(t...
            NCO:            netCDF Operators version 5.0.6 (Homepage = http://nco.sf....
            _NCProperties:  version=2,netcdf=4.8.1,hdf5=1.10.7
    """
    dataset: str = basin_id.split("_")[0]
    ds = CaravanForcing.get_dataset(dataset)
    ds_basin = ds.sel(basin_id=basin_id.encode())
    ds_basin_time = crop_ds(ds_basin, start_time, end_time)
    # convert mm/d to m3/s using the area of the basin
    ds_basin_time["streamflow"] = (
        ds_basin_time["streamflow"] * ds_basin_time["area"] / 1000 / 86400
    )
    ds_basin_time["streamflow"].attrs["unit"] = "m3/s"
    return ds_basin_time[
        ["timezone", "name", "country", "lat", "lon", "area", "streamflow"]
    ]
