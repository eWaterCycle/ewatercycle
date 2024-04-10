import xarray as xr
import numpy as np
import pandas as pd
from cartopy.io import shapereader
import fiona

from pathlib import Path
from typing import Type

import requests
from zipp import zipfile

from ewatercycle.base.forcing import DefaultForcing, LumpedUserForcing
from ewatercycle.util import get_time

COMMON_URL = "ca13056c-c347-4a27-b320-930c2a4dd207"
OPENDAP_URL = f"https://opendap.4tu.nl/thredds/dodsC/data2/djht/{COMMON_URL}/1/"
SHAPEFILE_URL = f"https://data.4tu.nl/file/{COMMON_URL}/bbe94526-cf1a-4b96-8155-244f20094719"

PROPERTY_VARS = ['timezone',
                 'name',
                 'country',
                 'lat',
                 'lon',
                 'area',
                 'p_mean',
                 'pet_mean',
                 'aridity',
                 'frac_snow',
                 'moisture_index',
                 'seasonality',
                 'high_prec_freq',
                 'high_prec_dur',
                 'low_prec_freq',
                 'low_prec_dur']
class Caravan(DefaultForcing):
    """Retrieves specified part of the caravan dataset from the OpenDAP server."""

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
            variables: Variables which are needed for model,
                if not specified will default to all (not recommended)
            shape: (Optional) Path to a shape file.
                If none is specified, will be downloaded automatically.
            **kwargs
        """
        dataset = basin_id.split('_')[0]
        ds = xr.open_dataset(
            f"{OPENDAP_URL}{dataset}.nc")
        ds_basin = ds.sel(basin_id=basin_id.encode())
        ds_basin_time = crop_ds(ds_basin, start_time, end_time)

        if shape is None:
            shape = get_shapefiles(directory, basin_id)

        shape_obj = shapereader.Reader(shape)
        centre = next(shape_obj.geometries()).centroid
        ds_basin_time.coords.update({'lat': centre.y,
                                     'lon': centre.x
                                     })
        ds_basin_time = ds_basin_time.drop_vars('basin_id')
        if variables == ():
            variables = (ds.data_vars.keys())

        # TODO: Check if this is per NetCDF convention
        variables = list(set(variables).difference(set(PROPERTY_VARS)))
        properties = list(set(variables).intersection(set(PROPERTY_VARS)))

        for prop in properties:
            ds_basin.coords.update({prop: ds_basin[prop].to_numpy()})

        for var in variables:
            ds_basin_time[var].to_netcdf(Path(directory) / f'{basin_id}_{start_time}_{end_time}_{var}.nc')

        forcing = cls(
            directory=Path(directory),
            start_time=start_time,
            end_time=end_time,
            shape=Path(shape),
            filenames={
                var: f'{basin_id}_{start_time}_{end_time}_{var}.nc' for var in variables
            }
        )
        forcing.save()
        return forcing


class LumpedCaravanForcing(Caravan, LumpedUserForcing):  # type: ignore[misc]
    ...



def get_shapefiles(directory: Path, basin_id: str):
    """retrieves shapefiles from openDAP"""

    zip_path = directory / 'shapefiles.zip'
    output_path = directory / 'shapefiles'

    if not zip_path.is_file():
        timeout = 300
        try:
            r = requests.get(SHAPEFILE_URL, timeout=timeout)
        except requests.exceptions.Timeout:
            msg = (
            f"Issue connecting to {SHAPEFILE_URL} after {timeout}s"
            )
            raise RuntimeError(msg)

        with zip_path.open('wb') as fin:
            fin.write(r.content)

    combined_shapefile_path = output_path / "combined.shp"
    if not combined_shapefile_path.is_file():
        with zipfile.ZipFile(zip_path) as myzip:
            myzip.extractall(path=directory)

    shape_path = output_path/ f'{basin_id}.shp'

    shape_obj = shapereader.Reader(combined_shapefile_path)
    list_records = []
    for record in shape_obj.records():
        list_records.append(record.attributes['gauge_id'])

    df = pd.DataFrame(data=list_records, index=range(len(list_records)), columns=['basin_id'])
    basin_index = df[df['basin_id'] == basin_id].index.array[0]

    with fiona.open(
        combined_shapefile_path
    ) as src:
        dst_schema = src.schema  # Copy the source schema
        # Create a sink for processed features with the same format and
        # coordinate reference system as the source.
        with fiona.open(
            shape_path,
            mode="w",
            layer=basin_id,
            crs=src.crs,
            driver="ESRI Shapefile",
            schema=dst_schema,
        ) as dst:
            for i, feat in enumerate(src):
                # kind of clunky but it works: select filtered polygon
                if i == basin_index:
                    geom = feat.geometry
                    assert geom.type == "Polygon"

                    # Add the signed area of the polygon and a timestamp
                    # to the feature properties map.
                    props = fiona.Properties.from_dict(
                        **feat.properties,
                    )

                    dst.write(fiona.Feature(geometry=geom, properties=props))

    return shape_path


def crop_ds(ds: xr.Dataset, start_time: str, end_time:str):
    get_time(start_time), get_time(end_time) # if utc, remove Z to parse to np.dt64
    start, end  = np.datetime64(start_time[:-1]), np.datetime64(end_time[:-1])
    ds = ds.isel(time=(ds['time'].to_numpy() >= start) & (ds['time'].to_numpy() <= end))
    return ds

