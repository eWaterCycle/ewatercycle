import logging
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from basic_modeling_interface import Bmi
from grpc4bmi.bmi_client_singularity import BmiClientSingularity
from numpy.testing import assert_array_equal

from ewatercycle import CFG
from ewatercycle.forcing import load_foreign
from ewatercycle.models.lisflood import Lisflood, XmlConfig
from ewatercycle.parameter_sets import ParameterSet, example_parameter_sets


@pytest.fixture
def mocked_config(tmp_path):
    CFG["output_dir"] = tmp_path
    CFG["container_engine"] = "singularity"
    CFG["singularity_dir"] = tmp_path
    CFG["parameterset_dir"] = tmp_path / "psr"
    CFG["parameter_sets"] = {}


def find_values_in_xml(tree, name):
    values = []
    for textvar in tree.iter("textvar"):
        textvar_name = textvar.attrib["name"]
        if textvar_name == name:
            values.append(textvar.get("value"))
    return set(values)


class TestLFlatlonUseCase:
    @pytest.fixture
    def parameterset(self, mocked_config):
        example_parameter_set = example_parameter_sets()["lisflood_fraser"]
        example_parameter_set.download()
        example_parameter_set.to_config()
        return example_parameter_set

    @pytest.fixture
    def generate_forcing(self, tmp_path, parameterset: ParameterSet):
        forcing_dir = tmp_path / "forcing"
        forcing_dir.mkdir()
        meteo_dir = Path(parameterset.directory) / "meteo"
        # Create the case where forcing data arenot part of parameter_set
        for file in meteo_dir.glob("*.nc"):
            shutil.copy(file, forcing_dir / f"my{file.stem}.nc")

        return load_foreign(
            target_model="lisflood",
            directory=str(forcing_dir),
            start_time="1986-01-02T00:00:00Z",
            end_time="2018-01-02T00:00:00Z",
            forcing_info={
                "PrefixPrecipitation": "mytp.nc",
                "PrefixTavg": "myta.nc",
                "PrefixE0": "mye0.nc",
            },
        )

    @pytest.fixture
    def model(self, parameterset, generate_forcing):
        forcing = generate_forcing
        m = Lisflood(
            version="20.10", parameter_set=parameterset, forcing=forcing
        )
        yield m
        if m.bmi:
            # Clean up container
            del m.bmi

    def test_default_parameters(self, model: Lisflood, tmp_path):
        expected_parameters = [
            ("IrrigationEfficiency", "0.75"),
            ("MaskMap", "$(PathMaps)/masksmall.map"),
            ("start_time", "1986-01-02T00:00:00Z"),
            ("end_time", "2018-01-02T00:00:00Z"),
        ]
        assert model.parameters == expected_parameters

    @pytest.fixture
    def model_with_setup(self, mocked_config, model: Lisflood):
        with patch.object(
            BmiClientSingularity, "__init__", return_value=None
        ) as mocked_constructor, patch("datetime.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)
            config_file, config_dir = model.setup(
                IrrigationEfficiency="0.8",
            )
        return config_file, config_dir, mocked_constructor

    def test_setup(self, model_with_setup, tmp_path):
        config_file, config_dir, mocked_constructor = model_with_setup

        # Check setup returns
        expected_cfg_dir = CFG["output_dir"] / "lisflood_20210102_030405"
        assert config_dir == str(expected_cfg_dir)
        assert config_file == str(expected_cfg_dir / "lisflood_setting.xml")

        # Check container started
        mocked_constructor.assert_called_once_with(
            image=f"{tmp_path}/ewatercycle-lisflood-grpc4bmi_20.10.sif",
            input_dirs=[
                f"{tmp_path}/psr/lisflood_fraser",
                f"{tmp_path}/forcing",
            ],
            work_dir=f"{tmp_path}/lisflood_20210102_030405",
        )

        # Check content config file
        _cfg = XmlConfig(str(config_file))
        assert find_values_in_xml(_cfg.config, "CalendarDayStart") == {
            "02/01/1986 00:00"
        }
        assert find_values_in_xml(_cfg.config, "StepStart") == {"1"}
        assert find_values_in_xml(_cfg.config, "StepEnd") == {"11688"}
        assert find_values_in_xml(_cfg.config, "PathMeteo") == {
            f"{tmp_path}/forcing"
        }
        assert find_values_in_xml(_cfg.config, "PathOut") == {str(config_dir)}
        assert find_values_in_xml(_cfg.config, "IrrigationEfficiency") == {
            "0.8"
        }
        assert find_values_in_xml(_cfg.config, "MaskMap") == {
            "$(PathMaps)/masksmall.map",
            "$(MaskMap)",
        }
        assert find_values_in_xml(_cfg.config, "PrefixPrecipitation") == {
            "mytp"
        }
        assert find_values_in_xml(_cfg.config, "PrefixTavg") == {"myta"}
        assert find_values_in_xml(_cfg.config, "PrefixE0") == {"mye0"}
        assert find_values_in_xml(_cfg.config, "PrefixES0") == {"es0"}
        assert find_values_in_xml(_cfg.config, "PrefixET0") == {"et0"}

    class TestGetValueAtCoords:
        def test_get_value_at_coords_single(self, caplog, model: Lisflood):
            model.bmi = MockedBmi()

            with caplog.at_level(logging.DEBUG):
                result = model.get_value_at_coords(
                    "Discharge", lon=[-124.35], lat=[52.93]
                )

            msg = (
                "Requested point was lon: -124.35, lat: 52.93;"
                " closest grid point is -124.35, 52.95."
            )

            assert msg in caplog.text
            assert result == np.array([1.0])
            assert model.bmi.indices == [311]

        def test_get_value_at_coords_multiple(self, model: Lisflood):
            model.bmi = MockedBmi()
            model.get_value_at_coords(
                "Discharge",
                lon=[-124.45, -124.35, -121.45],
                lat=[53.95, 52.93, 52.65],
            )
            assert_array_equal(model.bmi.indices, [0, 311, 433])

        def test_get_value_at_coords_faraway(self, model: Lisflood):
            model.bmi = MockedBmi()
            with pytest.raises(ValueError) as excinfo:
                model.get_value_at_coords("Discharge", lon=[0.0], lat=[0.0])
            msg = str(excinfo.value)
            assert "outside model grid." in msg

    class TestCustomMaskMap:
        @pytest.fixture
        def model(self, tmp_path, parameterset, generate_forcing):
            # Create the case where mask map is not part of parameter_set
            mask_dir = tmp_path / "custommask"
            mask_dir.mkdir()
            mask_file_in_ps = parameterset.directory / "maps/mask.map"
            shutil.copy(mask_file_in_ps, mask_dir / "mask.map")
            forcing = generate_forcing
            m = Lisflood(
                version="20.10", parameter_set=parameterset, forcing=forcing
            )
            yield m
            if m.bmi:
                # Clean up container
                del m.bmi

        @pytest.fixture
        def model_with_setup(self, tmp_path, mocked_config, model: Lisflood):
            with patch.object(
                BmiClientSingularity, "__init__", return_value=None
            ) as mocked_constructor, patch(
                "datetime.datetime"
            ) as mocked_datetime:
                mocked_datetime.now.return_value = datetime(
                    2021, 1, 2, 3, 4, 5
                )
                config_file, config_dir = model.setup(
                    MaskMap=str(tmp_path / "custommask/mask.map")
                )
            return config_file, config_dir, mocked_constructor

        def test_setup(self, model_with_setup, tmp_path):
            config_file, config_dir, mocked_constructor = model_with_setup

            # Check setup returns
            expected_cfg_dir = CFG["output_dir"] / "lisflood_20210102_030405"
            assert config_dir == str(expected_cfg_dir)
            assert config_file == str(
                expected_cfg_dir / "lisflood_setting.xml"
            )

            # Check container started
            mocked_constructor.assert_called_once_with(
                image=f"{tmp_path}/ewatercycle-lisflood-grpc4bmi_20.10.sif",
                input_dirs=[
                    f"{tmp_path}/psr/lisflood_fraser",
                    f"{tmp_path}/forcing",
                    f"{tmp_path}/custommask",
                ],
                work_dir=f"{tmp_path}/lisflood_20210102_030405",
            )

            # Check content config file
            _cfg = XmlConfig(str(config_file))
            assert find_values_in_xml(_cfg.config, "CalendarDayStart") == {
                "02/01/1986 00:00"
            }
            assert find_values_in_xml(_cfg.config, "StepStart") == {"1"}
            assert find_values_in_xml(_cfg.config, "StepEnd") == {"11688"}
            assert find_values_in_xml(_cfg.config, "PathMeteo") == {
                f"{tmp_path}/forcing"
            }
            assert find_values_in_xml(_cfg.config, "PathOut") == {
                str(config_dir)
            }
            assert find_values_in_xml(_cfg.config, "IrrigationEfficiency") == {
                "0.75",
                "$(IrrigationEfficiency)",
            }
            assert find_values_in_xml(_cfg.config, "MaskMap") == {
                f"{tmp_path}/custommask/mask"
            }
            assert find_values_in_xml(_cfg.config, "PrefixPrecipitation") == {
                "mytp"
            }
            assert find_values_in_xml(_cfg.config, "PrefixTavg") == {"myta"}
            assert find_values_in_xml(_cfg.config, "PrefixE0") == {"mye0"}
            assert find_values_in_xml(_cfg.config, "PrefixES0") == {"es0"}
            assert find_values_in_xml(_cfg.config, "PrefixET0") == {"et0"}

        def test_parameters_after_setup(
            self, model_with_setup, model: Lisflood, tmp_path
        ):
            expected_parameters = [
                ("IrrigationEfficiency", "0.75"),
                ("MaskMap", f"{tmp_path}/custommask/mask"),
                ("start_time", "1986-01-02T00:00:00Z"),
                ("end_time", "2018-01-02T00:00:00Z"),
            ]
            assert model.parameters == expected_parameters


class MockedBmi(Bmi):
    """Mimic a real use case with realistic shape and abitrary high precision."""

    def get_var_grid(self, name):
        return 0

    def get_grid_shape(self, grid_id):
        return 14, 31  # shape returns (len(y), len(x))

    def get_grid_x(self, grid_id):
        return np.array(
            [
                -124.450000000003,
                -124.350000000003,
                -124.250000000003,
                -124.150000000003,
                -124.050000000003,
                -123.950000000003,
                -123.850000000003,
                -123.750000000003,
                -123.650000000003,
                -123.550000000003,
                -123.450000000003,
                -123.350000000003,
                -123.250000000003,
                -123.150000000003,
                -123.050000000003,
                -122.950000000003,
                -122.850000000003,
                -122.750000000003,
                -122.650000000003,
                -122.550000000003,
                -122.450000000003,
                -122.350000000003,
                -122.250000000003,
                -122.150000000003,
                -122.050000000003,
                -121.950000000003,
                -121.850000000003,
                -121.750000000003,
                -121.650000000003,
                -121.550000000003,
                -121.450000000003,
            ]
        )

    def get_grid_y(self, grid_id):
        return np.array(
            [
                53.950000000002,
                53.8500000000021,
                53.7500000000021,
                53.6500000000021,
                53.5500000000021,
                53.4500000000021,
                53.3500000000021,
                53.2500000000021,
                53.1500000000021,
                53.0500000000021,
                52.9500000000021,
                52.8500000000021,
                52.7500000000021,
                52.6500000000021,
            ]
        )

    def get_grid_spacing(self, grid_id):
        return 0.1, 0.1

    def get_value_at_indices(self, name, indices):
        self.indices = indices
        return np.array([1.0])
