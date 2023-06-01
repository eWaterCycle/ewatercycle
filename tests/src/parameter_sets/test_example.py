import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ewatercycle import CFG
from ewatercycle.parameter_sets import ParameterSet


@pytest.fixture
def setup_config(tmp_path):
    CFG.parameterset_dir = tmp_path
    CFG.parameter_sets = {}
    CFG.ewatercycle_config = None
    yield CFG
    # Rollback changes made to CFG by tests
    print(CFG)
    CFG.parameter_sets = {}
    CFG.reload()


@pytest.fixture
def example(setup_config, tmp_path: Path):
    ps_dir = tmp_path / "mymodelexample"
    ps_dir.mkdir()
    ps_config = ps_dir / "config.ini"
    ps_config.write_text("some config")
    ps = ParameterSet(  # TODO CHECK WITH PETER/STEFAN
        name="firstexample",
        #config_url="https://github.com/mymodelorg/mymodelrepo/raw/master/mymodelexample/config.ini",  # noqa: E501
        #datafiles_url="https://github.com/mymodelorg/mymodelrepo/trunk/mymodelexample",
        directory=Path("mymodelexample"),
        config=Path("config.ini"),
        supported_model_versions={"0.4.2"},
    )
    ps.make_absolute(tmp_path)
    return ps


@pytest.mark.skip("ParameterSet.to_config is deprecated?")
def test_to_config(example, tmp_path):
    example.to_config()

    assert "firstexample" in CFG.parameter_sets
    expected = dict(
        doi="N/A",
        target_model="generic",
        directory="mymodelexample",
        config="mymodelexample/config.ini",
        supported_model_versions={"0.4.2"},
    )
    assert CFG.parameter_sets["firstexample"] == expected


@patch("urllib.request.urlopen")
@patch("subprocess.check_call")
@pytest.mark.skip("No downloaders are implemented.")
def test_download(
    mock_check_call,
    mock_urlopen,
    example, #: "ExampleParameterSet", 
    tmp_path
):
    example.config.unlink()
    example.directory.rmdir()
    ps_dir = tmp_path / "mymodelexample"
    r = Mock()
    r.read.return_value = b"somecontent"
    mock_urlopen.return_value = r
    mock_check_call.side_effect = lambda _: ps_dir.mkdir()

    example.download(download_dir=ps_dir)

    mock_urlopen.assert_called_once_with(
        "https://github.com/mymodelorg/mymodelrepo/raw/master/mymodelexample/config.ini"
    )
    mock_check_call.assert_called_once_with(
        [
            "svn",
            "export",
            "https://github.com/mymodelorg/mymodelrepo/trunk/mymodelexample",
            ps_dir,
        ]
    )
    assert (ps_dir / "config.ini").read_text() == "somecontent"


# TODO: Check with Stefan/Peter
# should this check of the download dir exists, or the config path?
# Also: ParameterSet.download only logs, does not raise error.
@pytest.mark.skip("Superceded by the next test?")
def test_download_already_exists(example, tmp_path: Path):
    ps_dir = tmp_path / "mymodelexample"
    ps_dir.mkdir(exist_ok=True)

    with pytest.raises(ValueError) as excinfo:
        example.download(download_dir=ps_dir)

    assert "already exists, will not overwrite." in str(excinfo.value)


def test_download_already_exists_but_skipped(
    example, tmp_path: Path, caplog
):
    ps_dir = tmp_path / "mymodelexample"
    ps_dir.mkdir(exist_ok=True)

    # Make a mock downloader to assert it is not called
    #  mocking the property is not possible, as the object has to be initiated first
    def mock_downloader(_): 
        assert False, ".downloader should not be called."
    example.downloader = mock_downloader

    with caplog.at_level(logging.INFO):
        example.download(download_dir=ps_dir, force=False)

    assert "already exists and download is not forced, skipping download" in caplog.text
