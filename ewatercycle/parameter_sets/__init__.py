import subprocess
from logging import getLogger
from pathlib import Path
from urllib.request import urlopen

from ruamel.yaml import YAML

from ewatercycle import CFG

from typing import Iterable, Union, List

from ._default import ParameterSet
from ._lisflood import LisfloodParameterSet

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
        subprocess.check_call(
            ["svn", "export", self.datafiles_url, self.directory]
        )
        # TODO replace subversion with alternative see https://stackoverflow.com/questions/33066582/how-to-download-a-folder-from-github/48948711
        with urlopen(self.config_url) as response:
            self.config.write_text(response.read().decode())

    def to_config(self):
        return dict(
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


def _parse_example_parameter_sets() -> List[ExampleParameterSet]:
    # TODO how to add a new model docs should be updated with this part
    return [
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


def download_example_parameter_sets(config_file: Union[str, Path]):
    """Downloads a couple of example parameter sets and adds them to the config_file

    Args:
        config_file: Config file for ewatercycle.
            For example `/etc/ewatercycle.yaml` or `~/.config/.ewatercycle/ewatercycle.yaml`

    """
    logger.info("Downloaded parameter sets: ...")
    examples = _parse_example_parameter_sets()

    if not CFG["parameter_sets"]:
        CFG["parameter_sets"] = {}

    for example in examples:
        example.download()
        CFG["parameter_sets"][example.name] = example.to_config()


    cp = CFG.copy()
    cp["esmvaltool_config"] = str(cp["esmvaltool_config"])
    cp["grdc_location"] = str(cp["grdc_location"])
    cp["singularity_dir"] = str(cp["singularity_dir"])
    cp["output_dir"] = str(cp["output_dir"])
    cp["parameterset_dir"] = str(cp["parameterset_dir"])
    old_config_file = cp.pop("ewatercycle_config")

    yaml = YAML()
    with open(config_file, "w") as f:
        yaml.dump(cp, f)

    logger.info(
        f"{len(examples)} example parameter sets were downloaded and added to {config_file}"
    )
