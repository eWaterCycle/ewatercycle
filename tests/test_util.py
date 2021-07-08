from datetime import datetime, timezone

import pytest

from ewatercycle.util import get_time, find_closest_point
from numpy.testing import assert_array_almost_equal


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
    distance, idx_lon, idx_lat = find_closest_point(
        grid_longitudes=[-99.83, -99.32],
        grid_latitudes=[42.25, 42.21],
        point_longitude=-99.32,
        point_latitude=43.25,
    )
    assert idx_lon == 1
    assert idx_lat == 0
    assert_array_almost_equal(distance, [111.22983323])
