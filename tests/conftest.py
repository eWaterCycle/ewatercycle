from collections import OrderedDict
from pathlib import Path

import pytest

from ewatercycle.parametersetdb import build_from_urls


@pytest.fixture
def yaml_config_url():
    return "data:text/plain,data: data/PEQ_Hupsel.dat\nparameters:\n  cW: 200\n  cV: 4\n  cG: 5.0e+6\n  cQ: 10\n  cS: 4\n  dG0: 1250\n  cD: 1500\n  aS: 0.01\n  st: loamy_sand\nstart: 367416 # 2011120000\nend: 368904 # 2012020000\nstep: 1\n"


@pytest.fixture
def yaml_config():
    return OrderedDict([
            ('data', 'data/PEQ_Hupsel.dat'),
            ('parameters', OrderedDict([
                ('cW', 200),
                ('cV', 4),
                ('cG', 5000000.0),
                ('cQ', 10),
                ('cS', 4),
                ('dG0', 1250),
                ('cD', 1500),
                ('aS', 0.01),
                ('st', 'loamy_sand')
            ])),
            ('start', 367416),
            ('end', 368904),
            ('step', 1)
        ])


@pytest.fixture
def sample_parameterset(yaml_config_url):
    return build_from_urls(
        config_format='yaml', config_url=yaml_config_url,
        datafiles_format='svn', datafiles_url='http://example.com',
    )


@pytest.fixture
def sample_shape():
    return str(Path(__file__).parents[1] / 'docs' / 'examples' / 'data' / 'Rhine' / 'Rhine.shp')

@pytest.fixture
def sample_marrmot_forcing_file():
    # Downloaded from
    # https://github.com/wknoben/MARRMoT/blob/master/BMI/Config/BMI_testcase_m01_BuffaloRiver_TN_USA.mat
    return str(Path(__file__).parent / 'models' / 'data' / 'BMI_testcase_m01_BuffaloRiver_TN_USA.mat')
