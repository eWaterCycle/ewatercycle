#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the ewatercycle_parametersetdb module.
"""
from collections import OrderedDict

import pytest

from ewatercycle.parametersetdb.config import fetch, YamlConfig


@pytest.fixture
def yaml_config_url():
    return "data:text/plain,data: data/PEQ_Hupsel.dat\nparameters:\n  cW: 200\n  cV: 4\n  cG: 5.0e+6\n  cQ: 10\n  cS: 4\n  dG0: 1250\n  cD: 1500\n  aS: 0.01\n  st: loamy_sand\nstart: 367416 # 2011120000\nend: 368904 # 2012020000\nstep: 1\n"


def test_fetch(yaml_config_url):
    result = fetch(yaml_config_url)
    assert 'PEQ_Hupsel.dat' in result


class TestYamlConfig:
    def test_construct_from_data_url(self, yaml_config_url):
        conf = YamlConfig(yaml_config_url)
        expected = OrderedDict([
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
        assert conf.config == expected

    def test_save(self, tmpdir, yaml_config_url):
        conf = YamlConfig(yaml_config_url)
        fn = tmpdir.join('myconfig.yml')

        conf.save(str(fn))

        assert 'PEQ_Hupsel.dat' in fn.read()
