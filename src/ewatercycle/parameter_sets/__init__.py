from itertools import chain
from logging import getLogger
from os import linesep
from typing import Dict, Tuple

from ewatercycle import CFG
from . import _pcrglobwb, _lisflood, _wflow
from ._example import ExampleParameterSet
from .default import ParameterSet
from ..config import DEFAULT_CONFIG, SYSTEM_CONFIG, USER_HOME_CONFIG

logger = getLogger(__name__)


def _parse_parametersets():
    parametersets = {}
    if CFG["parameter_sets"] is None:
        return []
    for name, options in CFG["parameter_sets"].items():
        parameterset = ParameterSet(name=name, **options)
        parametersets[name] = parameterset

    return parametersets


def available_parameter_sets(target_model: str = None) -> Tuple[str, ...]:
    """List available parameter sets on this machine.

    Args:
        target_model: Filter parameter sets on a model name

    Returns: Names of available parameter sets on current machine.

    """
    all_parameter_sets = _parse_parametersets()
    if not all_parameter_sets:
        if CFG['ewatercycle_config'] == DEFAULT_CONFIG:
            raise ValueError(f'No configuration file found.')
        raise ValueError(f'No parameter sets defined in {CFG["ewatercycle_config"]}. '
                         f'Use `ewatercycle.parareter_sets.download_example_parameter_sets` to download examples '
                         f'or define your own or ask whoever setup the ewatercycle system to do it.')
        # TODO explain somewhere how to add new parameter sets
    filtered = tuple(
        name
        for name, ps in all_parameter_sets.items()
        if ps.is_available and (target_model is None or ps.target_model == target_model)
    )
    if not filtered:
        raise ValueError(f'No parameter sets defined for {target_model} model in {CFG["ewatercycle_config"]}. '
                         f'Use `ewatercycle.parareter_sets.download_example_parameter_sets` to download examples '
                         f'or define your own or ask whoever setup the ewatercycle system to do it.')
    return filtered


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


def example_parameter_sets() -> Dict[str, ExampleParameterSet]:
    """Lists example parameter sets that can be downloaded with :py:func:`~download_example_parameter_sets`.
    """
    # TODO how to add a new model docs should be updated with this part
    examples = chain(
        _wflow.example_parameter_sets(),
        _pcrglobwb.example_parameter_sets(),
        _lisflood.example_parameter_sets(),
    )
    return {e.name: e for e in examples}


def download_example_parameter_sets(skip_existing=True):
    """Downloads all of the example parameter sets and adds them to the config_file.

    Downloads to `parameterset_dir` directory defined in :py:data:`ewatercycle.config.CFG`.

    Args:
        skip_existing: When true will not download any parameter set which already has a local directory.
            When false will raise ValueError exception when parameter set already exists.

    """
    examples = example_parameter_sets()

    i = 0
    for example in examples.values():
        example.download(skip_existing)
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
