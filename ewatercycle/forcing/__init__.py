import re
from pathlib import Path
from typing import Optional, Dict

from ruamel.yaml import YAML

from . import default, hype, lisflood, marrmot, pcrglobwb, wflow
from .datasets import DATASETS
from .default import DefaultForcing, FORCING_YAML

FORCING_CLASSES = {  # not sure how to annotate this
    "hype": hype.HypeForcing,
    "lisflood": lisflood.LisfloodForcing,
    "marrmot": marrmot.MarrmotForcing,
    "pcrglobwb": pcrglobwb.PCRGlobWBForcing,
    "wflow": wflow.WflowForcing,
}


def generate(target_model: str,
             dataset: str,
             start_time: str,
             end_time: str,
             shape: str,
             model_specific_options: Optional[Dict] = None) -> DefaultForcing:
    """Generate forcing data with ESMValTool.

    Args:
        target_model: Name of the model
        dataset: Name of the source dataset. See :py:data:`.DATASETS`.
        start_time: Start time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
        **model_specific_options: Model specific recipe settings. See `https://ewatercycle.readtherdocs.io/forcing_generate_options`_.

    Returns:
        Forcing object, e.g. :obj:`.lisflood.LisfloodForcing`
    """
    constructor = FORCING_CLASSES.get(target_model, None)
    if constructor is None:
        raise NotImplementedError(f'Target model `{target_model}` is not supported by the eWatercycle forcing generator')
    if model_specific_options is None:
        model_specific_options = {}
    forcing_info = constructor.generate(dataset, start_time, end_time, shape, **model_specific_options)
    forcing_info.save()
    return forcing_info


def load(directory):
    """Load previously generated or imported forcing data.

    Args:
        directory: forcing data directory; must contain `ewatercycle_forcing.yaml`

    Returns:
        Forcing object, e.g. :obj:`.marrmot.MarrmotForcing`
    """
    yaml = YAML()
    source = Path(directory) / FORCING_YAML
    # TODO give nicer error
    yaml.register_class(DefaultForcing)
    for forcing_cls in FORCING_CLASSES.values():
        yaml.register_class(forcing_cls)
    content = source.read_text()
    # Set directory in yaml string to parent of yaml file
    # Because in DefaultForcing.save the directory was removed
    abs_dir = str(source.parent.expanduser().resolve())
    content += f'directory: {abs_dir}\n'
    forcing_info = yaml.load(content)
    return forcing_info


# Or load_custom , load_external, load_???., from_external, import_forcing,
def load_foreign(target_model,
                 start_time: str,
                 end_time: str,
                 directory: str = '.',
                 shape: str = None,
                 forcing_info: Optional[Dict] = None) -> DefaultForcing:
    """Load existing forcing data generated from an external source.

    Args:
        target_model: Name of the hydrological model for which the forcing will be used
        start_time: Start time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
        directory: forcing data directory
        shape: Path to a shape file. Used for spatial selection.
        forcing_info: Model specific information about forcing
            data. For each model you can see the available information fields
            at `https://ewatercycle.readtherdocs.io/forcing_load_info`_.

    Returns:
        Forcing object, e.g. :obj:`.hype.HypeForcing`

    Examples:

        For Marrmot

        .. code-block:: python

          from ewatercycle.forcing import load_foreign

          forcing = load_foreign('marmot',
                                 directory='/data/marrmot-forcings-case1',
                                 start_time='1989-01-02T00:00:00Z',
                                 end_time='1999-01-02T00:00:00Z',
                                 forcing_info={
                                     'forcing_file': 'marrmot-1989-1999.mat'
                                 })

        For LisFlood

        .. code-block:: python

          from ewatercycle.forcing import load_foreign

          forcing = load_foreign(target_model='lisflood',
                                 directory='/data/lisflood-forcings-case1',
                                 start_time='1989-01-02T00:00:00Z',
                                 end_time='1999-01-02T00:00:00Z',
                                 forcing_info={
                                     'PrefixPrecipitation': 'tp.nc',
                                     'PrefixTavg': 'ta.nc',
                                     'PrefixE0': 'e.nc',
                                     'PrefixES0': 'es.nc',
                                     'PrefixET0': 'et.nc'
                                 })
    """
    constructor = FORCING_CLASSES.get(target_model, None)
    if constructor is None:
        raise NotImplementedError(
            f'Target model `{target_model}` is not supported by the eWatercycle forcing generator')
    return constructor(start_time, end_time, directory, shape, **forcing_info)


# TODO fix time conventions
# TODO add / fix tests
# TODO make sure model classes understand new forcing data objects
