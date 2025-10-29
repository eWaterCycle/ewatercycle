import shutil
import zipfile
from pathlib import Path

import fiona
import pandas as pd
import urllib3
import xarray as xr
from cartopy.io import shapereader

from ewatercycle._forcings._caravan_reference import CAMELS_VARS, ERA5_VARS
from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.util import get_time

COMMON_URL = "ca13056c-c347-4a27-b320-930c2a4dd207"
VERSION = 2
OPENDAP_URL = f"https://opendap.4tu.nl/thredds/dodsC/data2/djht/{COMMON_URL}/{VERSION}/"
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
            from ewatercycle.forcing import sources

            path = Path.cwd()
            forcing_path = path / "Forcing" / "Camels"
            forcing_path.mkdir(parents=True, exist_ok=True)
            experiment_start_date = "1997-08-01T00:00:00Z"
            experiment_end_date = "2005-09-01T00:00:00Z"
            HRU_id = 1022500

            camels_forcing = sources['CaravanForcing'].generate(
                start_time = experiment_start_date,
                end_time = experiment_end_date,
                directory = forcing_path,
                basin_id = f"camels_0{HRU_id}"
            )

        which gives something like:

        .. code-block:: python

            CaravanForcing(
            start_time='1997-08-01T00:00:00Z',
            end_time='2005-09-01T00:00:00Z',
            directory=PosixPath('/home/davidhaasnoot/eWaterCycle-WSL-WIP/Forcing/Camels'),
            shape=PosixPath('/home/davidhaasnoot/eWaterCycle-WSL-WIP/Forcing/Camels/shapefiles/camels_01022500.shp'),
            filenames={
                'tasmax':
                'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_tasmax.nc',
                'tasmin':
                'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_tasmin.nc',
                'evspsblpot':
                'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_evspsblpot.nc',
                'pr': 'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_pr.nc',
                'tas': 'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_tas.nc',
                'Q': 'camels_01022500_1997-08-01T00:00:00Z_2005-09-01T00:00:00Z_Q.nc'
            }
            )


        More in depth notebook van be found here:
        https://gist.github.com/Daafip/ac1b030eb5563a76f4d02175f2716fd7
    """  # noqa: E501

    @classmethod
    def get_dataset(cls: type["CaravanForcing"], dataset: str) -> xr.Dataset:
        """Opens specified dataset from data.4tu.nl OPeNDAP server.

        Args:
            dataset (str): name of dataset, choose from:
                'camels',
                'camelsaus',
                'camelsbr',
                'camelscl',
                'camelsgb',
                'hysets',
                'lamah'
        """
        return xr.open_dataset(f"{OPENDAP_URL}{dataset}.nc")

    @classmethod
    def get_basin_id(cls: type["CaravanForcing"], dataset: str) -> list[str]:
        """Gets a list of all the basin ids in provided dataset.

        Args:
            dataset (str): name of dataset, choose from:
                'camels',
                'camelsaus',
                'camelsbr',
                'camelscl',
                'camelsgb',
                'hysets',
                'lamah'

        Note:
            https://www.ewatercycle.org/caravan-map/ contains online a set of
            interactive maps which allows exploration of the available catchments and
            also contains the needed basin_ids.
            Alternatively, a zip with shapefiles is available at
            https://doi.org/10.4121/ca13056c-c347-4a27-b320-930c2a4dd207.v1 which also
            allows exploration of the dataset.
        """
        return [val.decode() for val in cls.get_dataset(dataset).basin_id.to_numpy()]

    @classmethod
    def generate(  # type: ignore[override]
        cls: type["CaravanForcing"],
        start_time: str,
        end_time: str,
        directory: str,
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
            directory: Directory in which forcing should be written.
            variables: Variables which are needed for model,
                if not specified will default to all.
            shape: (Optional) Path to a shape file.
                If none is specified, will be downloaded automatically.
            kwargs: Additional keyword arguments.
                basin_id: The ID of the desired basin. Data sets can be explored using
                    `CaravanForcing.get_dataset(dataset_name)` or
                    `CaravanForcing.get_basin_id(dataset_name)`
                    where `dataset_name` is the name of a dataset in Caravan
                    (for example, "camels" or "camelsgb").
                    For more information do `help(CaravanForcing.get_basin_id)` or see
                    https://www.ewatercycle.org/caravan-map/.
                data_source: The ID of the data source to be used. For some datasets
                    multiple datasources are available. currently this is only
                    implemented for the (basins in the) "camels" (ie. camels US)
                    dataset. If "data_sources" is not specified, it defaults to
                    'era5_land' (the default for caravan). Options for Camels are:
                        - 'nldas'
                        - 'maurer'
                        - 'daymet'
                    See the documentation of Camels for details on the differences
                    between these data sources: https://dx.doi.org/10.5065/D6MW2F4D
                retrieve_shape: If the shapefile should be retrieved (optional). By
                    default False.
        """
        if "basin_id" not in kwargs:
            msg = (
                "You have to specify a basin ID to be able to generate forcing from"
                " Caravan."
            )
            raise ValueError(msg)

        basin_id = str(kwargs["basin_id"])

        if "data_source" not in kwargs:
            data_source = "era5_land"
        elif kwargs["data_source"] in ["era5_land", "nldas", "maurer", "daymet"]:
            data_source = str(kwargs["data_source"])
        else:
            msg = (
                "If 'data_source' is provided it needs to be one of:\n"
                "   'era5_land', 'nldas', 'maurer', 'daymet'"
            )
            raise ValueError(msg)

        dataset: str = basin_id.split("_")[0]
        ds = cls.get_dataset(dataset)
        ds_basin = ds.sel(basin_id=basin_id.encode())

        if dataset != "camels" and data_source != "era5_land":
            msg = (
                "Alternative data sources are only implemented for the camels "
                "(USA) dataset"
            )
            raise ValueError(msg)
        ds_basin = get_camels_data(ds_basin, data_source.encode())

        ds_basin_time = crop_ds(ds_basin, start_time, end_time)

        retrieve_shape = (
            bool(kwargs["retrieve_shape"]) if "retrieve_shape" in kwargs else True
        )
        if retrieve_shape:
            shape = get_shapefiles(Path(directory), basin_id)

        if len(variables) == 0:
            variables = ds_basin_time.data_vars.keys()  # type: ignore[assignment]

        # only return the properties which are also in property vars
        properties = set(variables).intersection(PROPERTY_VARS)
        non_property_vars = set(variables) - properties

        # only take the vars also in Rename dict (ie. pr, tas, etc.)
        variable_names = non_property_vars.intersection(set(RENAME_ERA5.values()))

        for prop in properties:
            ds_basin_time.coords.update({prop: ds_basin_time[prop].to_numpy()})

        ds_basin_time = convert_units(ds_basin_time)

        start_time_name = start_time[:10]
        end_time_name = end_time[:10]

        history_attrs = ds_basin_time.attrs["history"]
        for var in variable_names:
            ds_basin_time[var].attrs["history"] = history_attrs

            # Basin IDs can be duplicate because of problem in opendap data
            #    only select the one with data (if it exists)
            valid_basin = ~ds_basin_time[var].isnull().all(dim="time")
            if ds_basin_time[var]["basin_id"].size > 1 and valid_basin.any():
                dout = ds_basin_time[var][~ds_basin_time[var].isnull().all(dim="time")]
            else:
                dout = ds_basin_time[var]

            dout.isel(basin_id=0).to_netcdf(
                Path(directory)
                / f"{basin_id}_{start_time_name}_{end_time_name}_{var}.nc"
            )

        forcing = cls(
            directory=Path(directory),
            start_time=start_time,
            end_time=end_time,
            shape=Path(shape) if shape is not None else None,
            filenames={
                var: f"{basin_id}_{start_time_name}_{end_time_name}_{var}.nc"
                for var in variable_names
            },
        )
        forcing.save()
        return forcing

    def to_xarray(self) -> xr.Dataset:
        """Return this Forcing object as an xarray Dataset."""
        if len(self.filenames) == 0:
            msg = "There are no variables stored in this Forcing object."
            raise ValueError(msg)
        fpaths = [self.directory / filename for _, filename in self.filenames.items()]
        return xr.merge([xr.open_dataset(fpath, chunks="auto") for fpath in fpaths])


