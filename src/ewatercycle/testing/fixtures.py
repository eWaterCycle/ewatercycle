"""Pytest fixtures for ewatercycle.

To use fixtures importe them in `conftest.py` file.
"""
from pathlib import Path

import pytest

from ewatercycle import CFG
from ewatercycle.config import Configuration


def rhine_shape() -> Path:
    return Path(__file__).parent / "data" / "Rhine" / "Rhine.shp"


@pytest.fixture
def sample_shape():
    return str(rhine_shape())


@pytest.fixture
def mocked_config(tmp_path: Path):
    parameterset_dir = tmp_path / "psr"
    parameterset_dir.mkdir()
    config = Configuration(
        output_dir=tmp_path,
        grdc_location=tmp_path,
        container_engine="apptainer",
        apptainer_dir=tmp_path,
        parameterset_dir=parameterset_dir,
        parameter_sets={},
        ewatercycle_config=None,
    )
    CFG.overwrite(config)
