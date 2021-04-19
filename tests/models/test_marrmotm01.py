from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from numpy.testing import assert_almost_equal
from scipy.io import loadmat
from xarray.testing import assert_allclose

from ewatercycle import CFG
from ewatercycle.models import MarrmotM01
from ewatercycle.models.marrmot import Solver


def test_parameters():
    model = MarrmotM01()
    expected = [
        ('maximum_soil_moisture_storage', 1000.0),
        ('initial_soil_moisture_storage', 900.0),
        ('solver', Solver()),
    ]
    assert model.parameters == expected


@pytest.fixture
def mocked_config(tmp_path):
    CFG['output_dir'] = tmp_path
    CFG['container_engine'] = 'docker'
    CFG['marrmot.docker_image'] = 'ewatercycle/marrmot-grpc4bmi:2020.11'


@pytest.fixture
def model():
    m = MarrmotM01()
    yield m
    if m.bmi:
        # Clean up container
        del m.bmi


class TestWithDefaultsAndExampleData:
    @pytest.fixture
    def forcing_file(self):
        # Downloaded from
        # https://github.com/wknoben/MARRMoT/blob/master/BMI/Config/BMI_testcase_m01_BuffaloRiver_TN_USA.mat
        return Path(__file__).parent / 'data' / 'BMI_testcase_m01_BuffaloRiver_TN_USA.mat'

    @pytest.fixture
    def model_with_setup(self, mocked_config, model: MarrmotM01, forcing_file: Path):
        cfg_file, cfg_dir = model.setup(
            forcing=forcing_file
        )
        return model, cfg_file, cfg_dir

    def test_setup(self, model_with_setup, forcing_file):
        model, cfg_file, cfg_dir = model_with_setup

        actual = loadmat(str(cfg_file))
        expected_forcing = loadmat(str(forcing_file))

        assert cfg_file.name == 'marrmot-m01_config.mat'
        assert model.bmi
        assert actual['model_name'] == "m_01_collie1_1p_1s"
        assert actual['parameters'] == [[1000]]
        assert actual['store_ini'] == [[900]]
        assert_almost_equal(actual['time_start'], expected_forcing['time_start'])
        assert_almost_equal(actual['time_end'], expected_forcing['time_end'])
        # TODO compare forcings
        # assert_almost_equal(actual['forcing'], expected_forcing['forcing'])
        # TODO assert solver
        # assert actual['solver'] == asdict(Solver())

    def test_parameters_after_setup(self, model_with_setup, forcing_file):
        model = model_with_setup[0]
        expected = [
            ('maximum_soil_moisture_storage', 1000.0),
            ('initial_soil_moisture_storage', 900.0),
            ('solver', Solver()),
            ('forcing_file', forcing_file)
        ]
        assert model.parameters == expected

    def test_get_value_as_xarray(self, model_with_setup):
        model, cfg_file, cfg_dir = model_with_setup
        model.initialize(str(cfg_file))
        model.update()

        actual = model.get_value_as_xarray('flux_out_Q')

        expected = xr.DataArray(
            data=[[0.552961]],
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
