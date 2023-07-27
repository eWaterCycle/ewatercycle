import logging
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import numpy as np
import pytest
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_apptainer import BmiClientApptainer

from ewatercycle import CFG
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.plugins.wflow.model import Wflow
from ewatercycle.testing.fake_models import FailingModel
from ewatercycle.util import CaseConfigParser


class MockedBmi(FailingModel):
    """Pretend to be a real BMI model."""

    def get_component_name(self) -> str:
        return "mocked"

    def initialize(self, config_file):
        pass

    def get_var_grid(self, name):
        return 1

    def get_grid_shape(self, grid_id):
        return 3, 2

    def get_grid_y(self, grid_id):
        return np.array([45.0, 46.0, 47.0])

    def get_grid_x(self, grid_id):
        return np.array([5.0, 6.0])

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


@pytest.fixture
def mocked_config(tmp_path: Path):
    CFG.output_dir = tmp_path
    CFG.container_engine = "apptainer"
    CFG.apptainer_dir = tmp_path
    CFG.parameter_sets = {}
    parameterset_dir = tmp_path / "wflow_testcase"
    parameterset_dir.mkdir()
    CFG.parameterset_dir = parameterset_dir


@pytest.fixture
def parameter_set(tmp_path, mocked_config):
    """Fake parameter set for tests."""
    directory = tmp_path / "wflow_testcase"
    config = directory / "wflow_sbm_nc.ini"
    # Trimmed down config from
    # https://github.com/openstreams/wflow/blob/master/examples/wflow_rhine_sbm_nc/wflow_sbm_NC.ini
    config_body = dedent(
        """[inputmapstacks]
        Precipitation = /inmaps/P
        EvapoTranspiration = /inmaps/PET
        Temperature = /inmaps/TEMP
        Inflow = /inmaps/IF

        [run]
        starttime=1991-02-01 00:00:00
        endtime=1991-03-01 00:00:00
        timestepsecs = 86400

        [framework]
        netcdfinput= inmaps.nc
    """
    )
    config.write_text(config_body)
    return ParameterSet(
        name="wflow_testcase",
        directory=directory,
        config=config,
        target_model="wflow",
    )


@pytest.fixture
def model(parameter_set):
    """`Model with fake parameterset for tests."""
    return Wflow(version="2020.1.1", parameter_set=parameter_set)


@pytest.fixture
def initialized_model(model):
    """Model with fake parameterset and fake BMI instance."""
    model._bmi = MockedBmi()
    return model


def test_constructor_adds_api_riverrunoff(parameter_set, caplog):
    with caplog.at_level(logging.WARNING):
        Wflow(version="2020.1.1", parameter_set=parameter_set)

    assert (
        "Config file from parameter set is missing API section, adding section"
        in caplog.text
    )
    assert (
        "Config file from parameter set is missing RiverRunoff option in API section"
        in caplog.text
    )
    assert "added it with value '2, m/s option'" in caplog.text


def test_str(model, tmp_path):
    actual = str(model)

    expected_ps = "".join(
        [
            "ParameterSet(name='wflow_testcase', ",
            f"directory={repr(tmp_path / 'wflow_testcase')}, ",
            f"config={repr(tmp_path / 'wflow_testcase' / 'wflow_sbm_nc.ini')}, ",
            "doi='N/A', target_model='wflow', supported_model_versions=set(), ",
            "downloader=None)",
        ]
    )
    expected = f"parameter_set={expected_ps} forcing=None"
    assert actual == expected


def test_setup(model):
    with patch.object(BmiClientApptainer, "__init__", return_value=None), patch(
        "datetime.datetime"
    ) as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup()
    expected_cfg_dir = CFG.output_dir / "wflow_20210102_030405"
    assert cfg_dir == str(expected_cfg_dir)
    expected_cfg_file = expected_cfg_dir / "wflow_ewatercycle.ini"
    assert cfg_file == str(expected_cfg_file)
    # Check content of config file
    cfg = CaseConfigParser()
    cfg.read(expected_cfg_file)
    assert cfg.get("API", "RiverRunoff") == "2, m/s"


def test_setup_withtimeoutexception(model, tmp_path):
    with patch.object(
        BmiClientApptainer, "__init__", side_effect=FutureTimeoutError()
    ), patch("datetime.datetime") as mocked_datetime, pytest.raises(
        TimeoutError
    ) as excinfo:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)
        model.setup()

    msg = str(excinfo.value)
    assert "docker://ewatercycle/wflow-grpc4bmi:2020.1.3" in msg
    assert "ewatercycle-wflow-grpc4bmi_2020.1.3.sif" in msg


def test_setup_with_custom_cfg_dir(model, tmp_path):
    my_cfg_dir = str(tmp_path / "mycfgdir")
    with patch.object(BmiClientApptainer, "__init__", return_value=None), patch(
        "datetime.datetime"
    ) as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)

        cfg_file, cfg_dir = model.setup(cfg_dir=my_cfg_dir)

    assert cfg_dir == my_cfg_dir
    assert cfg_file == str(Path(my_cfg_dir) / "wflow_ewatercycle.ini")


def test_get_value_as_coords(initialized_model, caplog):
    model = initialized_model

    with caplog.at_level(logging.DEBUG):
        result = model.get_value_at_coords("discharge", lon=[5.2], lat=[46.8])

    msg1 = "Requested point was lon: 5.2, lat: 46.8;"
    msg2 = "closest grid point is 5.00, 47.00."

    assert msg1 in caplog.text and msg2 in caplog.text
    assert result == np.array([1.0])
    assert model._bmi.indices == [4]
