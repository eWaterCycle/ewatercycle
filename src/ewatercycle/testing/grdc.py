"""GRDC functions for testing."""


from pathlib import Path

import pytest

from ewatercycle.observations.grdc import (
    _extract_metadata,
    _grdc_metadata_reader,
    _grdc_read,
)


@pytest.fixture
def grdc_file():
    return Path(__file__).parent / "data" / "test_file_grdc_Q_Day.Cmd.txt"

def test_extract_metadata_str_and_float():
    lines = [
        "# River: TEST RIVER",
        "# Station: TEST STATION (123456)",
        "# Latitude (DD):  12.11111",
    ]
    assert _extract_metadata(lines, "River") == "TEST RIVER"
    assert _extract_metadata(lines, "Station") == "TEST STATION (123456)"
    assert _extract_metadata(lines, "Latitude (DD)", cast=float) == pytest.approx(12.11111)
    assert _extract_metadata(lines, "Country", default="NA") == "NA"

def test_grdc_metadata_reader(grdc_file):
    file_content = grdc_file.read_text(encoding="cp1252")
    metadata = _grdc_metadata_reader(grdc_file, file_content)

    assert metadata["file_generation_date"] == "2025-05-15"
    assert metadata["river_name"] == "TEST RIVER"
    assert metadata["station_name"] == "TEST STATION (123456)"
    assert metadata["country_code"] == "TEST"
    assert metadata["grdc_latitude_in_arc_degree"] == pytest.approx(12.3456789)
    assert metadata["grdc_longitude_in_arc_degree"] == pytest.approx(12.3456789)
    assert metadata["grdc_catchment_area_in_km2"] == pytest.approx(123465.0)
    assert metadata["altitude_masl"] == pytest.approx(1234.0)
    assert metadata["dataSetContent"] == "MEAN DAILY DISCHARGE (Q)"
    assert metadata["units"] == "m³/s"
    assert metadata["Owner of original data"] == "TEST - Ministry of Testing"
    assert metadata["id_from_grdc"] == 123456789
    assert "test_file_grdc_Q_Day.Cmd.txt" in metadata["grdc_file_name"]

def test_grdc_read_dataframe(grdc_file):
    metadata, df = _grdc_read(
        grdc_file,
        start="1942-12-30",
        end="1943-01-05",
        column="streamflow",
    )

    # Metadata sanity check
    assert metadata["river_name"] == "TEST RIVER"

    # DataFrame checks
    assert not df.empty
    assert list(df.index[:3].strftime("%Y-%m-%d")) == ["1942-12-30", "1942-12-31", "1943-01-01"]
    assert df["streamflow"].iloc[0] == 1
    assert df["streamflow"].iloc[-1] == 7  # matches fake file values

def test_missing_metadata_defaults():
    lines = ["# Some unrelated header: VALUE"]
    assert _extract_metadata(lines, "River") == "NA"
    assert _extract_metadata(lines, "River", default="Unknown") == "Unknown"
