from collections import defaultdict
from ruamel.yaml import YAML

from . import default, hype, lisflood, marrmot, pcrglobwb, wflow
from .datasets import DATASETS

FORCING_CLASSES = defaultdict(
    default.DefaultForcing,
    hype=hype.HypeForcing,
    lisflood=lisflood.LisfloodForcing,
    marrmot=marrmot.MarrmotForcing,
    pcrglobwb=pcrglobwb.PCRGlobWBForcing,
    wflow=wflow.WflowForcing,
    )

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

# TODO fix time conventions
# TODO add / fix tests
# TODO make sure model classes understand new forcing data objects
# TODO figure out how to disable doubly rendered docstrings
# https://stackoverflow.com/questions/51125415/how-do-i-document-a-constructor-for-a-class-using-python-dataclasses
