from datetime import datetime
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import numpy as np
import pytest
from grpc4bmi.bmi_client_apptainer import BmiClientApptainer

from ewatercycle import CFG
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.plugins.hype.model import Hype, _set_code_in_cfg
from ewatercycle.testing.fake_models import FailingModel
from ewatercycle.forcing import sources
HypeForcing = sources["HypeForcing"]


@pytest.fixture
def mocked_config(tmp_path):
    CFG.output_dir = tmp_path
    CFG.container_engine = "apptainer"
    CFG.apptainer_dir = tmp_path
    CFG.parameter_sets = {}
    CFG.parameterset_dir = tmp_path
    return CFG


@pytest.fixture
def parameter_set(mocked_config):
    # Contents copied/inspired by demo.zip at https://sourceforge.net/projects/hype/files/release_hype_5_6_2/
    directory = mocked_config.parameterset_dir / "hype_testcase"
    directory.mkdir(parents=True)
    config = directory / "info.txt"
    # write info.txt
    config.write_text(
        dedent(
            """\
                !!Information om k�rningen.
                bdate      1961-01-01
                cdate      1962-01-01
                edate      1963-12-31
                substance N P
                readobsid n
                !!basinoutput
                basinoutput variable prec temp cout ccIN ccON ccSP ccPP
                basinoutput subbasin 609
                basinoutput meanperiod   1
                basinoutput decimals 7
                !!mapoutput
                mapoutput variable cTNl cTPl prec ccTN ccTP
                mapoutput meanperiod  5
                mapoutput decimals 3
                !!timeoutput
                timeoutput variable   prec temp crun
                timeoutput meanperiod 3
                timeoutput decimals 2
            """
        )
    )

    # write some parameter file
    geodata = directory / "GeoData.txt"
    geodata.write_text(
        dedent(
            """NAME	SUBID	MAINDOWN	X	Y	AREA	ROWNR	ELEV_MEAN	SLOPE_MEAN	REGION	LAKEREGION	parreg	SLC_1	SLC_2	SLC_3	SLC_4	SLC_5	SLC_6	SLC_7	SLC_8	SLC_9	SLC_10	SLC_11	SLC_12	SLC_13	SLC_14	SLC_15	SLC_16	SLC_17	lake_depth	LAKEDATAID	wetdep_n	drydep_n1	drydep_n2	drydep_n3	RIVLEN	Icatch	close_w	buffer
        subareaname	609	0	6442230	1554840	5600000	1	11.1	0.031	80	5	2	0	0.117	0	0	00	0	0.125	0	0	0	0.754	0	0	0	0	0.004	3.3	0	540	0.7	1.1	0.4	2366.4	0.33	0.29	0.08
        """
        )
    )
    return ParameterSet(
        name="hype_testcase",
        directory=str(directory),
        config=str(config),
        target_model="hype",
    )


