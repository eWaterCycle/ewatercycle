import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Type

import fiona
import numpy as np
import pandas as pd
import requests
import xarray as xr
from cartopy.io import shapereader

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.util import get_time

COMMON_URL = "ca13056c-c347-4a27-b320-930c2a4dd207"
OPENDAP_URL = f"https://opendap.4tu.nl/thredds/dodsC/data2/djht/{COMMON_URL}/1/"
SHAPEFILE_URL = (
    f"https://data.4tu.nl/file/{COMMON_URL}/bbe94526-cf1a-4b96-8155-244f20094719"
)

PROPERTY_VARS = [
    "timezone",
    "name",
    "country",
    "lat",
    "lon",
    "area",
    "p_mean",
    "pet_mean",
    "aridity",
    "frac_snow",
    "moisture_index",
    "seasonality",
    "high_prec_freq",
    "high_prec_dur",
    "low_prec_freq",
    "low_prec_dur",
]

RENAME_ERA5 = {
    "total_precipitation_sum": "pr",
    "potential_evaporation_sum": "evspsblpot",
    "temperature_2m_mean": "tas",
    "temperature_2m_min": "tasmin",
    "temperature_2m_max": "tasmax",
    "streamflow": "Q",
}


class CaravanForcing(DefaultForcing):
    """Retrieves specified part of the caravan dataset from the OpenDAP server.

    Examples:

    The caravan dataset is an already prepared set by Frederik Kratzert,
    (see https://doi.org/10.1038/s41597-023-01975-w).

    This retrieves it from the OpenDAP server of 4TU,
    (see https://doi.org/10.4121/bf0eaf7c-f2fa-46f6-b8cd-77ad939dd350.v4).

    This can be done by specifying the

    .. code-block:: python

        from pathlib import Path
        from rich import print
        from ewatercycle.forcing import sources

        path = Path.cwd()
        forcing_path = path / "Forcing"
        experiment_start_date = "1997-08-01T00:00:00Z"
        experiment_end_date = "2005-09-01T00:00:00Z"
        HRU_id = 1022500

        camels_forcing = sources['LumpedCaravanForcing'].retrieve(start_time = experiment_start_date,
                                                                  end_time = experiment_end_date,
                                                                  directory = forcing_path / "Camels",
                                                                  basin_id = f"camels_0{HRU_id}"
                                                                )
        which gives somthing like:

        .. code-block:: python

            LumpedCaravanForcing(
                start_time='1997-08-01T00:00:00Z',
                end_time='2005-09-01T00:00:00Z',
                directory=PosixPath('/home/davidhaasnoot/eWaterCycle-WSL-WIP/Forcing/Camels'),
                shape=PosixPath('/home/davidhaasnoot/eWaterCycle-WSL-WIP/Forcing/Camels/shapefiles/camels_01022500.shp'),
                filenames={
                    'tasmax': 'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_tasmax.nc',
                    'tasmin': 'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_tasmin.nc',
                    'evspsblpot': 'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_evspsblpot.nc',
                    'pr': 'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_pr.nc',
                    'tas': 'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_tas.nc',
                    'Q': 'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_Q.nc'
                }
            )
    """

    @classmethod
    def generate(cls):
        """ "Not Implemented"""
        msg = (
            "Caravan doesn't generate forcing, instead retrieves prepared forcing."
            "Use the `retrieve` function instead"
        )
        raise NotImplementedError(msg)

    @classmethod
    def retrieve(
        cls: Type["CaravanForcing"],
        start_time: str,
        end_time: str,
        basin_id: str,
        directory: str | Path,
        variables: tuple[str, ...] = (),
        shape: str | Path | None = None,
        **kwargs,
    ) -> "CaravanForcing":
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
                if not specified will default to all.
            shape: (Optional) Path to a shape file.
                If none is specified, will be downloaded automatically.
            **kwargs
        """
        dataset = basin_id.split("_")[0]
        ds = xr.open_dataset(f"{OPENDAP_URL}{dataset}.nc")
        ds_basin = ds.sel(basin_id=basin_id.encode())
        ds_basin_time = crop_ds(ds_basin, start_time, end_time)

        if shape is None:
            shape = get_shapefiles(Path(directory), basin_id)

        if variables == ():
            variables = ds_basin_time.data_vars.keys()

        # only return the properties which are also in property vars
        properties = set(variables).intersection(PROPERTY_VARS)
        non_property_vars = set(variables) - properties
        variable_names = non_property_vars.intersection(
            RENAME_ERA5.keys()
        )  # only take the vars also in Rename dict

        for prop in properties:
            ds_basin_time.coords.update({prop: ds_basin_time[prop].to_numpy()})

        ds_basin_time = ds_basin_time.rename(RENAME_ERA5)
        variables = [RENAME_ERA5[var] for var in variable_names]

        for temp in ["tas", "tasmin", "tasmax"]:
            ds_basin_time[temp].attrs.update({"height": "2m"})

        for var in variables:
            ds_basin_time[var].to_netcdf(
                Path(directory) / f"{basin_id}_{start_time}_{end_time}_{var}.nc"
            )

        forcing = cls(
            directory=Path(directory),
            start_time=start_time,
            end_time=end_time,
            shape=Path(shape),
            filenames={
                var: f"{basin_id}_{start_time}_{end_time}_{var}.nc" for var in variables
            },
        )
        forcing.save()
        return forcing


def get_shapefiles(directory: Path, basin_id: str):
    """Retrieves shapefiles from data 4TU."""
    zip_path = directory / "shapefiles.zip"
    output_path = directory / "shapefiles"
    shape_path = directory / f"{basin_id}.shp"

    if not shape_path.is_file():
        combined_shapefile_path = output_path / "combined.shp"
        if not combined_shapefile_path.is_file():
            timeout = 300
            try:
                with requests.get(SHAPEFILE_URL, timeout=timeout) as response:
                    with tempfile.TemporaryFile() as f:
                        shutil.copyfileobj(response.raw, f)
                        f.seek(0)
                        with zipfile.ZipFile(f) as z:
                            z.extractall(directory)

            except requests.exceptions.Timeout:
                msg = f"Issue connecting to {SHAPEFILE_URL} after {timeout}s"
                raise RuntimeError(msg)

        extract_basin_shapefile(basin_id, combined_shapefile_path, shape_path)

    return shape_path


def extract_basin_shapefile(
    basin_id: str,
    combined_shapefile_path: Path,
    shape_path: Path,
) -> None:
    shape_obj = shapereader.Reader(combined_shapefile_path)
    list_records = []
    for record in shape_obj.records():
        list_records.append(record.attributes["gauge_id"])

    df = pd.DataFrame(
        data=list_records, index=range(len(list_records)), columns=["basin_id"]
    )
    basin_index = df[df["basin_id"] == basin_id].index.array[0]

    with fiona.open(combined_shapefile_path) as src:
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


def crop_ds(ds: xr.Dataset, start_time: str, end_time: str):
    """Crops dataset based on time."""
    get_time(start_time), get_time(end_time)  # if utc, remove Z to parse to np.dt64
    start, end = np.datetime64(start_time[:-1]), np.datetime64(end_time[:-1])
    return ds.isel(
        time=(ds["time"].to_numpy() >= start) & (ds["time"].to_numpy() <= end)
    )
