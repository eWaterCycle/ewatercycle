from datetime import datetime, timezone
from pathlib import Path

import pytest
import xarray as xr
from numpy.testing import assert_array_equal

from ewatercycle.util import (
    find_closest_point,
    fit_extents_to_grid,
    get_time,
    merge_esvmaltool_datasets,
    reindex,
    to_absolute_path,
)


def test_get_time_with_utc():
    dt = get_time("1989-01-02T00:00:00Z")
    assert dt == datetime(1989, 1, 2, tzinfo=timezone.utc)


def test_get_time_with_cet():
    with pytest.raises(ValueError) as excinfo:
        get_time("1989-01-02T00:00:00+01:00")

    assert "not in UTC" in str(excinfo.value)


def test_get_time_without_tz():
    with pytest.raises(ValueError) as excinfo:
        get_time("1989-01-02T00:00:00")

    assert "not in UTC" in str(excinfo.value)


def test_find_closest_point():
    idx_lon, idx_lat = find_closest_point(
        grid_longitudes=[-99.83, -99.32],
        grid_latitudes=[42.25, 42.21],
        point_longitude=-99.32,
        point_latitude=43.25,
    )
    assert idx_lon == 1
    assert idx_lat == 0


def test_to_absolute_path():
    input_path = "~/nonexistent_file.txt"
    parsed = to_absolute_path(input_path)
    expected = Path.home() / "nonexistent_file.txt"
    assert parsed == expected


def test_to_absolute_path_must_exist():
    input_path = "~/nonexistent_file.txt"
    with pytest.raises(FileNotFoundError):
        to_absolute_path(input_path, must_exist=True)


def test_to_absolute_path_with_absolute_input_and_parent(tmp_path):
    input_path = tmp_path / "nonexistent_file.txt"
    parsed = to_absolute_path(str(input_path), parent=tmp_path)
    assert parsed == input_path


def test_to_absolute_path_with_relative_input_and_parent(tmp_path):
    input_path = "nonexistent_file.txt"
    parsed = to_absolute_path(input_path, parent=tmp_path)
    expected = tmp_path / "nonexistent_file.txt"
    assert parsed == expected


def test_to_absolute_path_with_relative_input_and_no_parent():
    input_path = "nonexistent_file.txt"
    parsed = to_absolute_path(input_path)
    expected = Path.cwd() / "nonexistent_file.txt"
    assert parsed == expected


def test_to_absolute_path_with_relative_input_and_relative_parent():
    input_path = "nonexistent_file.txt"
    parsed = to_absolute_path(input_path, parent=Path())
    expected = Path.cwd() / "nonexistent_file.txt"
    assert parsed == expected


def test_to_absolute_path_with_absolute_input_and_nonrelative_parent(tmp_path):
    parent = tmp_path / "parent_dir"
    input_path = tmp_path / "nonexistent_file.txt"

    with pytest.raises(ValueError) as excinfo:
        to_absolute_path(str(input_path), parent=parent)

    assert "is not a subpath of parent" in str(excinfo.value)


def test_reindex(tmp_path):
    expected_source = xr.DataArray(
        data=[[1.0, 2.0], [3.0, 4.0]],
        coords={
            "longitude": [19.35, 19.45],
            "latitude": [-33.05, -33.15],
            "time": "2014-09-06",
        },
        dims=["longitude", "latitude"],
        name="tas",
        attrs={"units": "degC"},
    )
    expected_source.to_netcdf(f"{tmp_path}/tas.nc")
    expected_mask = xr.DataArray(
        data=[
            [False, True, True, True, True],
            [False, False, True, True, True],
            [False, False, True, False, True],
            [False, False, False, False, False],
            [False, False, False, False, False],
        ],
        coords={
            "longitude": [19.05, 19.15, 19.25, 19.35, 19.45],
            "latitude": [-33.05, -33.15, -33.25, -33.35, -33.45],
        },
    )
    expected_mask.to_netcdf(f"{tmp_path}/mask.nc")
    reindex(
        f"{tmp_path}/tas.nc",
        "tas",
        f"{tmp_path}/mask.nc",
        f"{tmp_path}/tas_global.nc",
    )
    reindexed_data = xr.open_dataset(f"{tmp_path}/tas_global.nc")
    # Check coords
    assert_array_equal(
        reindexed_data["latitude"].values, expected_mask["latitude"].values
    )
    assert_array_equal(
        reindexed_data["longitude"].values, expected_mask["longitude"].values
    )

    # Check values based on coords values
    reindexed_val = (
        reindexed_data["tas"].sel(latitude=-33.05, longitude=19.35).to_numpy()
    )
    expected_val = expected_source.sel(latitude=-33.05, longitude=19.35).to_numpy()
    assert reindexed_val == expected_val

    # Check values based on coords indices
    reindexed_val = reindexed_data["tas"].isel(latitude=1, longitude=4).to_numpy()
    expected_val = expected_source.isel(latitude=1, longitude=1).to_numpy()
    assert reindexed_val == expected_val


