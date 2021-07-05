import numpy as np
import pytest
from basic_modeling_interface import Bmi

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
        return np.array([45.0, 46.0, 47.0])

    def get_grid_y(self, grid_id):
        return np.array([5.0, 6.0])

    def get_grid_spacing(self, grid_id):
        return 1.0, 1.0

    def get_value_at_indices(self, name, indices):
        self.indices = indices
        return np.array([1.0])


@pytest.fixture
def parameter_set(tmp_path):
    """Fake parameter set for tests."""
    directory = tmp_path / "wflow_testcase"
    directory.mkdir()
    config = directory / "wflow_sbm_nc.ini"
    config.write_text("[API]\n")
    return ParameterSet(
        "wflow_testcase",
        directory=directory,
        config=config,
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


def test_get_value_as_coords(initialized_model):
    model = initialized_model

    expected = np.array([1.0])
    result = model.get_value_at_coords("RiverRunoff", lon=[5.2], lat=[46.8])
    assert result == expected
    assert model.bmi.indices == [2]
