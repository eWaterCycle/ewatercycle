from datetime import datetime, timezone
from pathlib import Path

import pytest
from numpy.testing import assert_array_almost_equal

from ewatercycle.util import find_closest_point, get_time, to_absolute_path


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
    parsed = to_absolute_path(input_path, parent=Path("."))
    expected = Path.cwd() / "nonexistent_file.txt"
    assert parsed == expected


def test_to_absolute_path_with_absolute_input_and_nonrelative_parent(tmp_path):
    parent = tmp_path / "parent_dir"
    input_path = tmp_path / "nonexistent_file.txt"

    with pytest.raises(ValueError) as excinfo:
        to_absolute_path(str(input_path), parent=parent)

    assert "is not a subpath of parent" in str(excinfo.value)
