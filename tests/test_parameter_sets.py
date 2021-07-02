from unittest.mock import patch

import pytest

from ewatercycle import CFG
from ewatercycle.config import DEFAULT_CONFIG
from ewatercycle.parameter_sets import available_parameter_sets, get_parameter_set, example_parameter_sets, \
    download_example_parameter_sets, ExampleParameterSet


@pytest.fixture
def setup_config(tmp_path):
    CFG['parameterset_dir'] = tmp_path
    CFG['ewatercycle_config'] = tmp_path / 'ewatercycle.yaml'
    yield CFG
    CFG['ewatercycle_config'] = DEFAULT_CONFIG
    CFG.reload()


@pytest.fixture
def mocked_parameterset_dir(setup_config, tmp_path):
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


class TestAvailableParameterSets:
    def test_filled(self, mocked_parameterset_dir):
        names = available_parameter_sets('generic')
        assert set(names) == {'ps1', 'ps2'}  # ps3 is filtered due to not being available

    def test_no_config(self, tmp_path):
        # Load default config shipped with package
        CFG['ewatercycle_config'] = DEFAULT_CONFIG
        CFG.reload()

        with pytest.raises(ValueError) as excinfo:
            available_parameter_sets()

        assert 'No configuration file found' in str(excinfo.value)

    def test_no_sets_in_config(self, setup_config):
        with pytest.raises(ValueError) as excinfo:
            available_parameter_sets()

        assert 'No parameter sets defined in' in str(excinfo.value)

    def test_no_sets_for_model(self, mocked_parameterset_dir):
        with pytest.raises(ValueError) as excinfo:
            available_parameter_sets('somemodel')

        assert 'No parameter sets defined for somemodel model in' in str(excinfo.value)


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


def test_example_parameter_sets(setup_config):
    examples = example_parameter_sets()
    assert len(list(examples)) > 0
    for name in examples:
        assert name == examples[name].name


@patch.object(ExampleParameterSet, 'download')
def test_download_example_parameter_sets(mocked_download, setup_config, tmp_path):
    download_example_parameter_sets()

    assert mocked_download.call_count > 0
    assert CFG['ewatercycle_config'].read_text() == CFG.dump_to_yaml()
    assert len(CFG['parameter_sets']) > 0
