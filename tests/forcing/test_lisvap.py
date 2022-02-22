import os
import subprocess
from pathlib import PosixPath
from unittest.mock import patch

import pytest

from ewatercycle import CFG
from ewatercycle.forcing._lisvap import XmlConfig, create_lisvap_config, lisvap


def find_values_in_xml(tree, name):
    values = []
    for textvar in tree.iter("textvar"):
        textvar_name = textvar.attrib["name"]
        if textvar_name == name:
            values.append(textvar.get("value"))
    return set(values)


def test_create_lisvap_config(tmp_path, sample_lisvap_config):
    forcing_files = {
        "pr": "lisflood_ERA5_Rhine_pr_1989_1999.nc",
        "e": "lisflood_ERA5_Rhine_e_1989_1999.nc",
        "tas": "lisflood_ERA5_Rhine_tas_1989_1999.nc",
        "rsds": "lisflood_ERA5_Rhine_rsds_1989_1999.nc",
        "sfcWind": "lisflood_ERA5_Rhine_sfcWind_1989_1999.nc",
        "tasmax": "lisflood_ERA5_Rhine_tasmax_1989_1999.nc",
        "tasmin": "lisflood_ERA5_Rhine_tasmin_1989_1999.nc",
        "e0": "lisflood_ERA5_Rhine_e0_1989_1999.nc",
        "es0": "lisflood_ERA5_Rhine_es0_1989_1999.nc",
        "et0": "lisflood_ERA5_Rhine_et0_1989_1999.nc",
    }
    config_file = create_lisvap_config(
        str(tmp_path),
        str(tmp_path),
        "ERA5",
        sample_lisvap_config,
        str(tmp_path / "MaskMap_Rhine.nc"),
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        forcing_files=forcing_files,
    )

    # Check the name of new config file
    expected_config_file = str(tmp_path / "lisvap_ERA5_setting.xml")
    assert config_file == expected_config_file

    # Check content config file
    _cfg = XmlConfig(str(config_file))
    assert find_values_in_xml(_cfg.config, "CalendarDayStart") == {"02/01/1989 00:00"}
    assert find_values_in_xml(_cfg.config, "StepStart") == {"02/01/1989 00:00"}
    assert find_values_in_xml(_cfg.config, "StepEnd") == {"02/01/1999 00:00"}
    assert find_values_in_xml(_cfg.config, "PathOut") == {str(tmp_path)}
    assert find_values_in_xml(_cfg.config, "PathBaseMapsIn") == {
        f"{tmp_path}/maps_netcdf"
    }
    assert find_values_in_xml(_cfg.config, "MaskMap") == {f"{tmp_path}/MaskMap_Rhine"}
    assert find_values_in_xml(_cfg.config, "PathMeteoIn") == {str(tmp_path)}
    assert find_values_in_xml(_cfg.config, "PrefixE0") == {
        "lisflood_ERA5_Rhine_e0_1989_1999"
    }
    assert find_values_in_xml(_cfg.config, "TAvgMaps") == {
        "$(PathMeteoIn)/lisflood_ERA5_Rhine_tas_1989_1999"
    }


@pytest.fixture
def mocked_config(tmp_path):
    CFG["output_dir"] = tmp_path
    CFG["container_engine"] = "singularity"
    CFG["singularity_dir"] = tmp_path
    CFG["parameterset_dir"] = tmp_path / "psr"
    CFG["parameter_sets"] = {}


def prep_lisvap_input(tmp_path):
    CFG["parameterset_dir"].mkdir()
    forcing_dir = tmp_path / "forc"
    forcing_dir.mkdir()
    mask_map = CFG["parameterset_dir"] / "mask.nc"
    mask_map.write_text("Some file content")
    config_file = tmp_path / "lisvap.xml"
    config_file.write_text("Some file content")
    return config_file, forcing_dir, mask_map


@patch("subprocess.Popen")
def test_lisvap_singularity(mocked_popen, tmp_path, mocked_config):
    config_file, forcing_dir, mask_map = prep_lisvap_input(tmp_path)
    mocked_popen.return_value.communicate.return_value = ("output", "error")
    mocked_popen.return_value.wait.return_value = 0

    exit_code, stdout, stderr = lisvap(
        "20.10",
        str(CFG["parameterset_dir"]),
        str(forcing_dir),
        str(mask_map),
        str(config_file),
    )

    expected = [
        "singularity",
        "exec",
        "--bind",
        f"{tmp_path}/psr:{tmp_path}/psr,{tmp_path}/psr/mask.nc:{tmp_path}/psr/mask.nc,{tmp_path}/forc:{tmp_path}/forc",
        "--pwd",
        f"{tmp_path}/forc",
        PosixPath(f"{tmp_path}/ewatercycle-lisflood-grpc4bmi_20.10.sif"),
        "python3",
        "/opt/Lisvap/src/lisvap1.py",
        f"{tmp_path}/lisvap.xml",
    ]
    mocked_popen.assert_called_with(
        expected, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    assert exit_code == 0
    assert stderr == "error"
    assert stdout == "output"


@patch("subprocess.Popen")
def test_lisvap_docker(mocked_popen, tmp_path, mocked_config):
    CFG["container_engine"] = "docker"
    config_file, forcing_dir, mask_map = prep_lisvap_input(tmp_path)
    mocked_popen.return_value.communicate.return_value = ("output", "error")
    mocked_popen.return_value.wait.return_value = 0

    exit_code, stdout, stderr = lisvap(
        "20.10",
        str(CFG["parameterset_dir"]),
        str(forcing_dir),
        str(mask_map),
        str(config_file),
    )

    expected = [
        "docker",
        "run",
        "-ti",
        "--volume",
        f"{tmp_path}/psr:{tmp_path}/psr,{tmp_path}/psr/mask.nc:{tmp_path}/psr/mask.nc,{tmp_path}/forc:{tmp_path}/forc",
        "--pwd",
        f"{tmp_path}/forc",
        "ewatercycle/lisflood-grpc4bmi:20.10",
        "python3",
        "/opt/Lisvap/src/lisvap1.py",
        f"{tmp_path}/lisvap.xml",
    ]
    mocked_popen.assert_called_with(
        expected, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    assert exit_code == 0
    assert stderr == "error"
    assert stdout == "output"
