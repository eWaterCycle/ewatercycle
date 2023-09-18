from datetime import datetime
from pathlib import Path
from typing import Type
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr
from bmipy import Bmi
from grpc4bmi.bmi_optionaldest import OptionalDestBmi
from numpy.testing import assert_array_equal
from pydantic import ConfigDict
from pytest import fixture

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.base.model import ContainerizedModel, LocalModel, eWaterCycleModel
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.testing.fake_models import DummyModelWith2DRectilinearGrid


class MockModel(eWaterCycleModel):
    # Instead of using custom constructor had to do it the Pydantic way
    model_config = ConfigDict(arbitrary_types_allowed=True)
    mybmi: Bmi

    def _make_bmi_instance(self):
        return OptionalDestBmi(self.mybmi)


@fixture
def mocked_bmi():
    return DummyModelWith2DRectilinearGrid()


@fixture
def mocked_model(mocked_config, mocked_bmi):
    return MockModel(mybmi=mocked_bmi)


def test_version(mocked_model: eWaterCycleModel):
    assert mocked_model.version == ""


def test_parameters(mocked_model: eWaterCycleModel):
    assert mocked_model.parameters == {}.items()


class TestWithSetup:
    @fixture(autouse=True)
    def setup_on_mocked_model(self, mocked_model: eWaterCycleModel, tmp_path: Path):
        return mocked_model.setup(cfg_dir=str(tmp_path))

    def test_setup_cfg_dir(self, setup_on_mocked_model, tmp_path: Path):
        assert setup_on_mocked_model[1] == str(tmp_path)

    def test_setup_cfg_file(self, setup_on_mocked_model, tmp_path: Path):
        expected = str(tmp_path / "config.yaml")
        assert setup_on_mocked_model[0] == expected

    def test_setup_cfg_file_content(self, setup_on_mocked_model, tmp_path: Path):
        expected = "{}"
        assert (tmp_path / "config.yaml").read_text().strip() == expected

    def test_initialize(self, mocked_model: eWaterCycleModel, setup_on_mocked_model):
        config_file = setup_on_mocked_model[0]

        mocked_model.initialize(config_file)

        mocked_model.bmi.origin.mock.initialize.assert_called_once_with(config_file)

    def test_finalize(
        self,
        mocked_model: eWaterCycleModel,
        mocked_bmi: DummyModelWith2DRectilinearGrid,
    ):
        mocked_model.finalize()

        # mocked_model._bmi should be gone, so all calls after finalize fail
        assert not hasattr(mocked_model, "_bmi")
        mocked_bmi.mock.finalize.assert_called_once_with()

    def test_update(self, mocked_model: eWaterCycleModel):
        mocked_model.update()
        mocked_model.update()
        mocked_model.update()

        assert mocked_model.time == 3.0

    def test_time(self, mocked_model: eWaterCycleModel):
        result = mocked_model.time

        assert result == 0.0

    def test_time_step(self, mocked_model: eWaterCycleModel):
        result = mocked_model.time_step

        assert result == 1.0

    def test_start_time(self, mocked_model: eWaterCycleModel):
        result = mocked_model.start_time

        assert result == 0.0

    def test_end_time(self, mocked_model: eWaterCycleModel):
        result = mocked_model.end_time

        assert result == 100.0

    def test_time_as_datetime(self, mocked_model: eWaterCycleModel):
        result = mocked_model.time_as_datetime

        assert result == datetime(1970, 1, 1)

    def test_start_time_as_datetime(self, mocked_model: eWaterCycleModel):
        result = mocked_model.start_time_as_datetime

        assert result == datetime(1970, 1, 1)

    def test_end_time_as_datetime(self, mocked_model: eWaterCycleModel):
        result = mocked_model.end_time_as_datetime

        # 100th day of 1970
        assert result == datetime(1970, 4, 11)

    def test_time_as_isostr(self, mocked_model: eWaterCycleModel):
        result = mocked_model.time_as_isostr

        assert result == "1970-01-01T00:00:00Z"

    def test_start_time_as_isostr(self, mocked_model: eWaterCycleModel):
        result = mocked_model.start_time_as_isostr

        assert result == "1970-01-01T00:00:00Z"

    def test_end_time_as_isostr(self, mocked_model: eWaterCycleModel):
        result = mocked_model.end_time_as_isostr

        assert result == "1970-04-11T00:00:00Z"

    def test_time_units(self, mocked_model: eWaterCycleModel):
        result = mocked_model.time_units

        assert result == "days since 1970-01-01"

    def test_output_var_names(self, mocked_model: eWaterCycleModel):
        result = mocked_model.output_var_names

        assert result == ("plate_surface__temperature",)

    def test_get_value(self, mocked_model: eWaterCycleModel):
        result = mocked_model.get_value("plate_surface__temperature")

        expected = np.array(
            [
                1.1,
                2.2,
                3.3,
                4.4,
                5.5,
                6.6,
                7.7,
                8.8,
                9.9,
                10.1,
                11.1,
                12.1,
            ],
            dtype=np.float32,
        )
        assert_array_equal(result, expected)

    def test_get_value_at_coords(self, mocked_model: eWaterCycleModel):
        result = mocked_model.get_value_at_coords(
            "plate_surface__temperature",
            lat=[
                1.2,
            ],
            lon=[
                0.3,
            ],
        )

        expected = np.array(
            [
                7.7,
            ],
            dtype=np.float32,
        )
        assert_array_equal(result, expected)

    def test_set_value(
        self,
        mocked_model: eWaterCycleModel,
        mocked_bmi: DummyModelWith2DRectilinearGrid,
    ):
        new_values = np.full((12,), 4.2, dtype=np.float32)

        mocked_model.set_value("plate_surface__temperature", new_values)

        assert_array_equal(mocked_bmi.value, new_values)

    def test_set_value_at_coords(
        self,
        mocked_model: eWaterCycleModel,
        mocked_bmi: DummyModelWith2DRectilinearGrid,
    ):
        new_values = np.array([4.2, 1.23], dtype=np.float32)

        mocked_model.set_value_at_coords(
            "plate_surface__temperature",
            lon=[0.3, 0.2],
            lat=[1.2, 1.1],
            values=new_values,
        )

        expected = np.array(
            [
                1.1,
                1.23,
                3.3,
                4.4,
                5.5,
                6.6,
                4.2,
                8.8,
                9.9,
                10.1,
                11.1,
                12.1,
            ],
            dtype=np.float32,
        )
        assert_array_equal(mocked_bmi.value, expected)

    @pytest.mark.skip(
        reason="Implemntation and DummyModelWith2DRectilinearGrid are incompatible"
    )
    def test_get_value_as_xarray(self, mocked_model: eWaterCycleModel):
        result = mocked_model.get_value_as_xarray("plate_surface__temperature")

        expected = xr.DataArray(
            data=np.array(
                [
                    [
                        [1.1, 2.2, 3.3, 4.4],
                        [5.5, 6.6, 7.7, 8.8],
                        [9.9, 10.1, 11.1, 12.1],
                    ]
                ],
                dtype=np.float32,
            ),
            coords={
                "longitude": [0.1, 0.2, 0.3, 0.4],
                "latitude": [1.1, 1.2, 1.3],
                "time": [datetime(1970, 1, 1)],
            },
            dims=["time", "latitude", "longitude"],
            name="plate_surface__temperature",
            attrs={"units": "K"},
        )
        xr.testing.assert_equal(result, expected)


