from ewatercycle import CFG

from typing import Iterable

from ._default import ParameterSet
from ._lisflood import LisfloodParameterSet

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
    # TODO how to get valid target_model string?
    all_parameter_sets = _parse_parametersets()
    return (
        name
        for name, ps in all_parameter_sets.items()
        if ps.is_available and (target_model is None or ps.target_model == target_model)
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
    # TODO download archive matching doi from Zenodo
    # TODO unpack archive in CFG['parameterset_dir'] subdirectory
    # TODO print yaml snippet with target_model and config to add to ewatercycle.yaml
    raise NotImplementedError(
        "Auto download of parameter sets not yet supported"
    )


def download_example_parameter_sets():
    # TODO define array of examples urls per model 
    # TODO use build_from_urls and save_* to download files
    # TODO print yaml snippet
    # ...
    print(
        "Downloaded parameter sets: ..."
        "To use them, add the following snippet to cfg/ewatercycle.yaml"
    )


# from ewatercycle.parametersetdb import build_from_urls

# parameterset = build_from_urls(
#     config_format='ini', config_url='https://raw.githubusercontent.com/UU-Hydro/PCR-GLOBWB_input_example/master/ini_and_batch_files_for_pcrglobwb_course/rhine_meuse_30min_using_input_example/setup_natural_test.ini',
#     datafiles_format='svn', datafiles_url='https://github.com/UU-Hydro/PCR-GLOBWB_input_example/trunk/RhineMeuse30min',
# )
# parameterset.save_datafiles('./pcrglobwb_example_case')
# parameterset.save_config('./pcrglobwb_example_case/setup.ini')

# parameterset = build_from_urls(
#     config_format='ini', config_url='https://github.com/openstreams/wflow/raw/master/examples/wflow_rhine_sbm_nc/wflow_sbm_NC.ini',
#     datafiles_format='svn', datafiles_url='https://github.com/openstreams/wflow/trunk/examples/wflow_rhine_sbm_nc',
# )
# parameterset.save_datafiles('./wflow_example_case_nc')
