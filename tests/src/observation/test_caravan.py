import datetime
from pathlib import Path
from unittest import mock

import numpy as np
import pytest
import xarray as xr
from xarray.testing import assert_allclose

from ewatercycle.observation.caravan import get_caravan_data


@pytest.fixture()
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
                "basin_id": {
                    "dims": ("basin_id",),
                    "attrs": {},
                    "data": [b"camels_03439000", b"camels_03439000"],
                },
                "data_source": {
                    "dims": ("data_source",),
                    "attrs": {},
                    "data": [b"era5_land", b"nldas", b"maurer", b"daymet"],
                },
            },
            "attrs": {
                "title": "Basin mean forcing data for ",
                "history": "Thu Jun 13 15:42:28 2024: /usr/local/bin/ncap2 -s time=double(time) -O a/500dc8bd-c096-404c-a1c8-182249c621f4.nc a/500dc8bd-c096-404c-a1c8-182249c621f4.nc\nConverted to netCDF by David Haasnoot for eWatercycle using CAMELS and combined with merged Caravan dataset",
                "data_source_camels": "CAMELS-USA was compiled by A. Newman et al. `A large-sample watershed-scale hydrometeorological dataset for the contiguous USA` using daymet, nldas and maurer",
                "data_source_caravan": "The Caravan dataset by F. Kratzert et al `Caravan - A global community dataset for large-sample hydrology` uses era5 data",
                "url_source_data_camels": "https://dx.doi.org/10.5065/D6MW2F4D",
                "url_source_data_caravan": "https://doi.org/10.1038/s41597-023-01975-w",
                "NCO": "netCDF Operators version 5.2.4 (Homepage = http://nco.sf.net, Code = http://github.com/nco/nco, Citation = 10.1016/j.envsoft.2008.03.004)",
                "_NCProperties": "version=2,netcdf=4.9.2,hdf5=1.12.2",
                "DODS.strlen": 9,
                "DODS.dimName": "string9",
            },
            "dims": {"data_source": 4, "basin_id": 2, "time": 3},
            "data_vars": {
                "timezone": {
                    "dims": ("data_source", "basin_id"),
                    "attrs": {},
                    "data": [
                        [b"America/New_York", b"nan"],
                        [b"nan", b"nan"],
                        [b"nan", b"nan"],
                        [b"nan", b"nan"],
                    ],
                },
                "name": {
                    "dims": ("data_source", "basin_id"),
                    "attrs": {},
                    "data": [
                        [b"FRENCH BROAD RIVER AT ROSMAN, NC", b"nan"],
                        [b"nan", b"nan"],
                        [b"nan", b"nan"],
                        [b"nan", b"nan"],
                    ],
                },
                "country": {
                    "dims": ("data_source", "basin_id"),
                    "attrs": {},
                    "data": [
                        [b"United States of America", b"nan"],
                        [b"nan", b"nan"],
                        [b"nan", b"nan"],
                        [b"nan", b"nan"],
                    ],
                },
                "lat": {
                    "dims": ("data_source", "basin_id"),
                    "attrs": {"_ChunkSizes": [4, 1153]},
                    "data": [
                        [35.14333, np.nan],
                        [np.nan, np.nan],
                        [np.nan, np.nan],
                        [np.nan, np.nan],
                    ],
                },
                "lon": {
                    "dims": ("data_source", "basin_id"),
                    "attrs": {"_ChunkSizes": [4, 1153]},
                    "data": [
                        [-82.82472, np.nan],
                        [np.nan, np.nan],
                        [np.nan, np.nan],
                        [np.nan, np.nan],
                    ],
                },
                "area": {
                    "dims": ("data_source", "basin_id"),
                    "attrs": {"_ChunkSizes": [4, 1153]},
                    "data": [
                        [177.99471516630686, np.nan],
                        [np.nan, np.nan],
                        [np.nan, np.nan],
                        [np.nan, np.nan],
                    ],
                },
                "streamflow": {
                    "dims": ("data_source", "basin_id", "time"),
                    "attrs": {"unit": "m3/s"},
                    "data": [
                        [
                            [
                                2.266136469058591e-06,
                                2.183731341335023e-06,
                                2.121927679731787e-06,
                            ],
                            [np.nan, np.nan, np.nan],
                        ],
                        [[np.nan, np.nan, np.nan], [np.nan, np.nan, np.nan]],
                        [[np.nan, np.nan, np.nan], [np.nan, np.nan, np.nan]],
                        [[np.nan, np.nan, np.nan], [np.nan, np.nan, np.nan]],
                    ],
                },
            },
        }
    )
    assert_allclose(ds, expected)
