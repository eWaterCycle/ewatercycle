from ewatercycle.forcing._lisvap import XmlConfig, create_lisvap_config


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