class TestWithOnlyParameterSetAndDefaults:
    @pytest.fixture
    def model(self, parameter_set):
        return Hype("feb2021", parameter_set)

    @pytest.fixture
    def model_with_setup(self, mocked_config, model: Hype):
        with patch.object(
            BmiClientApptainer, "__init__", return_value=None
        ) as mocked_constructor, patch("datetime.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)
            config_file, config_dir = model.setup()
        return config_file, config_dir, mocked_constructor

    def test_setup_container(self, model_with_setup, tmp_path):
        mocked_constructor = model_with_setup[2]
        mocked_constructor.assert_called_once_with(
            image="ewatercycle-hype-grpc4bmi_feb2021.sif",
            work_dir=f"{tmp_path}/hype_20210102_030405",
            input_dirs=[],
            timeout=None,
            delay=0,
        )

    def test_setup_parameter_set_files(self, model_with_setup):
        config_dir = model_with_setup[1]
        geodata = Path(config_dir) / "GeoData.txt"
        assert "subareaname" in geodata.read_text()

    def test_setup_config_file(self, model_with_setup):
        config_file = model_with_setup[0]
        expected = dedent(
            """\
                !!Information om k�rningen.
                bdate      1961-01-01
                cdate      1962-01-01
                edate      1963-12-31
                substance N P
                readobsid n
                !!basinoutput
                basinoutput variable prec temp cout ccIN ccON ccSP ccPP
                basinoutput subbasin 609
                basinoutput meanperiod   1
                basinoutput decimals 7
                !!mapoutput
                mapoutput variable cTNl cTPl prec ccTN ccTP
                mapoutput meanperiod  5
                mapoutput decimals 3
                !!timeoutput
                timeoutput variable   prec temp crun
                timeoutput meanperiod 3
                timeoutput decimals 2
                resultdir ./
        """
        )
        assert Path(config_file).read_text() == expected

    def test_parameters(self, model):
        expected = [
            ("start_time", "1961-01-01T00:00:00Z"),
            ("end_time", "1963-12-31T00:00:00Z"),
            ("crit_time", "1962-01-01T00:00:00Z"),
        ]
        assert model.parameters == expected

    def test_get_value_as_xarray(self, model):
        with pytest.raises(NotImplementedError):
            model.get_value_as_xarray("comp outflow olake")

    def test_get_value_at_coords(self, model):
        class MockedBmi(FailingModel):
            """Pretend to be a real BMI model."""

            def get_var_grid(self, name):
                return 1

            def get_grid_x(self, grid_id):
                return np.array(
                    [5.8953929, 4.9553967, 5.6387277]
                )  # x subbasin lons of subbasinsin hype

            def get_grid_y(self, grid_id):
                return np.array(
                    [51.16437912, 50.21104813, 48.6910553]
                )  # y are lats of subbasins in hype

            def get_value_at_indices(self, name, dest, indices):
                self.indices = indices
                return np.array([13.0])

            def get_var_type(self, name):
                return "float64"

            def get_var_itemsize(self, name):
                return np.float64().size

            def get_var_nbytes(self, name):
                return np.float64().size * 3 * 3

        model.bmi = MockedBmi()

        actual = model.get_value_at_coords("comp outflow olake", lon=[5], lat=[50])
        assert actual == np.array([13.0])
        assert model.bmi.indices == [1]


class TestWithOnlyParameterSetAndFullSetup:
    @pytest.fixture
    def model(self, parameter_set):
        return Hype("feb2021", parameter_set)

    @pytest.fixture
    def model_with_setup(self, mocked_config, model: Hype, tmp_path):
        with patch.object(
            BmiClientApptainer, "__init__", return_value=None
        ) as mocked_constructor, patch("datetime.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)
            config_file, config_dir = model.setup(
                start_time="2000-01-01T00:00:00Z",
                end_time="2010-12-31T00:00:00Z",
                crit_time="2002-01-01T00:00:00Z",
                cfg_dir=str(tmp_path / "myworkdir"),
            )
        return config_file, config_dir, mocked_constructor

    def test_setup_container(self, model_with_setup, tmp_path):
        mocked_constructor = model_with_setup[2]
        mocked_constructor.assert_called_once_with(
            image="ewatercycle-hype-grpc4bmi_feb2021.sif",
            work_dir=f"{tmp_path}/myworkdir",
            input_dirs=[],
            timeout=None,
            delay=0,
        )

    def test_setup_parameter_set_files(self, model_with_setup):
        config_dir = model_with_setup[1]
        geodata = Path(config_dir) / "GeoData.txt"
        assert "subareaname" in geodata.read_text()

    def test_setup_config_file(self, model_with_setup):
        config_file = model_with_setup[0]
        expected = dedent(
            """\
                !!Information om k�rningen.
                bdate 2000-01-01 00:00:00
                cdate 2002-01-01 00:00:00
                edate 2010-12-31 00:00:00
                substance N P
                readobsid n
                !!basinoutput
                basinoutput variable prec temp cout ccIN ccON ccSP ccPP
                basinoutput subbasin 609
                basinoutput meanperiod   1
                basinoutput decimals 7
                !!mapoutput
                mapoutput variable cTNl cTPl prec ccTN ccTP
                mapoutput meanperiod  5
                mapoutput decimals 3
                !!timeoutput
                timeoutput variable   prec temp crun
                timeoutput meanperiod 3
                timeoutput decimals 2
                resultdir ./
        """
        )
        assert Path(config_file).read_text() == expected

    def test_parameters(self, model_with_setup, model):
        expected = [
            ("start_time", "2000-01-01T00:00:00Z"),
            ("end_time", "2010-12-31T00:00:00Z"),
            ("crit_time", "2002-01-01T00:00:00Z"),
        ]
        assert model.parameters == expected


def test_set_code_in_cfg():
    content = dedent(
        """\
                !!Information om k�rningen.
                bdate      1961-01-01
                cdate      1962-01-01
                edate      1963-12-31
                substance N P
                readobsid n
                !!basinoutput
                basinoutput variable prec temp cout ccIN ccON ccSP ccPP
                basinoutput subbasin 609
                basinoutput meanperiod   1
                basinoutput decimals 7
                !!mapoutput
                mapoutput variable cTNl cTPl prec ccTN ccTP
                mapoutput meanperiod  5
                mapoutput decimals 3
                !!timeoutput
                timeoutput variable   prec temp crun
                timeoutput meanperiod 3
                timeoutput decimals 2
            """
    )

    actual = _set_code_in_cfg(content, "bdate", "2000-05-06")

    expected = dedent(
        """\
                !!Information om k�rningen.
                bdate 2000-05-06
                cdate      1962-01-01
                edate      1963-12-31
                substance N P
                readobsid n
                !!basinoutput
                basinoutput variable prec temp cout ccIN ccON ccSP ccPP
                basinoutput subbasin 609
                basinoutput meanperiod   1
                basinoutput decimals 7
                !!mapoutput
                mapoutput variable cTNl cTPl prec ccTN ccTP
                mapoutput meanperiod  5
                mapoutput decimals 3
                !!timeoutput
                timeoutput variable   prec temp crun
                timeoutput meanperiod 3
                timeoutput decimals 2
            """
    )
    assert actual == expected


class TestWithForcingAndDefaults:
    @pytest.fixture
    def forcing(self, tmp_path):
        forcing_dir = tmp_path / "forcing"
        forcing_dir.mkdir()
        pobs = forcing_dir / "Pobs.txt"
        pobs.write_text(
            dedent(
                """\
            DATE	609
            1986-01-02	0.6
            """
            )
        )
        return HypeForcing(
            forcing="hype",
            start_time="1986-01-02T00:00:00Z",
            end_time="2018-01-02T00:00:00Z",
            directory=str(forcing_dir),
            Pobs=pobs.name,
        )

    @pytest.fixture
    def model(self, parameter_set, forcing):
        return Hype("feb2021", parameter_set, forcing)

    @pytest.fixture
    def model_with_setup(self, mocked_config, model: Hype):
        with patch.object(
            BmiClientApptainer, "__init__", return_value=None
        ) as mocked_constructor, patch("datetime.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)
            config_file, config_dir = model.setup()
        return config_file, config_dir, mocked_constructor

    def test_setup_container(self, model_with_setup, tmp_path):
        mocked_constructor = model_with_setup[2]
        mocked_constructor.assert_called_once_with(
            image="ewatercycle-hype-grpc4bmi_feb2021.sif",
            work_dir=f"{tmp_path}/hype_20210102_030405",
            input_dirs=[],
            timeout=None,
            delay=0,
        )

    def test_setup_forcing_files(self, model_with_setup):
        config_dir = model_with_setup[1]
        pobs = Path(config_dir) / "Pobs.txt"
        assert "DATE" in pobs.read_text()

    def test_setup_parameter_set_files(self, model_with_setup):
        config_dir = model_with_setup[1]
        geodata = Path(config_dir) / "GeoData.txt"
        assert "subareaname" in geodata.read_text()

    def test_setup_config_file(self, model_with_setup):
        config_file = model_with_setup[0]
        expected = dedent(
            """\
                !!Information om k�rningen.
                bdate 1986-01-02 00:00:00
                cdate 1986-01-02 00:00:00
                edate 2018-01-02 00:00:00
                substance N P
                readobsid n
                !!basinoutput
                basinoutput variable prec temp cout ccIN ccON ccSP ccPP
                basinoutput subbasin 609
                basinoutput meanperiod   1
                basinoutput decimals 7
                !!mapoutput
                mapoutput variable cTNl cTPl prec ccTN ccTP
                mapoutput meanperiod  5
                mapoutput decimals 3
                !!timeoutput
                timeoutput variable   prec temp crun
                timeoutput meanperiod 3
                timeoutput decimals 2
                resultdir ./
        """
        )
        assert Path(config_file).read_text() == expected

    def test_parameters(self, model):
        expected = [
            ("start_time", "1986-01-02T00:00:00Z"),
            ("end_time", "2018-01-02T00:00:00Z"),
            ("crit_time", "1986-01-02T00:00:00Z"),
        ]
        assert model.parameters == expected
