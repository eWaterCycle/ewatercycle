from collections import defaultdict
from ruamel.yaml import YAML
from typing import TypeVar

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

# Return type for DefaultForcing including subtypes.
Forcing = TypeVar('Forcing', bound=default.DefaultForcing)

def generate(target_model: str, **kwargs) -> Forcing:
    """Generate forcing data with ESMValTool.

    Args:
        target_model: Name of the model
        **kwargs: Model specific recipe settings

    Returns:
        Forcing object, e.g. :obj:`.lisflood.LisfloodForcing`
    """
    Forcing = FORCING_CLASSES[target_model]
    return Forcing.generate(**kwargs)


def load(directory) -> Forcing:
    """Load previously generated or imported forcing data.

    Args:
        directory: forcing data directory; must contain `ewatercycle_forcing.yaml`

    Returns:
        Forcing object, e.g. :obj:`.marrmot.MarrmotForcing`
    """
    yaml = YAML()
    source = Path(directory) / 'ewatercycle_forcing.yaml'
    data = yaml.load(source)

    target_model = data.pop('model')
    Forcing = FORCING_CLASSES[target_model]
    return Forcing(**data)


def load_foreign(target_model, **kwargs) -> Forcing:
    """Load existing forcing data generated from an external source.

    Args:
        target_model: Name of the hydrological model for which the forcing will be used
        **kwargs: Model specific configuration settings related to the forcing
            data. For each model you can see the available settings in the corresponding
            Forcing object, e.g. :obj:`.wflow.WflowForcing`.

    Returns:
        Forcing object, e.g. :obj:`.hype.HypeForcing`
    """
    Forcing = FORCING_CLASSES[target_model]
    return Forcing(**kwargs)


# TODO fix time conventions
# TODO add / fix tests
# TODO make sure model classes understand new forcing data objects
