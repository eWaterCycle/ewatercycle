import pytest

from ewatercycle.forcing._lisvap import create_lisvap_config, lisvap, XmlConfig


def find_values_in_xml(tree, name):
    values = []
    for textvar in tree.iter("textvar"):
        textvar_name = textvar.attrib["name"]
        if textvar_name == name:
            values.append(textvar.get("value"))
    return set(values)


def test_create_lisvap_config(tmp_path, sample_lisvap_config):
    config_file = create_lisvap_config(
        str(tmp_path),
        str(tmp_path),
        "ERA5",
        sample_lisvap_config,
        str(tmp_path / "MaskMap_Rhine.nc"),
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
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
    assert find_values_in_xml(_cfg.config, "PathBaseMapsIn") == {f"{tmp_path}/maps_netcdf"}
    assert find_values_in_xml(_cfg.config, "MaskMap") == {f"{tmp_path}/MaskMap_Rhine"}
    assert find_values_in_xml(_cfg.config, "PathMeteoIn") == {str(tmp_path)}
    assert find_values_in_xml(_cfg.config, "PrefixE0") == {"lisflood_ERA5_e0_1989_1999"}
    assert find_values_in_xml(_cfg.config, "TAvgMaps") == {"$(PathMeteoIn)/lisflood_ERA5_tas_1989_1999"}




