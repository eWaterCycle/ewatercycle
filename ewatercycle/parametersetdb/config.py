# -*- coding: utf-8 -*-
import configparser
from urllib.request import urlopen

from ruamel.yaml import YAML


class CaseConfigParser(configparser.ConfigParser):
    """Case sensitive config parser
    See https://stackoverflow.com/questions/1611799/preserve-case-in-configparser
    """
    def optionxform(self, optionstr):
        return optionstr


def fetch(url):
    """Fetches text of url"""
    with urlopen(url) as response:
        return response.read().decode()


class IniConfig:
    config = CaseConfigParser(strict=False)

    def __init__(self, source):
        body = fetch(source)
        self.config.read_string(body)

    def save(self, target):
        with open(target, 'w') as f:
            self.config.write(f)


class YamlConfig:
    yaml = YAML()

    def __init__(self, source):
        body = fetch(source)
        self.config = self.yaml.load(body)

    def save(self, target):
        with open(target, 'w') as f:
            self.yaml.dump(self.config, f)
