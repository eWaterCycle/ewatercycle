from pathlib import Path

import pytest


@pytest.fixture
def sample_marrmot_forcing_file():
    # Downloaded from
    # https://github.com/wknoben/MARRMoT/blob/master/BMI/Config/BMI_testcase_m01_BuffaloRiver_TN_USA.mat
    return str(
        Path(__file__).parent / "data" / "BMI_testcase_m01_BuffaloRiver_TN_USA.mat"
    )
