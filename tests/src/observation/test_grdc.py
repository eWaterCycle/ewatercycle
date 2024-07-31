from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from xarray.testing import assert_allclose

from ewatercycle import CFG
from ewatercycle.observation.grdc import get_grdc_data


@pytest.fixture()
def sample_grdc_file(tmp_path):
    fn = tmp_path / "42424242_Q_Day.Cmd.txt"
    # Sample with fictive data, but with same structure as real file
    body = """# Title:                 GRDC STATION DATA FILE
#                        --------------
# Format:                DOS-ASCII
# Field delimiter:       ;
# missing values are indicated by -999.000
#
# file generation date:  2000-02-02
#
# GRDC-No.:              42424242
# River:                 SOME RIVER
# Station:               SOME
# Country:               NA
# Latitude (DD):       52.356154
# Longitude (DD):      4.955153
# Catchment area (km²):      4242.0
# Altitude (m ASL):        8.0
# Next downstream station:      42424243
# Remarks:
#************************************************************
#
# Data Set Content:      MEAN DAILY DISCHARGE (Q)
#                        --------------------
# Unit of measure:                   m³/s
# Time series:           2000-01 - 2000-01
# No. of years:          1
# Last update:           2000-02-01
#
# Table Header:
#     YYYY-MM-DD - Date
#     hh:mm      - Time
#     Value   - original (provided) data
#************************************************************
#
# Data lines: 3
# DATA
YYYY-MM-DD;hh:mm; Value
2000-01-01;--:--;    123.000
2000-01-02;--:--;    456.000
2000-01-03;--:--;    -999.000"""
    with fn.open("w", encoding="cp1252") as f:
        f.write(body)
    return fn


@pytest.fixture()
def expected_results():
    return xr.Dataset.from_dict(
        {
            "coords": {
                "time": {
                    "dims": ("time",),
                    "attrs": {"long_name": "time"},
                    "data": [
                        datetime(2000, 1, 1, 0, 0),
                        datetime(2000, 1, 2, 0, 0),
                        datetime(2000, 1, 3, 0, 0),
                    ],
                },
                "id": {
                    "dims": (),
                    "attrs": {"long_name": "grdc number"},
                    "data": 42424242,
                },
            },
            "attrs": {
                "title": "MEAN DAILY DISCHARGE (Q)",
                "Conventions": "CF-1.7",
                "references": "grdc.bafg.de",
                "institution": "GRDC",
                "history": "Converted from 42424242_Q_Day.Cmd.txt of 2000-02-02 to netcdf by eWaterCycle Python package",
                "missing_value": "-999.000",
            },
            "dims": {"time": 3},
            "data_vars": {
                "streamflow": {
                    "dims": ("time",),
                    "attrs": {"units": "m3/s", "long_name": "Mean daily discharge (Q)"},
                    "data": [123.0, 456.0, np.nan],
                },
                "area": {
                    "dims": (),
                    "attrs": {"units": "km2", "long_name": "catchment area"},
                    "data": 4242.0,
                },
                "country": {
                    "dims": (),
                    "attrs": {
                        "long_name": "country name",
                        "iso2": "ISO 3166-1 alpha-2 - two-letter country code",
                    },
                    "data": "NA",
                },
                "geo_x": {
                    "dims": (),
                    "attrs": {
                        "units": "degree_east",
                        "long_name": "station longitude (WGS84)",
                    },
                    "data": 4.955153,
                },
                "geo_y": {
                    "dims": (),
                    "attrs": {
                        "units": "degree_north",
                        "long_name": "station latitude (WGS84)",
                    },
                    "data": 52.356154,
                },
                "geo_z": {
                    "dims": (),
                    "attrs": {
                        "units": "m",
                        "long_name": "station altitude (m above sea level)",
                    },
                    "data": 8.0,
                },
                "owneroforiginaldata": {
                    "dims": (),
                    "attrs": {"long_name": "Owner of original data"},
                    "data": "Unknown",
                },
                "river_name": {
                    "dims": (),
                    "attrs": {"long_name": "river name"},
                    "data": "SOME RIVER",
                },
                "station_name": {
                    "dims": (),
                    "attrs": {"long_name": "station name"},
                    "data": "SOME",
                },
                "timezone": {
                    "dims": (),
                    "attrs": {
                        "units": "00:00",
                        "long_name": "utc offset, in relation to the national capital",
                    },
                    "data": np.nan,
                },
            },
        }
    )


def test_get_grdc_data_with_datahome(
    tmp_path, expected_results: xr.Dataset, sample_grdc_file
):
    result_data = get_grdc_data(
        "42424242", "2000-01-01T00:00Z", "2000-02-01T00:00Z", data_home=str(tmp_path)
    )

    assert_allclose(result_data, expected_results)


