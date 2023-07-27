from importlib.metadata import entry_points
from logging import getLogger
from os import linesep
from pathlib import Path
from typing import Dict, Optional

from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.config import CFG, SYSTEM_CONFIG, USER_HOME_CONFIG

logger = getLogger(__name__)


def add_to_config(parameter_set: ParameterSet):
    """Add a parameter set to the e:py:data:`ewatercycle.config.CFG` object.

    Args:
        parameter_set: Parameter set to add to the config.
    """
    logger.info(f"Adding parameterset {parameter_set.name} to ewatercycle.CFG... ")

    if not CFG.parameter_sets:
        CFG.parameter_sets = {}

    CFG.parameter_sets[parameter_set.name] = parameter_set


def _abbreviate(path: Path):
    try:
        if CFG.parameterset_dir is None:
            raise ValueError("Can not abbreviate path without CFG.parameterset_dir")
        return path.relative_to(CFG.parameterset_dir)
    except ValueError:
        return path


def available_parameter_sets(
    target_model: Optional[str] = None,
) -> Dict[str, ParameterSet]:
    """List available parameter sets on this machine.

    Args:
        target_model: Filter parameter sets on a model name

    Returns:
        Dictionary available parameter sets on current machine.
    """
    all_parameter_sets = CFG.parameter_sets
    if not all_parameter_sets:
        raise ValueError(
            f"No parameter sets defined in {CFG.ewatercycle_config}. Use "
            "`ewatercycle.parameter_sets.download_example_parameter_sets()` to download"
            " examples or define your own or ask whoever setup the ewatercycle "
            "system to do it."
        )
        # TODO explain somewhere how to add new parameter sets
    filtered = {
        name: ps
        for name, ps in all_parameter_sets.items()
        if (target_model is None or ps.target_model == target_model)
    }
    if not filtered:
        raise ValueError(
            f"No parameter sets defined for {target_model} model in "
            f"{CFG.ewatercycle_config}. Use  "
            "`ewatercycle.parareter_sets.download_example_parameter_sets` to download "
            "examples or define your own or ask whoever setup the ewatercycle "
            "system to do it."
        )
    return filtered


def example_parameter_sets() -> Dict[str, ParameterSet]:
    """Lists the available example parameter sets.

    They can be downloaded with :py:func:`~download_example_parameter_sets`.

    To get your own example parameter set to be listed here it needs to be
    registered in the :py:data:`ewatercycle.parameter_sets`
    `entry point group <https://packaging.python.org/en/latest/specifications/entry-points/>`_.
    """
    # TODO how to add a new model docs should be updated with this part
    return {
        entry_point.name: entry_point.load()
        for entry_point in entry_points(group="ewatercycle.parameter_sets")  # /NOSONAR
    }


def download_example_parameter_sets(skip_existing=True):
    """Downloads all of the example parameter sets and adds them to the config_file.

    Downloads to `parameterset_dir` directory defined in
    :py:data:`ewatercycle.config.CFG`.

    Args:
        skip_existing: When true will not download any parameter set which
            already has a local directory. When false will raise ValueError
            exception when parameter set already exists.
    """
    examples = example_parameter_sets()

    i = 0
    for example in examples.values():
        example.download(CFG.parameterset_dir, force=not skip_existing)
        add_to_config(example)
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
