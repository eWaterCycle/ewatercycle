from pathlib import Path
from typing import Optional, Dict, Type

from ruamel.yaml import YAML

from ._default import DefaultForcing, FORCING_YAML
from . import _hype, _lisflood, _marrmot, _pcrglobwb, _wflow

from ewatercycle.util import to_absolute_path

FORCING_CLASSES: Dict[str, Type[DefaultForcing]] = {
    "hype": _hype.HypeForcing,
    "lisflood": _lisflood.LisfloodForcing,
    "marrmot": _marrmot.MarrmotForcing,
    "pcrglobwb": _pcrglobwb.PCRGlobWBForcing,
    "wflow": _wflow.WflowForcing,
}


def load(directory: str) -> DefaultForcing:
    """Load previously generated or imported forcing data.

    Args:
        directory: forcing data directory; must contain
            `ewatercycle_forcing.yaml` file

    Returns: Forcing object
    """
    yaml = YAML()
    source = to_absolute_path(directory)
    # TODO give nicer error
    yaml.register_class(DefaultForcing)
    for forcing_cls in FORCING_CLASSES.values():
        yaml.register_class(forcing_cls)
    # Set directory in yaml string to parent of yaml file
    # Because in DefaultForcing.save the directory was removed
    forcing_info = yaml.load(source / FORCING_YAML)
    forcing_info.directory = source
    if forcing_info.shape:
        forcing_info.shape = to_absolute_path(forcing_info.shape, parent = source)

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
        target_model: Name of the hydrological model for which the forcing will
            be used
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        directory: forcing data directory
        shape: Path to a shape file. Used for spatial selection.
        forcing_info: Dictionary with model-specific information about forcing
            data. See below for the available options for each model.

    Returns:
        Forcing object

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

    Model-specific forcing info:
    """
    constructor = FORCING_CLASSES.get(target_model, None)
    if constructor is None:
        raise NotImplementedError(
            f'Target model `{target_model}` is not supported by the '
            'eWatercycle forcing generator.')
    if forcing_info is None:
        forcing_info = {}
    return constructor(  # type: ignore # each subclass can have different forcing_info
        start_time=start_time,
        end_time=end_time,
        directory=directory,
        shape=shape,
        **forcing_info,
    )


def generate(target_model: str,
             dataset: str,
             start_time: str,
             end_time: str,
             shape: str,
             model_specific_options: Optional[Dict] = None) -> DefaultForcing:
    """Generate forcing data with ESMValTool.

    Args:
        target_model: Name of the model
        dataset: Name of the source dataset. See :py:mod:`~.datasets`.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
        model_specific_options: Dictionary with model-specific recipe settings.
            See below for the available options for each model.

    Returns:
        Forcing object


    Model-specific options that can be passed to `generate`:
    """
    constructor = FORCING_CLASSES.get(target_model, None)
    if constructor is None:
        raise NotImplementedError(
            f'Target model `{target_model}` is not supported by the '
            'eWatercycle forcing generator')
    if model_specific_options is None:
        model_specific_options = {}
    forcing_info = constructor.generate(dataset, start_time, end_time, shape,
                                        **model_specific_options)
    forcing_info.save()
    return forcing_info


# Append docstrings of with model-specific options to existing docstring
load_foreign.__doc__ += "".join(  # type:ignore
    [f"\n    {k}: {v.__init__.__doc__}" for k, v in FORCING_CLASSES.items()])

generate.__doc__ += "".join(  # type:ignore
    [f"\n    {k}: {v.generate.__doc__}" for k, v in FORCING_CLASSES.items()])
