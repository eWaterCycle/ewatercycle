from itertools import chain
from logging import getLogger
from os import linesep
from typing import Iterable

from ewatercycle import CFG
from . import _pcrglobwb, _lisflood, _wflow
from .default import ParameterSet
from ._example import ExampleParameterSet
from ..config import SYSTEM_CONFIG, USER_HOME_CONFIG

logger = getLogger(__name__)

CONSTRUCTORS = {
    "Lisflood": _lisflood.LisfloodParameterSet,  # TODO remove when MaskMap is no longer in parameter set see #121
}


def _parse_parametersets():
    parametersets = {}
    for name, options in CFG["parameter_sets"].items():
        model = options["target_model"]
        constructor = CONSTRUCTORS.get(model, ParameterSet)

        parameterset = constructor(name=name, **options)
        parametersets[name] = parameterset

    return parametersets


def available_parameter_sets(target_model: str = None) -> Iterable[str]:
    """List available parameter sets on this machine.

    Args:
        target_model: Filter parameter sets on a model name

    Returns: Names of available parameter sets on current machine.

    """
    all_parameter_sets = _parse_parametersets()
    return (
        name
        for name, ps in all_parameter_sets.items()
        if ps.is_available and (target_model is None or ps.target_model == target_model)
    )


def get_parameter_set(name: str) -> ParameterSet:
    """Get parameter set object available on this machine so it can be used in a model.

    Args:
        name: Name of parameter set

    Returns: Parameter set object that can be used in an ewatercycle model constructor.

    """
    all_parameter_sets = _parse_parametersets()

    ps = all_parameter_sets.get(name)
    if ps is None:
        raise KeyError(f"No parameter set available with name {name}")

    if not ps.is_available:
        raise ValueError(f"Cannot find parameter set with attributes {ps}")

    return ps


def download_parameter_sets(zenodo_doi: str, target_model: str, config: str):
    # TODO add docstring
    # TODO download archive matching doi from Zenodo
    # TODO unpack archive in CFG['parameterset_dir'] subdirectory
    # TODO print yaml snippet with target_model and config to add to ewatercycle.yaml
    raise NotImplementedError("Auto download of parameter sets not yet supported")


def example_parameter_sets() -> Iterable[ExampleParameterSet]:
    """Lists example parameter sets that can be downloaded with :py:func:`~download_example_parameter_sets`.
    """
    # TODO how to add a new model docs should be updated with this part
    return chain(
        _wflow.example_parameter_sets(),
        _pcrglobwb.example_parameter_sets(),
        _lisflood.example_parameter_sets(),
    )


def download_example_parameter_sets():
    """Downloads all of the example parameter sets and adds them to the config_file.

    Downloads to `parameterset_dir` directory defined in :py:data:`ewatercycle.config.CFG`.
    """
    examples = example_parameter_sets()

    i = 0
    for example in examples:
        example.download()
        example.to_config()
        i += 1

    logger.info(f"{i} example parameter sets were downloaded")

    try:
        config_file = CFG.save_to_file()
        logger.info(f"Saved parameter sets to configuration file {config_file}")
    except OSError as e:
        raise OSError(
            f"Failed to write parameter sets to configuration file. "
            f"Manually save content below to {USER_HOME_CONFIG} "
            f"or {SYSTEM_CONFIG} file: {linesep}"
            f"{CFG.dump_to_yaml()}"
        ) from e