class DummyLocalModel(LocalModel):
    bmi_class: Type[Bmi] = DummyModelWith2DRectilinearGrid


# bit ugly to have version here,
# but that is how version of DummyLocalModel class is determined
__version__ = "1.2.3"


class TestLocalModel:
    @fixture
    def model(self):
        return DummyLocalModel()

    def test_version(self, model):
        assert model.version == "1.2.3"

    @fixture(autouse=True)
    def setup_on_mocked_model(self, model: eWaterCycleModel, tmp_path: Path):
        return model.setup(cfg_dir=str(tmp_path))

    def test_bmi_class(self, model: eWaterCycleModel):
        assert model._bmi.origin.__class__ == DummyModelWith2DRectilinearGrid


class TestContainerizedModel:
    def test_version(self):
        model = ContainerizedModel(bmi_image="ewatercycle/ewatercycle_dummy:latest")

        assert model.version == "latest"

    @patch("ewatercycle.base.model.start_container")
    def test_setup(self, mocked_start_container, tmp_path: Path):
        model = ContainerizedModel(bmi_image="ewatercycle/ewatercycle_dummy:latest")

        model.setup(cfg_dir=str(tmp_path))

        mocked_start_container.assert_called_once_with(
            image="ewatercycle/ewatercycle_dummy:latest",
            work_dir=tmp_path,
            input_dirs=[],
            timeout=300,
        )

    @patch("ewatercycle.base.model.start_container")
    def test_setup_with_additional_input_dirs(
        self, mocked_start_container, tmp_path: Path
    ):
        forcing_dir = tmp_path / "forcing"
        forcing = DefaultForcing(
            directory=forcing_dir,
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
        )
        parameter_set_dir = tmp_path / "parameter_set"
        parameter_set = ParameterSet(
            name="test",
            directory=parameter_set_dir,
            config="config.yaml",
            target_model="containerizedmodel",
            supported_model_versions=["latest"],
        )
        model = ContainerizedModel(
            bmi_image="ewatercycle/ewatercycle_dummy:latest",
            parameter_set=parameter_set,
            forcing=forcing,
        )

        model.setup(cfg_dir=str(tmp_path))

        mocked_start_container.assert_called_once_with(
            image="ewatercycle/ewatercycle_dummy:latest",
            work_dir=tmp_path,
            input_dirs=[
                str(parameter_set_dir),
                str(forcing_dir),
            ],
            timeout=300,
        )
