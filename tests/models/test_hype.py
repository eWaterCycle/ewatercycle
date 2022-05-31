import pytest

from ewatercycle import CFG
from ewatercycle.models.hype import Hype
from ewatercycle.parameter_sets import ParameterSet


@pytest.fixture
def mocked_config(tmp_path):
    CFG["output_dir"] = tmp_path
    CFG["container_engine"] = "singularity"
    CFG["singularity_dir"] = tmp_path
    CFG["parameterset_dir"] = tmp_path / "psr"
    CFG["parameter_sets"] = {}


@pytest.fixture
def parameter_set(tmp_path, mocked_config):
    directory = tmp_path / "hype_testcase"
    config = directory / "info.txt"
    # TODO write info.txt
    # TODO write some parameter file
    # TODO write forcing files as part of parameter set
    return ParameterSet(
        "hype_testcase",
        directory=str(directory),
        config=str(config),
        target_model="hype",
    )


@pytest.fixture
def model(parameter_set):
    return Hype("feb2021", parameter_set)


def test_parameters(model):
    expected = []
    assert model.parameters == expected
