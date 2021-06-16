"""Forcing related functionality for default models"""

from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML


class DefaultForcing:
    """Container for forcing data.

    Args:
        dataset: Name of the source dataset. See :py:data:`.DATASETS`.
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

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
