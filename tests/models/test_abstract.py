from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Tuple
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr
from basic_modeling_interface import Bmi
from numpy.testing import assert_array_equal

from ewatercycle.models.abstract import AbstractModel


class MockedModel(AbstractModel):
    def setup(self, *args, **kwargs) -> Tuple[PathLike, PathLike]:
        if 'bmi' in kwargs:
            # sub-class of AbstractModel should construct bmi
            # using grpc4bmi Docker or Singularity client
            self.bmi = kwargs['bmi']
        return Path('foobar.cfg'), Path('.')

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        return xr.DataArray(
            data=[[1.0, 2.0]],
            dims=["time", "x"],
            name='Temperature',
            attrs=dict(units="degC"),
        )

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        return [('area', 42)]


@pytest.fixture
@patch('basic_modeling_interface.Bmi')
def bmi(MockedBmi):
    return MockedBmi()


@pytest.fixture
def model(bmi: Bmi):
    m = MockedModel()
    m.setup(bmi=bmi)
    return m


def test_setup(model):
    result = model.setup()

    expected = Path('foobar.cfg'), Path('.')
    assert result == expected


def test_initialize(model: MockedModel, bmi):
    config_file = 'foobar.cfg'
    model.initialize(config_file)

    bmi.initialize.assert_called_once_with(config_file)


def test_finalize(model: MockedModel, bmi):
    model.finalize()

    bmi.finalize.assert_called_once_with()


def test_update(model: MockedModel, bmi):
    model.update()

    bmi.update.assert_called_once_with()


def test_get_value(bmi, model: MockedModel):
    expected = np.array([1.0, 2.0])
    bmi.get_value.return_value = expected

    value = model.get_value('discharge')

    assert_array_equal(value, expected)


def test_set_value(model: MockedModel, bmi):
    value = np.array([1.0, 2.0])
    model.set_value('precipitation', value)

    bmi.set_value.assert_called_once_with('precipitation', value)


def test_start_time(bmi, model: MockedModel):
    bmi.get_start_time.return_value = 42.0

    time = model.start_time

    assert time == pytest.approx(42.0)


def test_end_time(bmi, model: MockedModel):
    bmi.get_end_time.return_value = 42.0

    time = model.end_time

    assert time == pytest.approx(42.0)


def test_time(bmi, model: MockedModel):
    bmi.get_current_time.return_value = 42.0

    time = model.time

    assert time == pytest.approx(42.0)


def test_time_units(bmi, model: MockedModel):
    bmi.get_time_units.return_value = 'd'

    units = model.time_units

    assert units == 'd'


def test_time_step(bmi, model: MockedModel):
    bmi.get_time_step.return_value = 1.0

    step = model.time_step

    assert step == pytest.approx(1.0)


def test_output_var_names(bmi, model: MockedModel):
    bmi.get_output_var_names.return_value = ('discharge', )

    names = model.output_var_names

    assert names == ('discharge', )


def test_get_value_as_xarray(model: MockedModel):
    expected = xr.DataArray(
            data=[[1.0, 2.0]],
            dims=["time", "x"],
            name='Temperature',
            attrs=dict(units="degC"),
        )

    dataarray = model.get_value_as_xarray("Temperature")

    xr.testing.assert_equal(dataarray, expected)
