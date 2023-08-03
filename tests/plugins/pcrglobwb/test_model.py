import logging
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_apptainer import BmiClientApptainer
from grpc4bmi.bmi_optionaldest import OptionalDestBmi

from ewatercycle import CFG
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.forcing import sources
from ewatercycle.parameter_sets import add_to_config, example_parameter_sets
from ewatercycle.plugins.pcrglobwb.model import PCRGlobWB, _SwapXY
from ewatercycle.testing.fake_models import FailingModel

PCRGlobWBForcing = sources["PCRGlobWBForcing"]


# @pytest.skip(
#     "Skipping the model testing: Downloader is broken.", allow_module_level=True
# )
# Mypy throws "error: "NoReturn" not callable [misc]". No idea why.
class MockedBmi(FailingModel):  # type: ignore
    """Pretend to be a real BMI model."""

    def initialize(self, config_file):
        pass

    def get_var_grid(self, name):
        return 1

    def get_grid_shape(self, grid_id, dest):
        return 3, 2  # shape returns (len(x), len(y))

    def get_grid_type(self, grid_id):
        return "rectilinear"

    def get_grid_x(self, grid_id, dest):
        return np.array([45.0, 46.0, 47.0])  # x are lats in pcrglob

    def get_grid_y(self, grid_id, dest):
        return np.array([5.0, 6.0])  # y are lons in pcrglob

    def get_grid_spacing(self, grid_id):
        return 1.0, 1.0

    def get_value_at_indices(self, name, dest, indices):
        self.indices = indices
        return np.array([1.0])

    def get_var_type(self, name):
        return "float64"

    def get_var_itemsize(self, name):
        return np.float64().size

    def get_var_nbytes(self, name):
        return np.float64().size * 3 * 2

    def get_grid_rank(self, grid_id):
        return 2


@pytest.fixture()
def mocked_config(tmp_path: Path):
    CFG.output_dir = tmp_path
    CFG.container_engine = "apptainer"
    CFG.apptainer_dir = tmp_path
    CFG.parameter_sets = {}
    parameterset_dir = tmp_path / "psr"
    parameterset_dir.mkdir()
    CFG.parameterset_dir = parameterset_dir


@pytest.fixture
def parameter_set(mocked_config):
    example_parameter_set = example_parameter_sets()["pcrglobwb_rhinemeuse_30min"]
    example_parameter_set.download(CFG.parameterset_dir)
    add_to_config(example_parameter_set)
    return example_parameter_set


@pytest.fixture
def forcing(parameter_set: ParameterSet):
    forcing_dir = parameter_set.directory / "forcing"
    return PCRGlobWBForcing(
        start_time="2001-01-01T00:00:00Z",
        end_time="2010-12-31T00:00:00Z",
        directory=str(forcing_dir),
        precipitationNC="precipitation_2001to2010.nc",
        temperatureNC="temperature_2001to2010.nc",
    )


@pytest.fixture
def model(parameter_set, forcing):
    return PCRGlobWB(forcing=forcing, parameter_set=parameter_set)


@pytest.fixture
def initialized_model(model):
    """Model with fake parameterset and fake BMI instance."""
    model._bmi = OptionalDestBmi(_SwapXY(MockedBmi()))
    return model


def test_setup(model):
    with (
        patch.object(BmiClientApptainer, "__init__", return_value=None),
        patch("datetime.datetime") as mocked_datetime,
    ):
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup()

    expected_cfg_dir = CFG.output_dir / "pcrglobwb_20210102_030405"
    assert cfg_dir == str(expected_cfg_dir)
    assert cfg_file == str(expected_cfg_dir / "pcrglobwb_ewatercycle.ini")


def test_setup_withtimeoutexception(model, tmp_path):
    with patch.object(
        BmiClientApptainer, "__init__", side_effect=FutureTimeoutError()
    ), patch("datetime.datetime") as mocked_datetime, pytest.raises(
        TimeoutError
    ) as excinfo:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)
        model.setup()

    msg = str(excinfo.value)
    assert "docker://ewatercycle/pcrg-grpc4bmi:setters" in msg
    assert "ewatercycle-pcrg-grpc4bmi_setters.sif" in msg


def test_setup_with_custom_cfg_dir(model, tmp_path):
    my_cfg_dir = str(tmp_path / "mycfgdir")
    with patch.object(BmiClientApptainer, "__init__", return_value=None), patch(
        "datetime.datetime"
    ) as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup(cfg_dir=my_cfg_dir)

    assert cfg_dir == my_cfg_dir
    assert cfg_file == str(Path(my_cfg_dir) / "pcrglobwb_ewatercycle.ini")


def test_get_value_as_coords(initialized_model, caplog):
    model = initialized_model

    with caplog.at_level(logging.DEBUG):
        result = model.get_value_at_coords("discharge", lon=[5.2], lat=[46.8])

    msg = (
        "Requested point was lon: 5.2, lat: 46.8;",
        " closest grid point is 5.00, 47.00.",
    )

    assert msg[0] in caplog.text
    assert msg[1] in caplog.text
    assert result == np.array([1.0])
