from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ewatercycle import CFG
from ewatercycle.observation.grdc import get_grdc_data


@pytest.fixture
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
2000-01-03;--:--;    -999.000"""  # noqa: E800
    with fn.open("w", encoding="cp1252") as f:
        f.write(body)
    return fn


@pytest.fixture
def expected_results(tmp_path, sample_grdc_file):
    data = pd.DataFrame(
        {"streamflow": [123.0, 456.0, np.NaN]},
        index=[datetime(2000, 1, 1), datetime(2000, 1, 2), datetime(2000, 1, 3)],
    )
    data.index.rename("time", inplace=True)
    global_metadata = {
        "altitude_masl": 8.0,
        "country_code": "NA",
        "file_generation_date": "2000-02-02",
        "grdc_catchment_area_in_km2": 4242.0,
        "grdc_file_name": str(tmp_path / sample_grdc_file),
        "grdc_latitude_in_arc_degree": 52.356154,
        "grdc_longitude_in_arc_degree": 4.955153,
        "id_from_grdc": 42424242,
        "last_update": "2000-02-01",
        "no_of_years": 1,
        "nrMeasurements": 3,
        "river_name": "SOME RIVER",
        "station_name": "SOME",
        "time_series": "2000-01 - 2000-01",
        "UserEndTime": "2000-02-01T00:00Z",
        "UserStartTime": "2000-01-01T00:00Z",
        "nrMissingData": 1,
    }
    var_metadata = {
        "long_name": "MEAN DAILY DISCHARGE (Q)",
        "units": "m³/s",
    }
    return data, global_metadata, var_metadata


def test_get_grdc_data_with_datahome(tmp_path, expected_results):
    expected_data, expected_metadata, expected_var_metadata = expected_results
    result_data = get_grdc_data(
        "42424242", "2000-01-01T00:00Z", "2000-02-01T00:00Z", data_home=str(tmp_path)
    )

    assert_frame_equal(result_data.to_dataframe(), expected_data)
    assert result_data.attrs == expected_metadata
    assert result_data["streamflow"].attrs == expected_var_metadata


def test_get_grdc_data_with_cfg(expected_results, tmp_path):
    CFG.grdc_location = tmp_path
    expected_data, expected_metadata, expected_var_metadata = expected_results
    result_data = get_grdc_data("42424242", "2000-01-01T00:00Z", "2000-02-01T00:00Z")

    assert_frame_equal(result_data.to_dataframe(), expected_data)
    assert result_data.attrs == expected_metadata
    assert result_data["streamflow"].attrs == expected_var_metadata


def test_get_grdc_data_without_file(tmp_path):
    with pytest.raises(ValueError, match="The grdc file .* does not exist!"):
        get_grdc_data(
            "42424243",
            "2000-01-01T00:00Z",
            "2000-02-01T00:00Z",
            data_home=str(tmp_path),
        )


def test_get_grdc_dat_custom_column_name(expected_results, tmp_path):
    CFG.grdc_location = str(tmp_path)
    result_data = get_grdc_data(
        "42424242", "2000-01-01T00:00Z", "2000-02-01T00:00Z", column="observation"
    )

    expected_default_data, expected_metadata, expected_var_metadata = expected_results
    expected_data = expected_default_data.rename(columns={"streamflow": "observation"})
    assert_frame_equal(result_data.to_dataframe(), expected_data)
    assert result_data.attrs == expected_metadata
    assert result_data["observation"].attrs == expected_var_metadata
