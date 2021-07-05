from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.forcing import load_foreign
from ewatercycle.models import PCRGlobWB
from ewatercycle.parameter_sets import example_parameter_sets, ParameterSet


@pytest.fixture
def mocked_config(tmp_path):
    CFG['output_dir'] = tmp_path
    CFG['container_engine'] = 'singularity'
    CFG['singularity_dir'] = tmp_path
    CFG['parameterset_dir'] = tmp_path / 'psr'
    CFG['parameter_sets'] = {}


@pytest.fixture
def parameter_set(mocked_config):
    example_parameter_set = example_parameter_sets()['pcrglobwb_example_case']
    example_parameter_set.download()
    example_parameter_set.to_config()
    return example_parameter_set


@pytest.fixture
def forcing(parameter_set: ParameterSet):
    forcing_dir = parameter_set.directory / 'forcing'
    return load_foreign(
        target_model="pcrglobwb",
        start_time="2001-01-01T00:00:00Z",
        end_time="2010-12-31T00:00:00Z",
        directory=str(forcing_dir),
        forcing_info=dict(
            precipitationNC="precipitation_2001to2010.nc",
            temperatureNC="temperature_2001to2010.nc"
        )
    )


@pytest.fixture
def model(parameter_set, forcing):
    return PCRGlobWB("setters", parameter_set, forcing)


def test_setup(model):
    with patch.object(BmiClientSingularity, '__init__', return_value=None), patch('datetime.datetime') as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup()

    expected_cfg_dir = CFG['output_dir'] / 'pcrglobwb_20210102_030405'
    assert cfg_dir == str(expected_cfg_dir)
    assert cfg_file == str(expected_cfg_dir / 'pcrglobwb_ewatercycle.ini')


def test_setup_with_custom_cfg_dir(model, tmp_path):
    my_cfg_dir = str(tmp_path / 'mycfgdir')
    with patch.object(BmiClientSingularity, '__init__', return_value=None), patch('datetime.datetime') as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup(cfg_dir=my_cfg_dir)

    assert cfg_dir == my_cfg_dir
    assert cfg_file == str(Path(my_cfg_dir) / 'pcrglobwb_ewatercycle.ini')
