import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from numpy.testing import assert_array_equal
import numpy as np

from grpc4bmi.bmi_client_singularity import BmiClientSingularity
from basic_modeling_interface import Bmi

from ewatercycle import CFG
from ewatercycle.forcing import load_foreign
from ewatercycle.parameter_sets._lisflood import LisfloodParameterSet
from ewatercycle.parametersetdb.datafiles import SubversionCopier
from ewatercycle.models.lisflood import Lisflood, XmlConfig


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
            directory=root,
            MaskMap=mask_dir / 'model_mask',
            config=root / 'settings_lat_lon-Run.xml',
        )

    @pytest.fixture
    def generate_forcing(self, tmp_path, parameterset):
        forcing_dir = tmp_path / 'forcing'
        forcing_dir.mkdir()
        meteo_dir = Path(parameterset.PathRoot) / 'meteo'
        # Create the case where forcing data arenot part of parameter_set
        for file in meteo_dir.glob('*.nc'):
            shutil.copy(file, forcing_dir)

        forcing = load_foreign(target_model='lisflood',
                               directory=str(forcing_dir),
                               start_time='1986-01-02T00:00:00Z',
                               end_time='2018-01-02T00:00:00Z',
                               forcing_info={
                                   'PrefixPrecipitation': 'tp.nc',
                                   'PrefixTavg': 'ta.nc',
                                   'PrefixE0': 'e0.nc',
                               })

        return forcing

    @pytest.fixture
    def model(self, parameterset, generate_forcing):
        forcing = generate_forcing
        m = Lisflood(version='20.10', parameter_set=parameterset, forcing=forcing)
        yield m
        if m.bmi:
            # Clean up container
            del m.bmi

    def test_default_parameters(self, model: Lisflood, tmp_path):
        expected_parameters = [
            ('IrrigationEfficiency', '0.75'),
            ('PathRoot', f'{tmp_path}/input'),
            ('MaskMap', f'{tmp_path}/mask'),
            ('config_template', f'{tmp_path}/input/settings_lat_lon-Run.xml'),
            ('start_time', '1986-01-02T00:00:00Z'),
            ('end_time', '2018-01-02T00:00:00Z'),
            ('forcing directory', f'{tmp_path}/forcing'),
        ]
        assert model.parameters == expected_parameters

    @pytest.fixture
    def model_with_setup(self, mocked_config, model: Lisflood):
        with patch.object(BmiClientSingularity, '__init__', return_value=None) as mocked_constructor, patch(
            'time.strftime', return_value='42'):
            config_file, config_dir = model.setup(
                IrrigationEfficiency='0.8',
            )
        return config_file, config_dir, mocked_constructor

    def test_setup(self, model_with_setup, tmp_path):
        config_file, config_dir, mocked_constructor = model_with_setup
        _cfg = XmlConfig(str(config_file))
        mocked_constructor.assert_called_once_with(
            image=f'{tmp_path}/ewatercycle-lisflood-grpc4bmi_20.10.sif',
            input_dirs=[
                f'{tmp_path}/input',
                f'{tmp_path}/mask',
                f'{tmp_path}/forcing'],
            work_dir=f'{tmp_path}/lisflood_42')
        assert 'lisflood_42' in str(config_dir)
        assert config_file.name == 'lisflood_setting.xml'
        for textvar in _cfg.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]
            if textvar_name == 'IrrigationEfficiency':
                assert textvar.get('value') == '0.8'

    class TestGetValueAtCoords():

        def test_get_value_at_coords_single(self, model: Lisflood):
            expected = np.array([1.0])
            model.bmi = MockedBmi()
            actual = model.get_value_at_coords('Discharge', lon=[-124.35], lat=[52.93])
            assert_array_equal(actual, expected)
            assert model.bmi.indices == [311]

        def test_get_value_at_coords_multiple(self, model: Lisflood):
            model.bmi = MockedBmi()
            model.get_value_at_coords('Discharge', lon=[-124.45, -124.35, -121.45], lat=[53.95, 52.93, 52.65])
            assert_array_equal(model.bmi.indices, [0, 311, 433])

        def test_get_value_at_coords_faraway(self, model: Lisflood):
            model.bmi = MockedBmi()
            with pytest.raises(ValueError) as excinfo:
                model.get_value_at_coords('Discharge', lon=[0.0], lat=[0.0])
            msg = str(excinfo.value)
            assert "This point is outside of the model grid." in msg


class MockedBmi(Bmi):
    """Mimic a real use case with realistic shape and abitrary high precision."""

    def get_var_grid(self, name):
        return 0

    def get_grid_shape(self, grid_id):
        return 14, 31  # shape returns (len(y), len(x))

    def get_grid_x(self, grid_id):
        return np.array([-124.450000000003, -124.350000000003, -124.250000000003,
                         -124.150000000003, -124.050000000003, -123.950000000003,
                         -123.850000000003, -123.750000000003, -123.650000000003,
                         -123.550000000003, -123.450000000003, -123.350000000003,
                         -123.250000000003, -123.150000000003, -123.050000000003,
                         -122.950000000003, -122.850000000003, -122.750000000003,
                         -122.650000000003, -122.550000000003, -122.450000000003,
                         -122.350000000003, -122.250000000003, -122.150000000003,
                         -122.050000000003, -121.950000000003, -121.850000000003,
                         -121.750000000003, -121.650000000003, -121.550000000003, -121.450000000003])

    def get_grid_y(self, grid_id):
        return np.array([53.950000000002, 53.8500000000021, 53.7500000000021, 53.6500000000021,
                         53.5500000000021, 53.4500000000021, 53.3500000000021, 53.2500000000021,
                         53.1500000000021, 53.0500000000021, 52.9500000000021, 52.8500000000021,
                         52.7500000000021, 52.6500000000021])

    def get_grid_spacing(self, grid_id):
        return 0.1, 0.1

    def get_value_at_indices(self, name, indices):
        self.indices = indices
        return np.array([1.0])
