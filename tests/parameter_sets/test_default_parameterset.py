from pathlib import Path

import pytest

from ewatercycle import CFG
from ewatercycle.parameter_sets import ParameterSet


@pytest.fixture
def mocked_config(tmp_path):
    CFG['parameterset_dir'] = tmp_path
    config = tmp_path / 'mymockedconfig.ini'
    config.write_text('Something')
    return config


class TestDefaults:
    @pytest.fixture
    def parameter_set(self, tmp_path, mocked_config: Path):
        return ParameterSet(
            name='justatest',
            directory=str(tmp_path),
            config=mocked_config.name,
        )

    def test_directory(self, parameter_set: ParameterSet, tmp_path):
        assert parameter_set.directory == tmp_path

    def test_config(self, parameter_set: ParameterSet, mocked_config):
        assert parameter_set.config == mocked_config

    def test_supported_model_versions(self, parameter_set: ParameterSet):
        assert parameter_set.supported_model_versions == set()

    def test_is_available(self, parameter_set: ParameterSet):
        assert parameter_set.is_available

    def test_repr(self, parameter_set: ParameterSet, tmp_path):
        expected = (
            "ParameterSet(name=justatest, "
            f"directory={str(tmp_path)}, "
            f"config={str(tmp_path)}/mymockedconfig.ini, "
            "doi=N/A, target_model=generic, supported_model_versions=set())"
        )
        assert repr(parameter_set) == expected

    def test_str(self, parameter_set: ParameterSet, tmp_path):
        expected = (
            'Parameter set\n'
            '-------------\n'
            "name=justatest\n"
            f"directory={str(tmp_path)}\n"
            f"config={str(tmp_path)}/mymockedconfig.ini\n"
            "doi=N/A\n"
            "target_model=generic\n"
            "supported_model_versions=set()"
        )
        assert str(parameter_set) == expected