def test_get_grdc_data_with_cfg(
    expected_results: xr.Dataset, tmp_path, sample_grdc_file
):
    CFG.grdc_location = tmp_path
    result_data = get_grdc_data("42424242", "2000-01-01T00:00Z", "2000-02-01T00:00Z")

    assert_allclose(result_data, expected_results)


def test_get_grdc_data_without_file(tmp_path):
    with pytest.raises(ValueError, match="The grdc file .* does not exist!"):
        get_grdc_data(
            "42424243",
            "2000-01-01T00:00Z",
            "2000-02-01T00:00Z",
            data_home=str(tmp_path),
        )


def test_get_grdc_data_custom_column_name(
    expected_results: xr.Dataset, tmp_path: Path, sample_grdc_file
):
    CFG.grdc_location = tmp_path
    result_data = get_grdc_data(
        "42424242", "2000-01-01T00:00Z", "2000-02-01T00:00Z", column="observation"
    )

    expected_data = expected_results.rename({"streamflow": "observation"})

    assert_allclose(result_data, expected_data)


@pytest.fixture()
def sample_nc_file(tmp_path):
    fn = tmp_path / "GRDC-Daily.nc"
    ds = xr.Dataset.from_dict(
        {
            "coords": {
                "time": {
                    "dims": ("time",),
                    "attrs": {"long_name": "time"},
                    "data": [
                        datetime(2000, 1, 1, 0, 0),
                        datetime(2000, 1, 2, 0, 0),
                        datetime(2000, 1, 3, 0, 0),
                    ],
                },
                "id": {
                    "dims": ("id",),
                    "attrs": {"long_name": "grdc number"},
                    "data": [42424242],
                },
            },
            "attrs": {
                "title": "MEAN DAILY DISCHARGE (Q)",
                "Conventions": "CF-1.7",
                "references": "grdc.bafg.de",
                "institution": "GRDC",
                "history": "Converted from 42424242_Q_Day.Cmd.txt of 2000-02-02 to netcdf by eWaterCycle Python package",
                "missing_value": "-999.000",
            },
            "dims": {"time": 3, "id": 1},
            "data_vars": {
                "runoff_mean": {
                    "dims": ("time", "id"),
                    "attrs": {"units": "m3/s", "long_name": "Mean daily discharge (Q)"},
                    "data": [[123.0], [456.0], [np.nan]],
                },
                "area": {
                    "dims": ("id",),
                    "attrs": {"units": "km2", "long_name": "catchment area"},
                    "data": [4242.0],
                },
                "country": {
                    "dims": ("id",),
                    "attrs": {
                        "long_name": "country name",
                        "iso2": "ISO 3166-1 alpha-2 - two-letter country code",
                    },
                    "data": ["NA"],
                },
                "geo_x": {
                    "dims": ("id",),
                    "attrs": {
                        "units": "degree_east",
                        "long_name": "station longitude (WGS84)",
                    },
                    "data": [4.955153],
                },
                "geo_y": {
                    "dims": ("id",),
                    "attrs": {
                        "units": "degree_north",
                        "long_name": "station latitude (WGS84)",
                    },
                    "data": [52.356154],
                },
                "geo_z": {
                    "dims": ("id",),
                    "attrs": {
                        "units": "m",
                        "long_name": "station altitude (m above sea level)",
                    },
                    "data": [8.0],
                },
                "owneroforiginaldata": {
                    "dims": ("id",),
                    "attrs": {"long_name": "Owner of original data"},
                    "data": ["Unknown"],
                },
                "river_name": {
                    "dims": ("id",),
                    "attrs": {"long_name": "river name"},
                    "data": ["SOME RIVER"],
                },
                "station_name": {
                    "dims": ("id",),
                    "attrs": {"long_name": "station name"},
                    "data": ["SOME"],
                },
                "timezone": {
                    "dims": ("id",),
                    "attrs": {
                        "units": "00:00",
                        "long_name": "utc offset, in relation to the national capital",
                    },
                    "data": [np.nan],
                },
            },
        }
    )
    ds.to_netcdf(fn)
    return str(tmp_path)


def test_get_grdc_data_from_nc(sample_nc_file, expected_results: xr.Dataset):
    result_data = get_grdc_data(
        "42424242", "2000-01-01T00:00Z", "2000-02-01T00:00Z", data_home=sample_nc_file
    )
    assert_allclose(result_data, expected_results)


def test_get_grdc_data_from_nc_missing_and_no_txtfile(tmp_path, sample_nc_file):
    with pytest.raises(
        ValueError,
        match="The grdc station 42424243 is not in the .*/GRDC-Daily.nc file and .*/42424243_Q_Day.Cmd.txt does not exist!",
    ):
        get_grdc_data(
            "42424243",
            "2000-01-01T00:00Z",
            "2000-02-01T00:00Z",
            data_home=str(tmp_path),
        )
