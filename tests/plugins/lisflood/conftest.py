from pathlib import Path

import pytest


@pytest.fixture
def sample_lisvap_config():
    return str(Path(__file__).parent / "data" / "settings_lisvap.xml")
