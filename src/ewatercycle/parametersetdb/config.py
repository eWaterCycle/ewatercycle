# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from configparser import ConfigParser
from typing import Any, Dict, Type
from urllib.request import urlopen
from xml.etree import ElementTree as ET

from ruamel.yaml import YAML


class CaseConfigParser(ConfigParser):
    """Case sensitive config parser
    See https://stackoverflow.com/questions/1611799/preserve-case-in-configparser
    """

    def optionxform(self, optionstr):
        return optionstr


def fetch(url):
    """Fetches text of url"""
    with urlopen(url) as response:
        return response.read().decode()


class AbstractConfig(ABC):
    @abstractmethod
    def __init__(self, source: str):
        """Fetches and parses config file

        Args:
            source:  Source url of config file
        """
        self.source = source
        self.config: Any = None
        """Dict like content of config """

    @abstractmethod
    def save(self, target: str):
        """

        Args:
            target: File path to save config to

        Returns:

        """
        pass


class IniConfig(AbstractConfig):
    """Config container where config is read/saved in ini format."""

    def __init__(self, source):
        super().__init__(source)
        body = fetch(source)
        self.config = CaseConfigParser(strict=False)
        self.config.read_string(body)

    def save(self, target):
        with open(target, "w") as f:
            self.config.write(f)


class YamlConfig(AbstractConfig):
    """Config container where config is read/saved in yaml format"""

    yaml = YAML()

    def __init__(self, source):
        super().__init__(source)
        body = fetch(source)
        self.config = self.yaml.load(body)

    def save(self, target):
        with open(target, "w") as f:
            self.yaml.dump(self.config, f)


CONFIG_FORMATS: Dict[str, Type[AbstractConfig]] = {
    "ini": IniConfig,
    "yaml": YamlConfig,
}


class XmlConfig(AbstractConfig):
    """Config container where config is read/saved in xml format."""

    def __init__(self, source):
        """Config container where config is read/saved in xml format.

        Args:
            source: file to read from
        """
        super().__init__(source)
        self.tree = ET.parse(source)
        self.config: ET.Element = self.tree.getroot()
        """XML element used to make changes to the config"""

    def save(self, target):
        """Save xml to file.

        Args:
            target: file to save to

        """
        self.tree.write(target)
