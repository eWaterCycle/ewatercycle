from pathlib import Path

import pytest

from ewatercycle.testing.fixtures import mocked_config, sample_shape


@pytest.fixture
def sample_lisvap_config():
    return str(Path(__file__).parent / "data" / "settings_lisvap.xml")
