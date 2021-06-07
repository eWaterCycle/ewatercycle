from datetime import datetime, timezone
from pathlib import Path

import pytest

from ewatercycle.util import get_time, parse_path


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


def test_parse_path():
    input_path = "~/nonexistent_file.txt"
    parsed = parse_path(input_path)
    expected = Path.home() / "nonexistent_file.txt"
    assert parsed == expected


def test_parse_path_must_exist():
    input_path = "~/nonexistent_file.txt"
    with pytest.raises(ValueError) as excinfo:
        parse_path(input_path, must_exist=True)
    assert "Got non-existent path" in str(excinfo.value)


def test_parse_path_invalid():
    with pytest.raises(ValueError) as excinfo:
        parse_path(123)
    assert "Tried to parse input path" in str(excinfo.value)
