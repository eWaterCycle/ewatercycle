from collections import defaultdict
from ruamel.yaml import YAML

from . import default, hype, lisflood, marrmot, pcrglobwb, wflow
from .recipe_generator import RecipeGenerator

FORCING_CLASSES = defaultdict(default.DefaultForcing, wflow=wflow.WflowForcing)


def generate(target_model: str, **kwargs):
    """Generate forcing data for model evaluation.

    Args:
        target_model: Name of the model
        **kwargs: Model specific recipe settings

    Returns:
        :obj:`ForcingData`
    """
    Forcing = FORCING_CLASSES[target_model]
    return Forcing.generate(**kwargs)


def load(target_model, **kwargs):
    """Load existing forcing data from disk.

    Args:
        target_model: Name of the hydrological model for which the forcing will be used
        **kwargs: Model specific configuration settings related to the forcing data

    Returns:
        :obj:`ForcingData`
    """
    Forcing = FORCING_CLASSES[target_model]
    return Forcing(**kwargs)


def reload(directory):
    """Reload previously generated forcing data.

    Args:
        directory: forcing data directory; must contain `ewatercycle_forcing.yaml`
    """
    yaml = YAML()
    source = Path(directory) / 'ewatercycle_forcing.yaml'
    data = yaml.load(source)

    target_model = data.pop('model')
    Forcing = FORCING_CLASSES[target_model]
    return Forcing(**data)
