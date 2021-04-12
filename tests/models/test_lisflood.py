import pytest

from ewatercycle.parametersetdb.datafiles import SubversionCopier
from ewatercycle.models.lisflood import Lisflood, LisfloodParameterSet

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
    copier.save(tmp_path)

def test_setup(model, parameterset):
    config_file, config_dir = model.setup(parameterset)

    assert '/scratch/shared/ewatercycle' in config_dir
    assert config_file == 'lisflood_{dataset}_setting.xml'