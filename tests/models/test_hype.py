from datetime import datetime
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
from genericpath import exists
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.models.hype import Hype
from ewatercycle.parameter_sets import ParameterSet


@pytest.fixture
def mocked_config(tmp_path):
    CFG["output_dir"] = tmp_path
    CFG["container_engine"] = "singularity"
    CFG["singularity_dir"] = tmp_path
    CFG["parameterset_dir"] = tmp_path / "psr"
    CFG["parameter_sets"] = {}
    return CFG


@pytest.fixture
def parameter_set(mocked_config):
    # Contents copied/inspired by demo.zip at https://sourceforge.net/projects/hype/files/release_hype_5_18_0/
    directory = mocked_config["parameterset_dir"] / "hype_testcase"
    directory.mkdir(parents=True)
    config = directory / "info.txt"

    # TODO write info.txt

    # write some parameter file
    geodata = directory / "GeoData.txt"
    geodata.write_text(
        dedent(
            """NAME	SUBID	MAINDOWN	X	Y	AREA	ROWNR	ELEV_MEAN	SLOPE_MEAN	REGION	LAKEREGION	parreg	SLC_1	SLC_2	SLC_3	SLC_4	SLC_5	SLC_6	SLC_7	SLC_8	SLC_9	SLC_10	SLC_11	SLC_12	SLC_13	SLC_14	SLC_15	SLC_16	SLC_17	lake_depth	LAKEDATAID	wetdep_n	drydep_n1	drydep_n2	drydep_n3	RIVLEN	Icatch	close_w	buffer
        subareaname	609	0	6442230	1554840	5600000	1	11.1	0.031	80	5	2	0	0.117	0	0	00	0	0.125	0	0	0	0.754	0	0	0	0	0.004	3.3	0	540	0.7	1.1	0.4	2366.4	0.33	0.29	0.08
        """
        )
    )

    # TODO write forcing files as part of parameter set

    return ParameterSet(
        "hype_testcase",
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
            BmiClientSingularity, "__init__", return_value=None
        ) as mocked_constructor, patch("datetime.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = datetime(2021, 1, 2, 3, 4, 5)
            config_file, config_dir = model.setup()
        return config_file, config_dir, mocked_constructor

    def test_setup_container(self, model_with_setup, tmp_path):
        mocked_constructor = model_with_setup[2]
        mocked_constructor.assert_called_once_with(
            image=f"{tmp_path}/ewatercycle-hype-grpc4bmi_feb2021.sif",
            work_dir=f"{tmp_path}/hype_20210102_030405",
        )

    def test_setup_parameter_set_files(self, model_with_setup):
        config_dir = model_with_setup[1]
        geodata = Path(config_dir) / "GeoData.txt"
        assert "subareaname" in geodata.read_text()

    def test_parameters(self, model):
        expected = []
        assert model.parameters == expected
