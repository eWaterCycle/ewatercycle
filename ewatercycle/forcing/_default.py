"""Forcing related functionality for default models"""
from copy import copy
from pathlib import Path
from typing import Optional
import logging

from ruamel.yaml import YAML

from ewatercycle.util import to_absolute_path

logger = logging.getLogger(__name__)

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
        self.directory = to_absolute_path(directory)
        self.shape = to_absolute_path(shape) if shape is not None else shape

    def __str__(self):
        """Nice formatting of forcing object."""
        return "\n".join(
            [
                "eWaterCycle forcing",
                "-------------------",
            ]
            + [f"{k}={v!s}" for k, v in self.__dict__.items()]
        )

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
        target = self.directory / FORCING_YAML
        # We want to make the yaml and its parent movable,
        # so the directory and shape should not be included in the yaml file
        clone = copy(self)
        del clone.directory

        if clone.shape:
            try:
                clone.shape = str(clone.shape.relative_to(self.directory))
            except ValueError:
                clone.shape = None
                logger.info(f"Shapefile {self.shape} is not in forcing directory {self.directory}. So, it won't be saved in {target}.")

        with open(target, 'w') as f:
            yaml.dump(clone, f)
        return target

    def plot(self):
        raise NotImplementedError("No generic plotting method available.")

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
