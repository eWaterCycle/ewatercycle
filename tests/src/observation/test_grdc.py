from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from xarray.testing import assert_allclose

from ewatercycle import CFG
from ewatercycle.observations.grdc import (
    get_grdc_data,
    _extract_metadata,
    _grdc_metadata_reader,
    _grdc_read,
)


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

@pytest.fixture
def grdc_file():
    return Path(__file__).parent / "data" / "test_file_grdc_Q_Day.Cmd.txt"

def test_extract_metadata_str_and_float():
    lines = [
        "# River: TEST RIVER",
        "# Station: TEST STATION (123456)",
        "# Latitude (DD):  12.11111",
    ]
    assert_allclose(_extract_metadata(lines, "River"),"TEST RIVER")
    assert _extract_metadata(lines, "Station") == "TEST STATION (123456)"
    assert _extract_metadata(lines, "Latitude (DD)", cast=float) == pytest.approx(12.11111)
    assert _extract_metadata(lines, "Country", default="NA") == "NA"

def test_grdc_metadata_reader(grdc_file):
    file_content = grdc_file.read_text(encoding="cp1252")
    metadata = _grdc_metadata_reader(grdc_file, file_content)

    assert metadata["file_generation_date"] == "2025-05-15"
    assert metadata["river_name"] == "TEST RIVER"
    assert metadata["station_name"] == "TEST STATION (123456)"
    assert metadata["country_code"] == "TEST"
    assert metadata["grdc_latitude_in_arc_degree"] == pytest.approx(12.3456789)
    assert metadata["grdc_longitude_in_arc_degree"] == pytest.approx(12.3456789)
    assert metadata["grdc_catchment_area_in_km2"] == pytest.approx(123465.0)
    assert metadata["altitude_masl"] == pytest.approx(1234.0)
    assert metadata["dataSetContent"] == "MEAN DAILY DISCHARGE (Q)"
    assert metadata["units"] == "m³/s"
    assert metadata["Owner of original data"] == "TEST - Ministry of Testing"
    assert metadata["id_from_grdc"] == 123456789
    assert "test_file_grdc_Q_Day.Cmd.txt" in metadata["grdc_file_name"]

def test_grdc_read_dataframe(grdc_file):
    metadata, df = _grdc_read(
        grdc_file,
        start="1942-12-30",
        end="1943-01-05",
        column="streamflow",
    )

    # Metadata sanity check
    assert metadata["river_name"] == "TEST RIVER"

    # DataFrame checks
    assert not df.empty
    assert list(df.index[:3].strftime("%Y-%m-%d")) == ["1942-12-30", "1942-12-31", "1943-01-01"]
    assert df["streamflow"].iloc[0] == 1
    assert df["streamflow"].iloc[-1] == 7  # matches fake file values

def test_missing_metadata_defaults():
    lines = ["# Some unrelated header: VALUE"]
    assert _extract_metadata(lines, "River") == "NA"
    assert _extract_metadata(lines, "River", default="Unknown") == "Unknown"