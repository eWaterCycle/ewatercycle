from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import xarray as xr
from numpy.testing import assert_almost_equal
from scipy.io import loadmat
from xarray.testing import assert_allclose

from ewatercycle import CFG
from ewatercycle.forcing import load_foreign
from ewatercycle.models.marrmot import Solver, MarrmotM01


@pytest.fixture
def mocked_config(tmp_path):
    CFG['output_dir'] = tmp_path
    CFG['container_engine'] = 'docker'


class TestWithDefaultsAndExampleData:
    @pytest.fixture
    def forcing_file(self, sample_marrmot_forcing_file):
        return sample_marrmot_forcing_file

    @pytest.fixture
    def generate_forcing(self, forcing_file):
        forcing = load_foreign('marrmot',
                               directory=str(Path(forcing_file).parent),
                               start_time='1989-01-01T00:00:00Z',
                               end_time='1992-12-31T00:00:00Z',
                               forcing_info={
                                   'forcing_file': str(Path(forcing_file).name)
                               })
        return forcing

    @pytest.fixture
    def model(self, generate_forcing, mocked_config):
        m = MarrmotM01(version="2020.11", forcing=generate_forcing)
        yield m
        if m.bmi:
            # Clean up container
            del m.bmi

    @pytest.fixture
    def model_with_setup(self, model: MarrmotM01):
        with patch('datetime.datetime') as mocked_datetime:
            mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

            cfg_file, cfg_dir = model.setup()
            return model, cfg_file, cfg_dir


    def test_str(self, model, forcing_file):
        actual = str(model)
        expected =  "\n".join(
            [
                "eWaterCycle MarrmotM01",
                "-------------------",
                "Version = 2020.11",
                "Parameter set = ",
                "  None",
                "Forcing = ",
                "  eWaterCycle forcing",
                "  -------------------",
                "  start_time=1989-01-01T00:00:00Z",
                "  end_time=1992-12-31T00:00:00Z",
                f"  directory={str(Path(forcing_file).parent)}",
                "  shape=None",
                "  forcing_file=BMI_testcase_m01_BuffaloRiver_TN_USA.mat",
            ])
        assert actual == expected

    def test_parameters(self, model):

        expected = [
            ('maximum_soil_moisture_storage', 10.0),
            ('initial_soil_moisture_storage', 5.0),
            ('solver', Solver()),
            ('start time', '1989-01-01T00:00:00Z'),
            ('end time', '1992-12-31T00:00:00Z'),
        ]
        assert model.parameters == expected

    def test_setup(self, model_with_setup, forcing_file):
        model, cfg_file, cfg_dir = model_with_setup

        expected_cfg_dir = CFG['output_dir'] / 'marrmot_20210102_030405'
        assert cfg_dir == str(expected_cfg_dir)
        assert cfg_file == str(expected_cfg_dir / 'marrmot-m01_config.mat')
        assert model.bmi
        actual = loadmat(str(cfg_file))
        expected_forcing = loadmat(forcing_file)
        assert actual['model_name'] == "m_01_collie1_1p_1s"
        assert_almost_equal(actual['time_start'], expected_forcing['time_start'])
        assert_almost_equal(actual['time_end'], expected_forcing['time_end'])
        # TODO compare forcings
        # assert_almost_equal(actual['forcing'], expected_forcing['forcing'])
        # TODO assert solver
        # assert actual['solver'] == asdict(Solver())

    def test_parameters_after_setup(self, model_with_setup):
        model = model_with_setup[0]
        expected = [
            ('maximum_soil_moisture_storage', 10.0),
            ('initial_soil_moisture_storage', 5.0),
            ('solver', Solver()),
            ('start time', '1989-01-01T00:00:00Z'),
            ('end time', '1992-12-31T00:00:00Z'),
        ]
        assert model.parameters == expected

    def test_get_value_as_xarray(self, model_with_setup):
        model, cfg_file, cfg_dir = model_with_setup
        model.initialize(cfg_file)
        model.update()

        actual = model.get_value_as_xarray('flux_out_Q')

        expected = xr.DataArray(
            data=[[11.91879913]],
            coords={
                "longitude": [87.49],
                "latitude": [35.29],
                "time": datetime(1989, 1, 2, tzinfo=timezone.utc)
            },
            dims=["latitude", "longitude"],
            name='flux_out_Q',
            attrs={"units": 'mm day'},
        )
        assert_allclose(actual, expected)

    def test_setup_with_own_cfg_dir(self, tmp_path, mocked_config, model: MarrmotM01):
        cfg_file, cfg_dir = model.setup(
            cfg_dir=str(tmp_path)
        )
        assert cfg_dir == str(tmp_path)

    def test_setup_create_cfg_dir(self, tmp_path, mocked_config, model: MarrmotM01):
        work_dir = tmp_path / 'output'
        cfg_file, cfg_dir = model.setup(
            cfg_dir=str(work_dir)
        )
        assert cfg_dir == str(work_dir)


