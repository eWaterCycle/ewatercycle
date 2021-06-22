"""Forcing related functionality for default models"""
from copy import copy
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

FORCING_YAML = 'ewatercycle_forcing.yaml'


class DefaultForcing:
    """Container for forcing data.

    Args:
        directory: Directory where forcing data files are stored.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
    """
    def __init__(self,
                 start_time: str,
                 end_time: str,
                 directory: str,
                 shape: Optional[str] = None):
        self.start_time = start_time
        self.end_time = end_time
        self.directory = directory
        self.shape = shape

    @classmethod
    def generate(
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        **model_specific_options,
    ) -> 'DefaultForcing':
        """Generate forcing data with ESMValTool."""
        raise NotImplementedError("No default forcing generator available.")

    def save(self):
        """Export forcing data for later use."""
        yaml = YAML()
        yaml.register_class(self.__class__)
        target = Path(self.directory) / FORCING_YAML
        # We want to make the yaml and its parent movable,
        # so the directory should not be included in the yaml file
        clone = copy(self)
        del clone.directory
        with open(target, 'w') as f:
            yaml.dump(clone, f)
        return target

    def plot(self):
        raise NotImplementedError("No generic plotting method available.")

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
