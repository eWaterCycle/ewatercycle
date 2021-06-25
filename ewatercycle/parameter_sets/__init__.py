import subprocess
from logging import getLogger
from os import linesep
from pathlib import Path
from typing import Iterable, List
from urllib.request import urlopen

from ewatercycle import CFG
from ._default import ParameterSet
from ._lisflood import LisfloodParameterSet
from ..config import SYSTEM_CONFIG, USER_HOME_CONFIG

logger = getLogger(__name__)

CONSTRUCTORS = {
    "Lisflood": LisfloodParameterSet,  # TODO remove when MaskMap is no longer in parameter set see #121
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
    # TODO add docstring
    all_parameter_sets = _parse_parametersets()
    return (
        name
        for name, ps in all_parameter_sets.items()
        if ps.is_available
        and (target_model is None or ps.target_model == target_model)
    )


def get_parameter_set(name: str):
    # TODO add docstring
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
    raise NotImplementedError(
        "Auto download of parameter sets not yet supported"
    )


class ExampleParameterSet(ParameterSet):
    def __init__(
        self,
        config_url: str,
        datafiles_url: str,
        name,
        directory: str,
        config: str,
        doi="N/A",
        target_model="generic",
    ):
        super().__init__(name, directory, config, doi, target_model)
        self.config_url = config_url
        self.datafiles_url = datafiles_url

    def download(self):
        if self.directory.exists():
            raise ValueError("Directory already exists, will not overwrite")

        logger.info(f"Downloading example parameter set {self.name} to {self.directory}...")

        subprocess.check_call(
            ["svn", "export", self.datafiles_url, self.directory]
        )
        # TODO replace subversion with alternative see https://stackoverflow.com/questions/33066582/how-to-download-a-folder-from-github/48948711
        with urlopen(self.config_url) as response:
            self.config.write_text(response.read().decode())

        logger.info("Download complete.")

    def to_config(self):
        logger.info(f"Adding parameterset {self.name} to ewatercycle.CFG... ")

        if not CFG["parameter_sets"]:
            CFG["parameter_sets"] = {}

        CFG["parameter_sets"][self.name] = dict(
            directory=str(_abbreviate(self.directory)),
            config=str(_abbreviate(self.config)),
            doi=self.doi,
            target_model=self.target_model,
        )


def _abbreviate(path: Path):
    try:
        return path.relative_to(CFG["parameterset_dir"])
    except ValueError:
        return path


def example_parameter_sets() -> List[ExampleParameterSet]:
    # TODO how to add a new model docs should be updated with this part

    return [
        # TODO move to ./_pcrglobwb.py
        ExampleParameterSet(
            # Relative to CFG['parameterset_dir']
            directory="pcrglobwb_example_case",
            name="pcrglobwb_example_case",
            # Relative to CFG['parameterset_dir']
            config="pcrglobwb_example_case/setup_natural_test.ini",
            datafiles_url="https://github.com/UU-Hydro/PCR-GLOBWB_input_example/trunk/RhineMeuse30min",
            # Raw url to config file
            config_url="https://raw.githubusercontent.com/UU-Hydro/PCR-GLOBWB_input_example/master/ini_and_batch_files_for_pcrglobwb_course/rhine_meuse_30min_using_input_example/setup_natural_test.ini",
            doi="N/A",
            target_model="pcrglobwb",
        ),
        # TODO move to ./_wflow.py
        ExampleParameterSet(
            # Relative to CFG['parameterset_dir']
            directory="wflow_rhine_sbm_nc",
            name="wflow_rhine_sbm_nc",
            # Relative to CFG['parameterset_dir']
            config="wflow_rhine_sbm_nc/wflow_sbm_NC.ini",
            datafiles_url="https://github.com/openstreams/wflow/trunk/examples/wflow_rhine_sbm_nc",
            # Raw url to config file
            config_url="https://github.com/openstreams/wflow/raw/master/examples/wflow_rhine_sbm_nc/wflow_sbm_NC.ini",
            doi="N/A",
            target_model="wflow",
        ),
        # TODO move to ./_lisflood.py
        ExampleParameterSet(
            # Relative to CFG['parameterset_dir']
            directory="lisflood_fraser",
            name="lisflood_fraser",
            # Relative to CFG['parameterset_dir']
            config="lisflood_fraser/settings_lat_lon-Run.xml",
            datafiles_url="https://github.com/ec-jrc/lisflood-usecases/trunk/LF_lat_lon_UseCase",
            # Raw url to config file
            config_url="https://github.com/ec-jrc/lisflood-usecases/raw/master/LF_lat_lon_UseCase/settings_lat_lon-Run.xml",
            doi="N/A",
            target_model="lisflood",
        ),
    ]


def download_example_parameter_sets():
    """Downloads a couple of example parameter sets and adds them to the config_file."""
    examples = example_parameter_sets()

    for example in examples:
        example.download()
        example.to_config()

    logger.info(
        f"{len(examples)} example parameter sets were downloaded"
    )

    try:
        config_file = CFG.save_to_file()
        logger.info(
            f"Saved parameter sets to configuration file {config_file}"
        )
    except OSError as e:
        raise OSError(
            f'Failed to write parameter sets to configuration file. '
            f'Manually save content below to {USER_HOME_CONFIG} '
            f'or {SYSTEM_CONFIG} file: {linesep}'
            f'{CFG.dump_to_yaml()}'
        ) from e
