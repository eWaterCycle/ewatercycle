from datetime import datetime, timezone

import pytest
import numpy as np
import xarray as xr

from ewatercycle.util import get_time, convert_timearray_to_datetime


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