def get_shapefiles(directory: Path, basin_id: str) -> Path:
    """Retrieve shapefiles from data 4TU.nl ."""
    zip_path = directory / "shapefiles.zip"
    output_path = directory / "shapefiles"
    shape_path = directory / f"{basin_id}.shp"
    combined_shapefile_path = output_path / "combined.shp"

    if not shape_path.is_file():
        if not combined_shapefile_path.is_file():
            http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=10.0, read=300))
            with (
                http.request("GET", SHAPEFILE_URL, preload_content=False) as r,
                zip_path.open("wb") as out_file,
            ):
                shutil.copyfileobj(r, out_file)

        with zipfile.ZipFile(zip_path) as myzip:
            myzip.extractall(path=directory)

        extract_basin_shapefile(basin_id, combined_shapefile_path, shape_path)

    return shape_path


def extract_basin_shapefile(
    basin_id: str,
    combined_shapefile_path: Path,
    shape_path: Path,
) -> None:
    """Extract single polygon from multipolygon shapefile."""
    shape_obj = shapereader.Reader(combined_shapefile_path)
    list_records = [record.attributes["gauge_id"] for record in shape_obj.records()]

    basins = pd.DataFrame(
        data=list_records, index=range(len(list_records)), columns=["basin_id"]
    )
    basin_index = basins[basins["basin_id"] == basin_id].index.array[0]

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
                    if geom.type != "Polygon":
                        msg = "Only polygons are supported"
                        raise ValueError(msg)

                    # Add the signed area of the polygon and a timestamp
                    # to the feature properties map.
                    props = fiona.Properties.from_dict(
                        **feat.properties,
                    )

                    dst.write(fiona.Feature(geometry=geom, properties=props))


