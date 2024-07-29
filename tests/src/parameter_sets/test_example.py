import logging
from pathlib import Path

import pytest

from ewatercycle import CFG
from ewatercycle.parameter_sets import ParameterSet


@pytest.fixture()
def setup_config(tmp_path):
    CFG.parameterset_dir = tmp_path
    CFG.parameter_sets = {}
    CFG.ewatercycle_config = None
    yield CFG
    # Rollback changes made to CFG by tests
    CFG.parameter_sets = {}
    CFG.reload()


@pytest.fixture()
def example(setup_config, tmp_path: Path):
    ps_dir = tmp_path / "mymodelexample"
    ps_dir.mkdir()
    ps_config = ps_dir / "config.ini"
    ps_config.write_text("some config")
    ps = ParameterSet(
        name="firstexample",
        directory=Path("mymodelexample"),
        config=Path("config.ini"),
        supported_model_versions={"0.4.2"},
    )
    ps.make_absolute(tmp_path)
    return ps


def test_download_already_exists_but_skipped(example, tmp_path: Path, caplog):
    ps_dir = tmp_path / "mymodelexample"
    ps_dir.mkdir(exist_ok=True)

    # Make a mock downloader to assert it is not called
    #  mocking the property is not possible, as the object has to be initiated first
    def mock_downloader(_):
        assert False, ".downloader should not be called."  # noqa: B011

    example.downloader = mock_downloader

    with caplog.at_level(logging.INFO):
        example.download(download_dir=ps_dir, force=False)

    assert "already exists and download is not forced, skipping download" in caplog.text
