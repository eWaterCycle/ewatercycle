# -*- coding: utf-8 -*-
"""Documentation about ewatercycle_parametersetdb"""
from typing import Any

from ewatercycle.parametersetdb.config import AbstractConfig, CONFIG_FORMATS
from ewatercycle.parametersetdb.datafiles import AbstractCopier, DATAFILES_FORMATS


class ParameterSet:
    def __init__(self, df: AbstractCopier, cfg: AbstractConfig):
        """Parameter set holds the config and datafiles required as input for a model

        Args:
            df: datafiles url container
            cfg: config container
        """
        self.df = df
        self._cfg = cfg

    def save_datafiles(self, target):
        """Saves datafiles to target directory

        Args:
            target: Path of target directory

        """
        self.df.save(target)

    def save_config(self, target):
        """Saves config file as target filename

        Args:
            target: filename of config file
        """
        self._cfg.save(target)

    @property
    def config(self) -> Any:
        """Configuration as dictionary.

        To make changes to configuration before saving set the config keys and/or values.

        Can be a nested dict.
        """
        return self._cfg.config


def build_from_urls(config_format, config_url, datafiles_format, datafiles_url) -> ParameterSet:
    """Construct ParameterSet based on urls

    Args:
        config_format: Format of file found at config url
        config_url: Url of config file
        datafiles_format: Method to stage datafiles url
        datafiles_url: Source url of datafiles
    """
    return ParameterSet(
        DATAFILES_FORMATS[datafiles_format](datafiles_url),
        CONFIG_FORMATS[config_format](config_url),
    )
