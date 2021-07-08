from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from basic_modeling_interface import Bmi
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.models import Wflow
from ewatercycle.parameter_sets import ParameterSet


class MockedBmi(Bmi):
    """Pretend to be a real BMI model."""

    def initialize(self, config_file):
        pass

    def get_var_grid(self, name):
        return 1

    def get_grid_shape(self, grid_id):
        return 3, 2  # shape returns (len(x), len(y))

    def get_grid_x(self, grid_id):
        return np.array([45.0, 46.0, 47.0])  # x are lats in wflow

    def get_grid_y(self, grid_id):   # y are lons in wflow
        return np.array([5.0, 6.0])

    def get_grid_spacing(self, grid_id):
        return 1.0, 1.0

    def get_value_at_indices(self, name, indices):
        self.indices = indices
        return np.array([1.0])


@pytest.fixture
def mocked_config(tmp_path):
    CFG["output_dir"] = tmp_path
    CFG["container_engine"] = "singularity"
    CFG["singularity_dir"] = tmp_path
    CFG["parameterset_dir"] = tmp_path / "psr"
    CFG["parameter_sets"] = {}


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
    wflow = Wflow(version="2020.1.1", parameter_set=parameter_set)
    return wflow


@pytest.fixture
def initialized_model(model):
    """Model with fake parameterset and fake BMI instance."""
    model.bmi = MockedBmi()
    return model


def test_setup(model):
    with patch.object(
        BmiClientSingularity, "__init__", return_value=None
    ), patch("datetime.datetime") as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup()

    expected_cfg_dir = CFG["output_dir"] / "wflow_20210102_030405"
    assert cfg_dir == str(expected_cfg_dir)
    assert cfg_file == str(expected_cfg_dir / "wflow_ewatercycle.ini")


def test_setup_with_custom_cfg_dir(model, tmp_path):
    my_cfg_dir = str(tmp_path / "mycfgdir")
    with patch.object(
        BmiClientSingularity, "__init__", return_value=None
    ), patch("datetime.datetime") as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup(cfg_dir=my_cfg_dir)

    assert cfg_dir == my_cfg_dir
    assert cfg_file == str(Path(my_cfg_dir) / "wflow_ewatercycle.ini")


def test_get_value_as_coords(initialized_model):
    model = initialized_model

    expected = np.array([1.0])
    result = model.get_value_at_coords("discharge", lon=[5.2], lat=[46.8])
    assert result == expected
    assert model.bmi.indices == [4]
