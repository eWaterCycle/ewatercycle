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
                "history": "Wed Mar 27 16:11:00 2024: /usr/bin/ncap2 -s time=double(time) -O Caravan/camels.nc Caravan/camels.nc\nMerged together from separate files; All forcing and state variables are derived from ERA5-Land hourly by ECMWF. Streamflow data was taken from the CAMELS (US) dataset by Newman et al. (2014).",
                "NCO": "netCDF Operators version 5.0.6 (Homepage = http://nco.sf.net, Code = http://github.com/nco/nco)",
            },
            "dims": {"time": 3},
            "data_vars": {
                "timezone": {"dims": (), "attrs": {}, "data": b"America/New_York"},
                "name": {
                    "dims": (),
                    "attrs": {},
                    "data": b"FRENCH BROAD RIVER AT ROSMAN, NC",
                },
                "country": {
                    "dims": (),
                    "attrs": {},
                    "data": b"United States of America",
                },
                "lat": {"dims": (), "attrs": {}, "data": 35.14333},
                "lon": {"dims": (), "attrs": {}, "data": -82.82472},
                "area": {"dims": (), "attrs": {}, "data": 177.99471},
                "streamflow": {
                    "dims": ("time",),
                    "attrs": {
                        "unit": "mm/d",
                        "long_name": "Observed streamflow",
                    },
                    "data": [2.266e-06, 2.184e-06, 2.122e-06],
                },
            },
        }
    )
    assert_allclose(ds, expected)