def test_reindex_baddimsname(tmp_path):
    expected_source = xr.DataArray(
        data=[[1.0, 2.0], [3.0, 4.0]],
        coords={
            "longitude": [19.35, 19.45],
            "latitude": [-33.05, -33.15],
            "time": "2014-09-06",
        },
        dims=["longitude", "latitude"],
        name="tas",
        attrs={"units": "degC"},
    )
    expected_source.to_netcdf(f"{tmp_path}/tas.nc")
    expected_mask = xr.DataArray(
        data=[
            [False, True, True, True, True],
            [False, False, True, True, True],
            [False, False, True, False, True],
            [False, False, False, False, False],
            [False, False, False, False, False],
        ],
        coords={
            "leftright": [19.05, 19.15, 19.25, 19.35, 19.45],
            "updown": [-33.05, -33.15, -33.25, -33.35, -33.45],
        },
    )
    expected_mask.to_netcdf(f"{tmp_path}/mask.nc")
    with pytest.raises(
        ValueError, match="Bad naming of dimensions in source_file and mask_file"
    ):
        reindex(
            f"{tmp_path}/tas.nc",
            "tas",
            f"{tmp_path}/mask.nc",
            f"{tmp_path}/tas_global.nc",
        )


class TestFitExtents2Map:
    @pytest.mark.parametrize(
        "extents, expected",
        [
            [
                {
                    "start_longitude": 4.1,
                    "start_latitude": 46.3,
                    "end_longitude": 11.9,
                    "end_latitude": 52.2,
                },
                {
                    "start_longitude": 4.05,
                    "start_latitude": 46.25,
                    "end_longitude": 11.95,
                    "end_latitude": 52.25,
                },
            ],
            [
                {
                    "start_longitude": -76.101,
                    "start_latitude": 40.395,
                    "end_longitude": -73.664,
                    "end_latitude": 41.951,
                },
                {
                    "start_longitude": -76.15,
                    "start_latitude": 40.35,
                    "end_longitude": -73.65,
                    "end_latitude": 42.05,
                },
            ],
        ],
    )
    def test_defaults(self, extents, expected):
        result = fit_extents_to_grid(extents)
        assert result == expected


@pytest.fixture(scope="function")
def esmvaltool_output() -> list[xr.Dataset]:
    files = list((Path(__file__).parent / "esmvaltool" / "files").glob("*.nc"))
    return [xr.open_dataset(file, chunks="auto") for file in files]


def test_merge_esmvaltool_datasets(esmvaltool_output):
    ds = merge_esvmaltool_datasets(esmvaltool_output)
    for var in ["tas", "pr", "rsds"]:
        assert not ds[var].mean(dim=["lat", "lon"]).isnull().any("time")

    assert "height" in ds["tas"].attrs
    assert "lat_bnds" in ds  # ensure bounds are present
    assert "lon_bnds" in ds
    assert ds["tas"].chunks is not None  # ensure that it's a dask array


def test_merge_datasets_multivar(esmvaltool_output):
    for i in range(len(esmvaltool_output)):
        if "tas" in esmvaltool_output[i]:  # tas has height attribute
            esmvaltool_output[i]["second_var"] = esmvaltool_output[i]["tas"] + 1
    with pytest.raises(ValueError, match="More than one variable found in dataset"):
        merge_esvmaltool_datasets(esmvaltool_output)
