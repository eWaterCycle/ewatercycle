"""Global Runoff Data Centre module."""

import logging
import os
from typing import Dict, Optional, Union

import pandas as pd
import xarray as xr
from numpy import nan

from ewatercycle import CFG
from ewatercycle.util import get_time, to_absolute_path

logger = logging.getLogger(__name__)

MetaDataType = Dict[str, Union[str, int, float]]


def get_grdc_data(
    station_id: str,
    start_time: str,
    end_time: str,
    data_home: Optional[str] = None,
    column: str = "streamflow",
) -> xr.Dataset:
    """Get river discharge data from Global Runoff Data Centre (GRDC).

    Requires the GRDC daily data files in a local directory. The GRDC daily data
    NetCDF file can be downloaded at
    https://www.bafg.de/GRDC/EN/02_srvcs/21_tmsrs/riverdischarge_node.html .
    The downloaded zip file contains a file named GRDC-Daily.nc.

    This function will first try to read data from the GRDC-Daily.nc file in the ``data_home`` directory.
    If that fails it will look for the GRDC Export (ASCII text) formatted file for example ``6435060_Q_Day.Cmd.txt``.

    Args:
        station_id: The station id to get. The station id can be found in the
            catalogues at
            https://www.bafg.de/GRDC/EN/02_srvcs/21_tmsrs/212_prjctlgs/project_catalogue_node.html
        start_time: Start time of model in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of model in  UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        data_home : optional. The directory where the daily grdc data is
            located. If left out will use the grdc_location in the eWaterCycle
            configuration file.
        column: optional. Name of column in dataframe. Default: "streamflow".

    Returns:
        grdc data in a xarray dataset. Shaped like a filtered version of the GRDC daily NetCDF file.

    Raises:
        ValueError: If no data for the requested station id and period could not be found.

    Examples:

        .. code-block:: python

            from ewatercycle.observation.grdc import get_grdc_data

            ds = get_grdc_data('6435060',
                               '2000-01-01T00:00Z',
                               '2001-01-01T00:00Z')
            ds
            <xarray.Dataset> Size: 5kB
            Dimensions:              (time: 367)
            Coordinates:
            * time                 (time) datetime64[ns] 3kB 2000-01-01 ... 2001-01-01
                id                   int32 4B 6435060
            Data variables:
                streamflow           (time) float32 1kB ...
                area                 float32 4B ...
                country              <U2 8B ...
                geo_x                float32 4B ...
                geo_y                float32 4B ...
                geo_z                float32 4B ...
                owneroforiginaldata  <U38 152B ...
                river_name           <U11 44B 'RHINE RIVER'
                station_name         <U6 24B 'LOBITH'
                timezone             float32 4B ...
            Attributes:
                title:          Mean daily discharge (Q)
                Conventions:    CF-1.7
                references:     grdc.bafg.de
                institution:    GRDC
                history:        Download from GRDC Database, 21/06/2024
                missing_value:  -999.000
    """  # noqa: E501
    if data_home:
        data_path = to_absolute_path(data_home)
    elif CFG.grdc_location:
        data_path = to_absolute_path(CFG.grdc_location)
    else:
        raise ValueError(
            "Provide the grdc path using `data_home` argument"
            "or using `grdc_location` in ewatercycle configuration file."
        )

    if not data_path.exists():
        raise ValueError(f"The grdc directory {data_path} does not exist!")

    # Read the NetCDF file
    nc_file = data_path / "GRDC-Daily.nc"
    if nc_file.exists():
        ds = xr.open_dataset(nc_file)
        if int(station_id) in ds["id"]:
            ds = ds.sel(
                id=int(station_id),
                time=slice(get_time(start_time).date(), get_time(end_time).date()),
            )
            return ds.rename({"runoff_mean": column})

    # Read the text data
    raw_file = data_path / f"{station_id}_Q_Day.Cmd.txt"
    if not raw_file.exists():
        if nc_file.exists():
            raise ValueError(
                f"The grdc station {station_id} is not in the {nc_file} file and {raw_file} does not exist!"  # noqa: E501
            )
        else:
            raise ValueError(f"The grdc file {raw_file} does not exist!")

    # Convert the raw data to an dataframe
    metadata, df = _grdc_read(
        raw_file,
        start=get_time(start_time).date(),
        end=get_time(end_time).date(),
        column=column,
    )

    ds = xr.Dataset.from_dict(
        {
            "coords": {
                "time": {
                    "dims": ("time",),
                    "attrs": {"long_name": "time"},
                    "data": df.index.values,
                },
                "id": {
                    "dims": (),
                    "attrs": {"long_name": "grdc number"},
                    "data": int(station_id),
                },
            },
            "dims": {
                "time": len(df.index),
            },
            "attrs": {
                "title": metadata["dataSetContent"],
                "Conventions": "CF-1.7",
                "references": "grdc.bafg.de",
                "institution": "GRDC",
                "history": f"Converted from {raw_file.name} of {metadata['file_generation_date']} to netcdf by eWaterCycle Python package",
                "missing_value": "-999.000",
            },
            "data_vars": {
                column: {
                    "dims": ("time",),
                    "attrs": {"units": "m3/s", "long_name": "Mean daily discharge (Q)"},
                    "data": df[column].values,
                },
                "area": {
                    "dims": (),
                    "attrs": {"units": "km2", "long_name": "catchment area"},
                    "data": metadata["grdc_catchment_area_in_km2"],
                },
                "country": {
                    "dims": (),
                    "attrs": {
                        "long_name": "country name",
                        "iso2": "ISO 3166-1 alpha-2 - two-letter country code",
                    },
                    "data": metadata["country_code"],
                },
                "geo_x": {
                    "dims": (),
                    "attrs": {
                        "units": "degree_east",
                        "long_name": "station longitude (WGS84)",
                    },
                    "data": metadata["grdc_longitude_in_arc_degree"],
                },
                "geo_y": {
                    "dims": (),
                    "attrs": {
                        "units": "degree_north",
                        "long_name": "station latitude (WGS84)",
                    },
                    "data": metadata["grdc_latitude_in_arc_degree"],
                },
                "geo_z": {
                    "dims": (),
                    "attrs": {
                        "units": "m",
                        "long_name": "station altitude (m above sea level)",
                    },
                    "data": metadata["altitude_masl"],
                },
                "owneroforiginaldata": {
                    "dims": (),
                    "attrs": {"long_name": "Owner of original data"},
                    "data": metadata["Owner of original data"],
                },
                "river_name": {
                    "dims": (),
                    "attrs": {"long_name": "river name"},
                    "data": metadata["river_name"],
                },
                "station_name": {
                    "dims": (),
                    "attrs": {"long_name": "station name"},
                    "data": metadata["station_name"],
                },
                "timezone": {
                    "dims": (),
                    "attrs": {
                        "units": "00:00",
                        "long_name": "utc offset, in relation to the national capital",
                    },
                    "data": nan,
                },
            },
        }
    )

    return ds


