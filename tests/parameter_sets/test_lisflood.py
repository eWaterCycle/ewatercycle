import pytest
from ewatercycle.parameter_sets._lisflood import LisfloodParameterSet

from ewatercycle.parameter_sets import get_parameter_set

from ewatercycle import CFG
from ewatercycle.config._config_object import DEFAULT_CONFIG


@pytest.fixture
def setup_config(tmp_path):
    CFG['parameterset_dir'] = tmp_path
    CFG['ewatercycle_config'] = tmp_path / 'ewatercycle.yaml'
    yield CFG
    CFG['ewatercycle_config'] = DEFAULT_CONFIG
    CFG.reload()


@pytest.fixture
def mocked_parameterset_dir(setup_config, tmp_path):
    ps_dir = tmp_path / 'alisfloodexample'
    ps_dir.mkdir()
    config = ps_dir / 'settings.xml'
    config.write_text('Something')
    maskmap = ps_dir / 'mask.nc'
    maskmap.write_text('Someotherthing')
    CFG["parameter_sets"] = {
        'alisfloodexample': {
            'directory': str(ps_dir),
            'config': str(config.relative_to(tmp_path)),
            'MaskMap': str(maskmap.relative_to(tmp_path)),
            'target_model': 'lisflood',
            'doi': 'somedoi1'
        }
    }


def test_get_parameter_set(mocked_parameterset_dir, tmp_path):
    ps = get_parameter_set('alisfloodexample')

    assert isinstance(ps, LisfloodParameterSet)
    assert ps.MaskMap == tmp_path / 'alisfloodexample' / 'mask.nc'


def test_is_available(mocked_parameterset_dir):
    ps = get_parameter_set('alisfloodexample')

    assert ps.is_available
