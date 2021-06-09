"""Forcing related functionality for default models"""
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

FORCING_YAML = 'ewatercycle_forcing.yaml'


@dataclass
class DefaultForcing:
    """Container for forcing data."""

    # Default attributes that every forcing class should have:
    start_time: str
    """Start time of the forcing data"""
    end_time: str
    """End time of the forcing data"""
    directory: str = '.'
    """Location where the forcing data is stored."""
    shape: str = None
    """Shape file"""

    # Model-specific attributes (preferably with default values):
    # ...

    @classmethod
    def generate(cls,
                 dataset: str,
                 start_time: str,
                 end_time: str,
                 shape: str,
                 ) -> 'DefaultForcing':
        """Generate forcing data with ESMValTool."""
        raise NotImplementedError("No default forcing generator available.")

    def save(self):
        """Export forcing data for later use."""
        yaml = YAML()
        yaml.register_class(self.__class__)
        target = Path(self.directory) / FORCING_YAML
        # We want to make the yaml and its parent moveable,
        # so the directory should not be included in the yaml file
        inner_file = StringIO()
        yaml.dump(self, inner_file)
        inner = inner_file.getvalue()
        inner = inner.replace(f'directory: {self.directory}\n', '')
        with open(target, 'w') as f:
            f.write(inner)
        return target

    def plot(self):
        raise NotImplementedError("No generic plotting method available.")
