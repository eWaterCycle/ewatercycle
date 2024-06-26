import datetime
from pathlib import Path
from unittest import mock

import pytest
import xarray as xr
from xarray.testing import assert_allclose

from ewatercycle.observation.caravan import get_caravan_data


@pytest.fixture
def mock_retrieve():
    with mock.patch(
        "ewatercycle._forcings.caravan.CaravanForcing.get_dataset"
    ) as mock_class:
        test_file = (
            Path(__file__).parent.parent
            / "base"
            / "forcing_files"
            / "test_caravan_file.nc"
        )
        mock_class.return_value = xr.open_dataset(test_file)
        yield mock_class


def test_get_caravan_data(mock_retrieve):
    ds = get_caravan_data(
        basin_id="camels_03439000",
        start_time="1981-01-01T00:00:00Z",
        end_time="1981-01-03T00:00:00Z",
    )
    expected = xr.Dataset.from_dict(
        {
            "coords": {
                "time": {
                    "dims": ("time",),
                    "attrs": {},
                    "data": [
                        datetime.datetime(1981, 1, 1, 0, 0),
                        datetime.datetime(1981, 1, 2, 0, 0),
                        datetime.datetime(1981, 1, 3, 0, 0),
                    ],
                },
                "basin_id": {"dims": (), "attrs": {}, "data": b"camels_03439000"},
            },
            "attrs": {
                "history": "Wed Mar 27 16:11:00 2024: /usr/bin/ncap2 -s time=double(time) -O Caravan/camels.nc Caravan/camels.nc\nMerged together from separate files; All forcing and state variables are derived from ERA5-Land hourly by ECMWF. Streamflow data was taken from the CAMELS (US) dataset by Newman et al. (2014).",  # noqa
                "NCO": "netCDF Operators version 5.0.6 (Homepage = http://nco.sf.net, Code = http://github.com/nco/nco)",  # noqa
            },
            "dims": {"time": 3},
            "data_vars": {
                "streamflow": {
                    "dims": ("time",),
                    "attrs": {
                        "unit": "mm/d",
                        "long_name": "Observed streamflow",
                    },
                    "data": [1.100000023841858, 1.059999942779541, 1.0299999713897705],
                }
            },
        }
    )
    assert_allclose(ds, expected)