class TestWithCustomSetupAndExampleData:
    @pytest.fixture
    def forcing_file(self, sample_marrmot_forcing_file):
        return sample_marrmot_forcing_file

    @pytest.fixture
    def generate_forcing(self, forcing_file):
        forcing = load_foreign('marrmot',
                               directory=str(Path(forcing_file).parent),
                               start_time='1989-01-01T00:00:00Z',
                               end_time='1992-12-31T00:00:00Z',
                               forcing_info={
                                   'forcing_file': str(Path(forcing_file).name)
                               })
        return forcing

    @pytest.fixture
    def model(self, generate_forcing, mocked_config):
        m = MarrmotM01(version="2020.11", forcing=generate_forcing)
        yield m
        if m.bmi:
            # Clean up container
            del m.bmi

    @pytest.fixture
    def model_with_setup(self, model: MarrmotM01):
        with patch('datetime.datetime') as mocked_datetime:
            mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

            cfg_file, cfg_dir = model.setup(
                maximum_soil_moisture_storage=1234,
                initial_soil_moisture_storage=4321,
                start_time='1990-01-01T00:00:00Z',
                end_time='1991-12-31T00:00:00Z',
            )
            return model, cfg_file, cfg_dir

    def test_setup(self, model_with_setup):
        model, cfg_file, cfg_dir = model_with_setup

        expected_cfg_dir = CFG['output_dir'] / 'marrmot_20210102_030405'
        assert cfg_dir == str(expected_cfg_dir)
        assert cfg_file == str(expected_cfg_dir / 'marrmot-m01_config.mat')
        assert model.bmi
        actual = loadmat(str(cfg_file))
        assert actual['model_name'] == "m_01_collie1_1p_1s"
        assert actual['parameters'] == [[1234]]
        assert actual['store_ini'] == [[4321]]
        assert_almost_equal(actual['time_start'], [[1990, 1, 1, 0, 0, 0]])
        assert_almost_equal(actual['time_end'], [[1991, 12, 31, 0, 0, 0]])


class TestWithDatesOutsideRangeSetupAndExampleData:
    @pytest.fixture
    def forcing_file(self, sample_marrmot_forcing_file):
        return sample_marrmot_forcing_file

    @pytest.fixture
    def generate_forcing(self, forcing_file):
        forcing = load_foreign('marrmot',
                               directory=str(Path(forcing_file).parent),
                               start_time='1989-01-01T00:00:00Z',
                               end_time='1992-12-31T00:00:00Z',
                               forcing_info={
                                   'forcing_file': str(Path(forcing_file).name)
                               })
        return forcing

    @pytest.fixture
    def model(self, generate_forcing, mocked_config):
        m = MarrmotM01(version="2020.11", forcing=generate_forcing)
        yield m
        if m.bmi:
            # Clean up container
            del m.bmi

    def test_setup_with_earlystart(self, model: MarrmotM01):
        with pytest.raises(ValueError) as excinfo:
            model.setup(
                start_time='1980-01-01T00:00:00Z',
            )
        assert 'start_time outside forcing time range' in str(excinfo.value)

    def test_setup_with_lateend(self, model: MarrmotM01):
        with pytest.raises(ValueError) as excinfo:
            model.setup(
                end_time='2000-01-01T00:00:00Z',
            )
        assert 'end_time outside forcing time range' in str(excinfo.value)
