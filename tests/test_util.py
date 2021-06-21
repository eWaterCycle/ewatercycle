from datetime import datetime, timezone

import pytest

from ewatercycle.util import get_time, find_closest_point
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
    actual_distances, actual_index = (
        [[118.77417243, 111.22983323],[122.9552163 , 115.67902656]],
        1)
    expected_distances, expected_index = find_closest_point([-99.83, -99.32], [42.25, 42.21], -99.32, 43.25)
    assert_array_almost_equal(actual_distances, expected_distances)
    assert actual_index == expected_index
