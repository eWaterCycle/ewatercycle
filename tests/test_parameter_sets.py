import pytest

from ewatercycle import CFG
from ewatercycle.parameter_sets import available_parameter_sets


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
            'directory': ps1_dir,
            'config': config1.relative_to(tmp_path),
            'target_model': 'generic',
            'doi': 'N/A'
        },
        'ps2': {
            'directory': ps2_dir,
            'config': config2.relative_to(tmp_path),
            'target_model': 'generic',
            'doi': 'N/A'
        }
    }


def test_available_parameter_sets(mocked_parameterset_dir):
    names = available_parameter_sets('generic')
    assert set(names) == {'ps1', 'ps2'}
