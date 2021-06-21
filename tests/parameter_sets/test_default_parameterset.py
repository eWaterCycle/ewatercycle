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
    def parameter_set(self, tmp_path, mocked_config):
        return ParameterSet(
            name='justatest',
            directory=str(tmp_path),
            config='mymockedconfig.ini'
        )

    def test_directory(self, parameter_set: ParameterSet, tmp_path):
        assert parameter_set.directory == tmp_path

    def test_config(self, parameter_set: ParameterSet, mocked_config):
        assert parameter_set.config == mocked_config

    def test_is_available(self, parameter_set: ParameterSet):
        assert parameter_set.is_available
