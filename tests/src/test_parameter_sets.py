from pathlib import Path
from unittest.mock import patch

import pytest

from ewatercycle import CFG
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.parameter_sets import (
    available_parameter_sets,
    download_example_parameter_sets,
    example_parameter_sets,
)


@pytest.fixture()
def setup_config(tmp_path: Path):
    CFG.parameterset_dir = tmp_path
    CFG.parameter_sets = {}
    config_file = tmp_path / "ewatercycle.yaml"
    CFG.save_to_file(config_file)
    CFG.ewatercycle_config = config_file
    yield CFG
    CFG.parameter_sets = {}
    CFG.ewatercycle_config = None
    CFG.reload()


@pytest.fixture()
def mocked_parameterset_dir(setup_config, tmp_path):
    ps1_dir = tmp_path / "ps1"
    ps1_dir.mkdir()
    config1 = ps1_dir / "mymockedconfig1.ini"
    config1.write_text("Something")
    ps2_dir = tmp_path / "ps2"
    ps2_dir.mkdir()
    config2 = ps2_dir / "mymockedconfig2.ini"
    config2.write_text("Something else")
    CFG.parameter_sets = {
        "ps1": {
            "directory": str(ps1_dir),
            "config": str(config1.relative_to(ps1_dir)),
            "target_model": "generic",
            "doi": "somedoi1",
        },
        "ps2": {
            "directory": str(ps2_dir),
            "config": str(config2.relative_to(ps2_dir)),
            "target_model": "generic",
            "doi": "somedoi2",
        },
    }


class TestAvailableParameterSets:
    def test_filled(self, mocked_parameterset_dir):
        names = available_parameter_sets("generic").keys()
        assert set(names) == {
            "ps1",
            "ps2",
        }  # ps3 is filtered due to not being available

    def test_no_sets_in_config(self, setup_config):
        with pytest.raises(ValueError) as excinfo:
            available_parameter_sets()

        assert "No parameter sets defined in" in str(excinfo.value)

    def test_no_sets_for_model(self, mocked_parameterset_dir):
        with pytest.raises(ValueError) as excinfo:
            available_parameter_sets("somemodel")

        assert "No parameter sets defined for somemodel model in" in str(excinfo.value)

    def test_value(self, mocked_parameterset_dir, tmp_path):
        actual = available_parameter_sets()["ps1"]

        assert actual.name == "ps1"
        assert actual.directory == tmp_path / "ps1"
        assert actual.config == tmp_path / "ps1" / "mymockedconfig1.ini"
        assert actual.doi == "somedoi1"
        assert actual.target_model == "generic"


def test_example_parameter_sets(setup_config):
    examples = example_parameter_sets()
    assert examples == {}


@patch.object(ParameterSet, "download")
def test_download_example_parameter_sets(mocked_download, setup_config, tmp_path):
    download_example_parameter_sets()

    assert mocked_download.call_count == 0
    assert CFG.ewatercycle_config.read_text() == CFG.dump_to_yaml()
    assert len(CFG.parameter_sets) == 0