def _grdc_read(grdc_station_path, start, end, column):
    with grdc_station_path.open("r", encoding="cp1252", errors="ignore") as file:
        data = file.read()

    metadata = _grdc_metadata_reader(grdc_station_path, data)

    all_lines = data.split("\n")
    header = 0
    for i, line in enumerate(all_lines):
        if line.startswith("# DATA"):
            header = i + 1
            break

    # Import GRDC data into dataframe and modify dataframe format
    grdc_data = pd.read_csv(
        grdc_station_path,
        encoding="cp1252",
        skiprows=header,
        delimiter=";",
        parse_dates=["YYYY-MM-DD"],
        na_values="-999",
    )
    grdc_station_df = pd.DataFrame(
        {column: grdc_data[" Value"].array},
        index=grdc_data["YYYY-MM-DD"].array,
    )
    grdc_station_df.index.rename("time", inplace=True)

    # Select GRDC station data that matches the forecast results Date
    grdc_station_select = grdc_station_df.loc[start:end]

    return metadata, grdc_station_select


def _grdc_metadata_reader(grdc_station_path, all_lines):
    # Initiating a dictionary that will contain all GRDC attributes.
    # This function is based on earlier work by Rolf Hut.
    # https://github.com/RolfHut/GRDC2NetCDF/blob/master/GRDC2NetCDF.py
    # DOI: 10.5281/zenodo.19695
    # that function was based on earlier work by Edwin Sutanudjaja
    # from Utrecht University.
    # https://github.com/edwinkost/discharge_analysis_IWMI

    # initiating a dictionary that will contain all GRDC attributes:
    attribute_grdc = {}

    # split the content of the file into several lines
    all_lines = all_lines.replace("\r", "")
    all_lines = all_lines.split("\n")

    # get grdc ids (from files) and check their consistency with their
    # file names
    id_from_file_name = int(
        os.path.basename(grdc_station_path).split(".")[0].split("_")[0]
    )
    id_from_grdc = None
    if id_from_file_name == int(all_lines[8].split(":")[1].strip()):
        id_from_grdc = int(all_lines[8].split(":")[1].strip())
    else:
        print(
            "GRDC station "
            + str(id_from_file_name)
            + " ("
            + str(grdc_station_path)
            + ") is NOT used."
        )

    if id_from_grdc is not None:
        attribute_grdc["grdc_file_name"] = str(grdc_station_path)
        attribute_grdc["id_from_grdc"] = id_from_grdc

        try:
            attribute_grdc["file_generation_date"] = str(
                all_lines[6].split(":")[1].strip()
            )
        except (IndexError, ValueError):
            attribute_grdc["file_generation_date"] = "NA"

        try:
            attribute_grdc["river_name"] = str(all_lines[9].split(":")[1].strip())
        except (IndexError, ValueError):
            attribute_grdc["river_name"] = "NA"

        try:
            attribute_grdc["station_name"] = str(all_lines[10].split(":")[1].strip())
        except (IndexError, ValueError):
            attribute_grdc["station_name"] = "NA"

        try:
            attribute_grdc["country_code"] = str(all_lines[11].split(":")[1].strip())
        except (IndexError, ValueError):
            attribute_grdc["country_code"] = "NA"

        try:
            attribute_grdc["grdc_latitude_in_arc_degree"] = float(
                all_lines[12].split(":")[1].strip()
            )
        except (IndexError, ValueError):
            attribute_grdc["grdc_latitude_in_arc_degree"] = "NA"

        try:
            attribute_grdc["grdc_longitude_in_arc_degree"] = float(
                all_lines[13].split(":")[1].strip()
            )
        except (IndexError, ValueError):
            attribute_grdc["grdc_longitude_in_arc_degree"] = "NA"

        try:
            attribute_grdc["grdc_catchment_area_in_km2"] = float(
                all_lines[14].split(":")[1].strip()
            )
            if attribute_grdc["grdc_catchment_area_in_km2"] <= 0.0:
                attribute_grdc["grdc_catchment_area_in_km2"] = "NA"
        except (IndexError, ValueError):
            attribute_grdc["grdc_catchment_area_in_km2"] = "NA"

        try:
            attribute_grdc["altitude_masl"] = float(all_lines[15].split(":")[1].strip())
        except (IndexError, ValueError):
            attribute_grdc["altitude_masl"] = "NA"

        try:
            attribute_grdc["dataSetContent"] = str(all_lines[20].split(":")[1].strip())
        except (IndexError, ValueError):
            attribute_grdc["dataSetContent"] = "NA"

        try:
            attribute_grdc["units"] = str(all_lines[22].split(":")[1].strip())
        except (IndexError, ValueError):
            attribute_grdc["units"] = "NA"

        try:
            attribute_grdc["Owner of original data"] = (
                all_lines[18].split(":")[1].strip()
            )
        except (IndexError, ValueError):
            attribute_grdc["Owner of original data"] = "Unknown"

    return attribute_grdc
