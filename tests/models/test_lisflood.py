import shutil

import pytest

from ewatercycle.parametersetdb.datafiles import SubversionCopier
from ewatercycle.models.lisflood import CFG, Lisflood, LisfloodParameterSet


def mocked_config(tmp_path):
    CFG['scratch_dir'] = tmp_path
    CFG['container_engine'] = 'singularity'
    CFG['lisflood']['singularity_image'] = 'docker://ewatercycle/lisflood-grpc4bmi:latest'

@pytest.fixture
def model():
    m = Lisflood()
    yield m
    if m.bmi:
        del m.bmi

@pytest.fixture
def parameterset(tmp_path):
    source = 'https://github.com/ec-jrc/lisflood-usecases/trunk/LF_lat_lon_UseCase'
    copier = SubversionCopier(source)
    root = tmp_path / 'input'
    copier.save(root)

    mask_dir = tmp_path / 'mask'
    mask_dir.mkdir()
    shutil.copy(
        root / 'maps' / 'masksmall.map',
        mask_dir / 'model_mask',
    )
    return LisfloodParameterSet(
        root=root,
        mask=mask_dir,
        config_template=root / 'settings_lat_lon-Run.xml',
    )

def forcing(tmp_path):
    forcing_dir = tmp_path / 'forcing'


    @dataclass
    class MockedForcingData(ForcingData):
        start_year = '1986'
        end_year = '1986'
        forcing = 'ERA5'
        location = forcing_dir

    return MockedForcingData()

def test_setup(model, forcing, parameterset):
    config_file, config_dir = model.setup(forcing, parameterset)

    assert '/scratch/shared/ewatercycle' in config_dir
    assert config_file == 'lisflood_{dataset}_setting.xml'