import shutil

import pytest

from esmvalcore.experimental.recipe_output import DataFile
from ewatercycle.forcing.forcing_data import ForcingData
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

@pytest.fixture
def forcing(tmp_path):
    forcing_dir = tmp_path / 'forcing'
    forcing_dir.mkdir()

    class MockedTaskOutput:
        data_files = (
            DataFile(str(forcing_dir / 'lisflood_ERA-Interim_Meuse_rsds_1990_1990.nc')),
            DataFile(str(forcing_dir / 'lisflood_ERA-Interim_Meuse_e_1990_1990.nc')),
            DataFile(str(forcing_dir / 'lisflood_ERA-Interim_Meuse_tasmax_1990_1990.nc')),
            DataFile(str(forcing_dir / 'lisflood_ERA-Interim_Meuse_pr_1990_1990.nc')),
            DataFile(str(forcing_dir / 'lisflood_ERA-Interim_Meuse_sfcWind_1990_1990.nc')),
            DataFile(str(forcing_dir / 'lisflood_ERA-Interim_Meuse_tas_1990_1990.nc')),
            DataFile(str(forcing_dir / 'lisflood_ERA-Interim_Meuse_tasmin_1990_1990.nc')),
        )

    # TODO copy meteo files from usecase and convert from pcraster to netcdf
    recipe_output = {
        'diagnostic_daily/script': MockedTaskOutput()
    }
    return ForcingData(recipe_output)


def test_setup(model, forcing, parameterset):
    config_file, config_dir = model.setup(forcing, parameterset)

    assert '/scratch/shared/ewatercycle' in config_dir
    assert config_file == 'lisflood_{dataset}_setting.xml'