import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from ewatercycle import CFG
from ewatercycle.config._config_object import Config


def test_config_object():
    """Test that the config is of the right type."""
    assert isinstance(CFG, Config)


def test_singularity_dir_is_deprecated(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger="ewatercycle.config._config_object"):
        config = Config(**{"singularity_dir": str(tmp_path)})

        assert config.apptainer_dir == tmp_path
        assert "singularity_dir has been deprecated" in caplog.text
