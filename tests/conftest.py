from pathlib import Path

import pytest

from ewatercycle import CFG


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
def mocked_config(tmp_path):
    CFG["output_dir"] = tmp_path
    CFG["container_engine"] = "apptainer"
    CFG["apptainer_dir"] = tmp_path
    CFG["parameterset_dir"] = tmp_path / "psr"
    CFG["parameter_sets"] = {}