def crop_ds(ds: xr.Dataset, start_time: str, end_time: str) -> xr.Dataset:
    """Crops dataset based on time."""
    start = pd.Timestamp(get_time(start_time)).tz_convert(None)
    end = pd.Timestamp(get_time(end_time)).tz_convert(None)
    return ds.isel(
        time=(ds["time"].to_numpy() >= start) & (ds["time"].to_numpy() <= end)
    )


def get_camels_data(ds: xr.Dataset, data_source: bytes) -> xr.Dataset:
    """Grab the right source of input data for the camels (USA) dataset.

    The way the dataset on OPENDAP is structured is not optimal, see the
    discussion at:
    https://github.com/eWaterCycle/ewatercycle/pull/433/

    This function will select and rename the right variables.
    """
    if data_source == b"era5_land":
        ds_era5 = ds.sel(data_source=b"era5_land")
        ds_era5 = ds_era5.drop_vars("data_source")
        ds_era5 = ds_era5[[*PROPERTY_VARS, *ERA5_VARS, "streamflow"]]
        return ds_era5.rename(RENAME_ERA5)

    ds_common = ds.sel(data_source=b"era5_land")
    ds_common = ds_common.drop_vars("data_source")
    ds_common = ds_common[[*PROPERTY_VARS, "streamflow"]]
    ds_common = ds_common.rename({"streamflow": "Q"})

    ds_camels = ds.sel(data_source=data_source)
    ds_camels = ds_camels.drop_vars("data_source")
    ds_camels = ds_camels[CAMELS_VARS]

    return xr.merge((ds_common, ds_camels))


def convert_units(ds: xr.Dataset) -> xr.Dataset:
    """Caravan uses degrees C, mm/d. We need Kelvin and km/m2/s."""
    # convert units to Kelvin for compatibility with CMOR MIP table units
    for temp in ["tas", "tasmin", "tasmax"]:
        if ds[temp].attrs["unit"] in ["°C", "degC"]:
            ds[temp].values = ds[temp].to_numpy() + 273.15
            ds[temp].attrs["unit"] = "K"
        ds[temp].attrs.update({"height": "2m"})

    for var in ["evspsblpot", "pr"]:
        if ds[var].attrs["unit"] in ["mm", "mm/d"]:
            # mm/day --> kg m-2 s-1
            ds[var].values = ds[var].to_numpy() / (86400)
            ds[var].attrs["unit"] = "kg m-2 s-1"

    return ds
