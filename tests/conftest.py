from pathlib import Path

import pytest

from ewatercycle import CFG
from ewatercycle.config import Configuration


@pytest.fixture
def sample_shape():
    return str(
        Path(__file__).parents[1] / "docs" / "examples" / "data" / "Rhine" / "Rhine.shp"
    )


@pytest.fixture
def sample_marrmot_forcing_file():
    # Downloaded from
    # https://github.com/wknoben/MARRMoT/blob/master/BMI/Config/BMI_testcase_m01_BuffaloRiver_TN_USA.mat
    return str(
        Path(__file__).parent
        / "models"
        / "data"
        / "BMI_testcase_m01_BuffaloRiver_TN_USA.mat"
    )


@pytest.fixture
def sample_lisvap_config():
    return str(Path(__file__).parent / "forcing" / "data" / "settings_lisvap.xml")


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
