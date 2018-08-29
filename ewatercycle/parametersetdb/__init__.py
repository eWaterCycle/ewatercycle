# -*- coding: utf-8 -*-
"""Documentation about ewatercycle_parametersetdb"""
from ewatercycle.parametersetdb.config import IniConfig, YamlConfig
from ewatercycle.parametersetdb.datafiles import SubversionCopier
from ewatercycle.parametersetdb.version import __version__

CONFIG_FORMATS = {
    'ini': IniConfig,
    'yaml': YamlConfig,
}

DATAFILES_FORMATS = {
    'svn': SubversionCopier
}


class ParameterSet:
    def __init__(self, df, cfg):
        self.df = df
        self._cfg = cfg

    def save_datafiles(self, target):
        self.df.save(target)

    def save_config(self, target):
        self._cfg.save(target)

    @property
    def config(self):
        return self._cfg.config
