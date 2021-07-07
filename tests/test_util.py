from datetime import datetime, timezone
from pathlib import Path

import pytest

from ewatercycle.util import get_time, find_closest_point, to_absolute_path
from numpy.testing import assert_array_almost_equal


def test_get_time_with_utc():
    dt = get_time('1989-01-02T00:00:00Z')
    assert dt == datetime(1989, 1, 2, tzinfo=timezone.utc)


def test_get_time_with_cet():
    with pytest.raises(ValueError) as excinfo:
        get_time('1989-01-02T00:00:00+01:00')

    assert 'not in UTC' in str(excinfo.value)


def test_get_time_without_tz():
    with pytest.raises(ValueError) as excinfo:
        get_time('1989-01-02T00:00:00')

    assert 'not in UTC' in str(excinfo.value)


def test_find_closest_point():
    expected_distances, expected_index = (
        [[118.77417243, 111.22983323],[122.9552163 , 115.67902656]],
        1)
    actual_distances, actual_index = find_closest_point([-99.83, -99.32], [42.25, 42.21], -99.32, 43.25)
    assert_array_almost_equal(actual_distances, expected_distances)
    assert actual_index == expected_index


def test_to_absolute_path():
    input_path = "~/nonexistent_file.txt"
    parsed = to_absolute_path(input_path)
    expected = Path.home() / "nonexistent_file.txt"
    assert parsed == expected


def test_to_absolute_path_must_exist():
    input_path = "~/nonexistent_file.txt"
    with pytest.raises(ValueError) as excinfo:
        to_absolute_path(input_path, must_exist=True)
    assert "Got non-existent path" in str(excinfo.value)


def test_to_absolute_path_with_absolute_input_and_parent(tmp_path):
    input_path = tmp_path / "nonexistent_file.txt"
    parsed = to_absolute_path(str(input_path), parent = tmp_path)
    assert parsed == input_path


def test_to_absolute_path_with_relative_input_and_parent(tmp_path):
    input_path = "nonexistent_file.txt"
    parsed = to_absolute_path(input_path, parent = tmp_path)
    expected = tmp_path / "nonexistent_file.txt"
    assert parsed == expected


def test_to_absolute_path_with_relative_input_and_relative_parent():
    input_path = "nonexistent_file.txt"
    parsed = to_absolute_path(input_path, parent = Path('.'))
    expected =  Path.cwd() / "nonexistent_file.txt"
    assert parsed == expected
