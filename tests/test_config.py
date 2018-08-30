#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the ewatercycle_parametersetdb module.
"""
from ewatercycle.parametersetdb.config import fetch, YamlConfig


def test_fetch(yaml_config_url):
    result = fetch(yaml_config_url)

    assert 'PEQ_Hupsel.dat' in result


class TestYamlConfig:
    def test_construct_from_data_url(self, yaml_config_url, yaml_config):
        conf = YamlConfig(yaml_config_url)

        assert conf.config == yaml_config

    def test_save(self, tmpdir, yaml_config_url):
        conf = YamlConfig(yaml_config_url)
        fn = tmpdir.join('myconfig.yml')

        conf.save(str(fn))

        assert 'PEQ_Hupsel.dat' in fn.read()
