from pathlib import Path

import pytest

from ewatercycle import CFG
from ewatercycle.base.parameter_set import ParameterSet


class TestDefaults:
    @pytest.fixture
    def mocked_ps_config(self, tmp_path):
        CFG.parameterset_dir = tmp_path
        config = tmp_path / "mymockedconfig.ini"
        config.write_text("Something")
        return config

    @pytest.fixture
    def parameter_set(self, tmp_path, mocked_ps_config: Path):
        return ParameterSet(
            name="justatest",
            directory=tmp_path,
            config=mocked_ps_config,
        )

    def test_directory(self, parameter_set: ParameterSet, tmp_path):
        assert parameter_set.directory == tmp_path

    def test_config(self, parameter_set: ParameterSet, mocked_ps_config):
        assert parameter_set.config == mocked_ps_config

    def test_supported_model_versions(self, parameter_set: ParameterSet):
        assert parameter_set.supported_model_versions == set()

    def test_str(self, parameter_set: ParameterSet, tmp_path):
        expected = (
            "Parameter set\n"
            "-------------\n"
            "name=justatest\n"
            f"directory={tmp_path!s}\n"
            f"config={tmp_path!s}/mymockedconfig.ini\n"
            "doi=N/A\n"
            "target_model=generic\n"
            "supported_model_versions=set()\n"
            "downloader=None"
        )
        assert str(parameter_set) == expected


class TestOutsideCFG:
    @pytest.fixture
    def mocked_ps_config(self, tmp_path):
        parameterset_dir = tmp_path / "parameter-sets"
        parameterset_dir.mkdir()
        CFG.parameterset_dir = parameterset_dir
        config = tmp_path / "mymockedconfig.ini"
        config.write_text("Something")
        return config

    @pytest.fixture
    def parameter_set(self, tmp_path, mocked_ps_config: Path):
        return ParameterSet(
            name="justatest",
            directory=str(tmp_path / "my-parameter-set"),
            config=mocked_ps_config.name,
        )

    def test_directory(self, parameter_set: ParameterSet, tmp_path):
        assert parameter_set.directory == tmp_path / "my-parameter-set"
