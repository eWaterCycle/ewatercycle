from pathlib import Path
from ruamel.yaml import YAML

from . import default, hype, lisflood, marrmot, pcrglobwb, wflow
from .datasets import DATASETS

FORCING_CLASSES = {  # not sure how to annotate this
    "hype": hype.HypeForcing,
    "lisflood": lisflood.LisfloodForcing,
    "marrmot": marrmot.MarrmotForcing,
    "pcrglobwb": pcrglobwb.PCRGlobWBForcing,
    "wflow": wflow.WflowForcing,
}


def generate(target_model: str, dataset, start_time, end_time, shape, model_specific_options):
    """Generate forcing data with ESMValTool.

    Args:
        target_model: Name of the model
        **kwargs: Model specific recipe settings

    Returns:
        Forcing object, e.g. :obj:`.lisflood.LisfloodForcing`
    """
    constructor = FORCING_CLASSES.get(target_model, default.DefaultForcing)
    return constructor.generate(**kwargs)


def load(directory):
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
    constructor = FORCING_CLASSES.get(target_model, default.DefaultForcing)
    return constructor(**data)


def load_foreign(target_model, **forcing_info):
    """Load existing forcing data generated from an external source.

    Args:
        target_model: Name of the hydrological model for which the forcing will be used
        **kwargs: Model specific configuration settings related to the forcing
            data. For each model you can see the available settings in the corresponding
            Forcing object, e.g. :obj:`.wflow.WflowForcing`.

    Returns:
        Forcing object, e.g. :obj:`.hype.HypeForcing`
    """
    constructor = FORCING_CLASSES.get(target_model, default.DefaultForcing)
    return constructor(**kwargs)


# TODO fix time conventions
# TODO add / fix tests
# TODO make sure model classes understand new forcing data objects
