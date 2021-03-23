from datetime import datetime

import pytest
import xarray as xa
import numpy as np
from xarray.testing import assert_equal

from ewatercycle.observation.grdc import get_grdc_data


@pytest.fixture
def sample_grdc_file(tmp_path):
    fn = tmp_path / '42424242_Q_Day.Cmd.txt'
    # Sample with fictive data, but with same structure as real file
    s = '''# Title:                 GRDC STATION DATA FILE
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
# Catchment area (km�):      4242.0
# Altitude (m ASL):        8.0
# Next downstream station:      42424243
# Remarks:
#************************************************************
#
# Data Set Content:      MEAN DAILY DISCHARGE (Q)
#                        --------------------
# Unit of measure:                  m�/s
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
2000-01-03;--:--;    -999.000'''
    with open(fn, 'w') as f:
        f.write(s)
    return fn


def test_get_grdc_data(tmp_path, sample_grdc_file):
    result = get_grdc_data('42424242', '2000-01-01', '2000-02-01', data_home=tmp_path)

    expected = xa.Dataset(
        {'streamflow': ('time', [123., 456., np.nan])},
        coords={'time': [datetime(2000, 1, 1), datetime(2000, 1, 2), datetime(2000, 1, 3)]},
        attrs={
            'altitude_masl': 8.0,
            'country_code': 'NA',
            'dataSetContent': 'MEAN DAILY DISCHARGE (Q)',
            'file_generation_date': '2000-02-02',
            'grdc_catchment_area_in_km2': 4242.0,
            'grdc_file_name': str(tmp_path / sample_grdc_file),
            'grdc_latitude_in_arc_degree': 52.356154,
            'grdc_longitude_in_arc_degree': 4.955153,
            'id_from_grdc': 42424242,
            'last_update': '2000-02-01',
            'no_of_years': 1,
            'nrMeasurements': 'NA',
            'river_name': 'SOME RIVER',
            'station_name': 'SOME',
            'time_series': '2000-01 - 2000-01',
            'units': 'm�/s'
        }
    )

    assert_equal(result, expected)
    assert result.attrs == expected.attrs
