"""Forcing related functionality for default models"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict

from ruamel.yaml import YAML


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
    shape: Optional[str] = None
    """Shape file"""

    # Model-specific attributes (preferably with default values):
    # ...

    @classmethod
    def generate(cls,
                 dataset: str,
                 start_time: str,
                 end_time: str,
                 shape: str,
                 **_kwargs: Dict  # Subclasses can have additional named arguments, added to pass mypy
                 ) -> 'DefaultForcing':
        """Generate forcing data with ESMValTool."""
        raise NotImplementedError("No default forcing generator available.")

    def save(self):
        """Export forcing data for later use."""
        yaml = YAML()
        yaml.register_class(self.__class__)
        target = Path(self.directory) / 'ewatercycle_forcing.yaml'
        # TODO remove directory or set to .
        with open(target, 'w') as f:
            yaml.dump(self, f)
        return target

    def plot(self):
        raise NotImplementedError("No generic plotting method available.")
