from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.models import Wflow
from ewatercycle.parameter_sets import ParameterSet


@pytest.fixture
def mocked_config(tmp_path):
    CFG['output_dir'] = tmp_path
    CFG['container_engine'] = 'singularity'
    CFG['singularity_dir'] = tmp_path
    CFG['parameterset_dir'] = tmp_path / 'psr'
    CFG['parameter_sets'] = {}


@pytest.fixture
def parameter_set(tmp_path, mocked_config):
    """Fake parameter set for tests."""
    directory = tmp_path / "wflow_testcase"
    directory.mkdir()
    config = directory / "wflow_sbm_nc.ini"
    config.write_text("[API]\n")
    return ParameterSet(
        "wflow_testcase",
        directory=str(directory),
        config=str(config),
        target_model="wflow",
    )


@pytest.fixture
def model(parameter_set):
    """`Model with fake parameterset for tests."""
    return Wflow(version="2020.1.1", parameter_set=parameter_set)


def test_setup(model):
    with patch.object(BmiClientSingularity, '__init__', return_value=None), patch('datetime.datetime') as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup()

    expected_cfg_dir = CFG['output_dir'] / 'wflow_20210102_030405'
    assert cfg_dir == str(expected_cfg_dir)
    assert cfg_file == str(expected_cfg_dir / 'wflow_ewatercycle.ini')


def test_setup_with_custom_cfg_dir(model, tmp_path):
    my_cfg_dir = str(tmp_path / 'mycfgdir')
    with patch.object(BmiClientSingularity, '__init__', return_value=None), patch('datetime.datetime') as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup(cfg_dir=my_cfg_dir)

    assert cfg_dir == my_cfg_dir
    assert cfg_file == str(Path(my_cfg_dir) / 'wflow_ewatercycle.ini')
