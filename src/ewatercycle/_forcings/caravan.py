import xarray as xr
import numpy as np
import geopandas as gpd

from pathlib import Path
from typing import Type

import wget
from zipp import zipfile

from ewatercycle.base.forcing import DefaultForcing, LumpedUserForcing
from ewatercycle.util import  get_time


class Caravan(DefaultForcing):
    """Forcing object which retrieves part of the caravan dataset stored on the OpenDAP server"""

    @classmethod
    def retrieve(cls: Type["Caravan"],
                 start_time: str,
                 end_time: str,
                 basin_id: str,
                 directory: str | Path,
                 variables: tuple[str, ...] = (),
                 shape: str | Path | None = None,
                 **kwargs) -> "Caravan":
        """Retrieve caravan for a model.

        Args:
            start_time: Start time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: nd time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            basin_id: Caravan basin_id
            directory: Directory in which forcing should be written.
                If not given will create timestamped directory.
            variables: Variables which are needed for model, if not specified will default to all (not recommended)
            shape: (Optional) Path to a shape file. If none is specified, will be downloaded automatically.
            **kwargs
        """
        dataset = basin_id.split('_')[0]
        ds = xr.open_dataset(
            f"https://opendap.4tu.nl/thredds/dodsC/data2/djht/ca13056c-c347-4a27-b320-930c2a4dd207/1/{dataset}.nc")
        ds_basin = ds.sel(basin_id=basin_id.encode())
        ds_basin_time = crop_ds(ds_basin, start_time, end_time)

        if variables == ():
            variables = (ds.data_vars.keys())

        for var in variables:
            ds_basin_time[var].to_netcdf(Path(directory) / f'{basin_id}_{start_time}_{end_time}_{var}.nc')

        if shape is None:
            shape = get_shapefiles(directory, basin_id)

        forcing = cls(
            directory=Path(directory),
            start_time=start_time,
            end_time=end_time,
            shape=Path(shape),
            filenames={
                var: Path(directory) / f'{basin_id}_{start_time}_{end_time}_{var}' for var in variables
            }
        )
        forcing.save()
        return forcing


class LumpedCaravanForcing(Caravan, LumpedUserForcing):  # type: ignore[misc]
    ...



def get_shapefiles(directory: Path, basin_id: str):
    shape_file_url = "https://data.4tu.nl/file/ca13056c-c347-4a27-b320-930c2a4dd207/bbe94526-cf1a-4b96-8155-244f20094719"
    zip_path = directory / 'shapefiles.zip'
    output_path = directory / 'shapefiles'

    if not zip_path.is_file():
        wget.download(shape_file_url, out=str(zip_path))

    combined_shapefile_path = output_path / "combined.shp"
    if not combined_shapefile_path.is_file():
        with zipfile.ZipFile(zip_path) as myzip:
            myzip.extractall(path=output_path)

    shape = output_path/ f'{basin_id}.shp'
    gdf = gpd.read_file(combined_shapefile_path)
    gdf[gdf['gauge_id'] == basin_id].to_file(shape)

    return shape


def crop_ds(ds: xr.Dataset, start_time: str, end_time:str):
    start_time_dt, end_time_dt = get_time(start_time), get_time(end_time) # if utc, remove Z to parse to np.dt64
    start, end  = np.datetime64(start_time[:-1]), np.datetime64(end_time[:-1])
    ds = ds.isel(time=(ds['time'].values >= start) & (ds['time'].values <= end))
    return ds

