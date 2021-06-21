import pytest

from ewatercycle import CFG
from ewatercycle.parameter_sets import available_parameter_sets, get_parameter_set


@pytest.fixture
def mocked_parameterset_dir(tmp_path):
    CFG['parameterset_dir'] = tmp_path
    ps1_dir = tmp_path / 'ps1'
    ps1_dir.mkdir()
    config1 = ps1_dir / 'mymockedconfig1.ini'
    config1.write_text('Something')
    ps2_dir = tmp_path / 'ps2'
    ps2_dir.mkdir()
    config2 = ps2_dir / 'mymockedconfig2.ini'
    config2.write_text('Something else')
    CFG['parameter_sets'] = {
        'ps1': {
            'directory': str(ps1_dir),
            'config': str(config1.relative_to(tmp_path)),
            'target_model': 'generic',
            'doi': 'somedoi1'
        },
        'ps2': {
            'directory': str(ps2_dir),
            'config': str(config2.relative_to(tmp_path)),
            'target_model': 'generic',
            'doi': 'somedoi2'
        },
        'ps3': {
            'directory': str(tmp_path / 'ps3'),
            'config': 'unavailable_config_file',
            'target_model': 'generic',
            'doi': 'somedoi3'
        }
    }


def test_available_parameter_sets(mocked_parameterset_dir):
    names = available_parameter_sets('generic')
    assert set(names) == {'ps1', 'ps2'}  # ps3 is filtered due to not being available


class TestGetParameterSet:

    def test_valid(self, mocked_parameterset_dir, tmp_path):
        actual = get_parameter_set('ps1')

        assert actual.name == 'ps1'
        assert actual.directory == tmp_path / 'ps1'
        assert actual.config == tmp_path / 'ps1' / 'mymockedconfig1.ini'
        assert actual.doi == 'somedoi1'
        assert actual.target_model == 'generic'

    def test_unknown(self, mocked_parameterset_dir):
        with pytest.raises(KeyError):
            get_parameter_set('ps9999')

    def test_unavailable(self, mocked_parameterset_dir):
        with pytest.raises(ValueError):
            get_parameter_set('ps3')
