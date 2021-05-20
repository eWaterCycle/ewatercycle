import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
import xarray

from esmvalcore.experimental.recipe_output import DataFile
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing.forcing_data import ForcingData
from ewatercycle.parametersetdb.datafiles import SubversionCopier
from ewatercycle.models.lisflood import Lisflood, LisfloodParameterSet


@pytest.fixture
def mocked_config(tmp_path):
    CFG['output_dir'] = tmp_path
    CFG['container_engine'] = 'singularity'
    CFG['singularity_dir'] = tmp_path


class TestLFlatlonUseCase:
    @pytest.fixture
    def parameterset(self, tmp_path):
        # TODO dont let test download stuff from Internet, it is unreliable,
        #  copy use case files to this repo instead
        source = 'https://github.com/ec-jrc/lisflood-usecases/trunk/LF_lat_lon_UseCase'
        copier = SubversionCopier(source)
        root = tmp_path / 'input'
        copier.save(str(root))

        mask_dir = tmp_path / 'mask'
        mask_dir.mkdir()
        shutil.copy(
            root / 'maps' / 'masksmall.map',
            mask_dir / 'model_mask',
        )
        return LisfloodParameterSet(
            root=root,
            mask=mask_dir / 'model_mask',
            config_template=root / 'settings_lat_lon-Run.xml',
        )


    @pytest.fixture
    def forcing(self, tmp_path, parameterset):
        forcing_dir = tmp_path / 'forcing'
        forcing_dir.mkdir()
        meteo_dir = Path(parameterset.root) / 'meteo'
        meteo_files = {
            'ta.nc': {'ta': 'tas'},
            'e0.nc': False,
            'tp.nc': False,
        }
        for fn, var_rename in meteo_files.items():
            ds = xarray.open_dataset(meteo_dir / fn)
            # TODO save files as f"lisflood_{prefix['value']}_{timestamp}",
            if var_rename:
                ds.rename(var_rename).to_netcdf(forcing_dir / fn)
            else:
                ds.to_netcdf(forcing_dir / fn)

        class MockedTaskOutput:
            data_files = (
                DataFile(str(forcing_dir / 'e0.nc')),
                DataFile(str(forcing_dir / 'ta.nc')),
                DataFile(str(forcing_dir / 'tp.nc')),
            )

        recipe_output = {
            'diagnostic_daily/script': MockedTaskOutput()
        }
        return forcing_dir, ForcingData(recipe_output)


    @pytest.fixture
    def model(self, parameterset, forcing):
        forcing_dir, _ = forcing
        m = Lisflood(version='20.10', parameter_set=parameterset, forcing=forcing_dir)
        yield m
        if m.bmi:
            # Clean up container
            del m.bmi


    @pytest.fixture
    def model_with_setup(self, mocked_config, model: Lisflood):
        with patch.object(BmiClientSingularity, '__init__', return_value=None) as mocked_constructor, patch(
              'time.strftime', return_value='42'):
            config_file, config_dir = model.setup()
        return config_file, config_dir, mocked_constructor

    def test_setup(self, model_with_setup, tmp_path):
        config_file, config_dir, mocked_constructor = model_with_setup

        mocked_constructor.assert_called_once_with(
            image='docker://ewatercycle/lisflood-grpc4bmi:20.10',
            input_dirs=[
                f'{tmp_path}/input',
                f'{tmp_path}/mask',
                f'{tmp_path}/forcing'],
            work_dir=f'{tmp_path}/lisflood_42')
        assert 'lisflood_42' in str(config_dir)
        assert config_file.name == 'lisflood_setting.xml'
