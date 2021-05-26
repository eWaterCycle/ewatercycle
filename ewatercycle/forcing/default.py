"""Forcing related functionality for default models"""

from dataclasses import dataclass
from ruamel.yaml import YAML


@dataclass
class DefaultForcing:
    """Container for forcing data.

    Attributes:
        directory (str): Location where the forcing data is stored
        start_time (str): Start time of the forcing data
        end_time (str): End time of the forcing data
    """
    directory: str
    start_time: str
    end_time: str

    @classmethod
    def generate(**kwargs):
        """Generate forcing data with ESMValTool."""
        raise NotImplementedError("No default forcing generator available.")

    def save(self):
        """Export forcing data for later use."""
        yaml = YAML()
        target = Path(self.directory) / 'ewatercycle_forcing.yaml'
        data = dict(model='default', **self.__dict__)
        with open(target, 'w') as f:
            yaml.dump(data, f)
        return target

    def plot(self):
        raise NotImplementedError("No generic plotting method available.")
