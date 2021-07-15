from ewatercycle import CFG
from ewatercycle.parameter_sets import download_example_parameter_sets


def test_download_example_parameter_sets(tmp_path):
    CFG["parameterset_dir"] = tmp_path / "parameters"
    download_example_parameter_sets()

    assert (tmp_path / "parameters" / "pcrglobwb_rhinemeuse_30min").exists()
    assert (tmp_path / "parameters/pcrglobwb_rhinemeuse_30min/setup_natural_test.ini").exists()


# TODO test for the case where ewatercycle.yaml cfg is not writable
# TODO test for NoneType paths in CFG
