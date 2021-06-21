from ewatercycle import CFG

from typing import Iterable

from ._default import ParameterSet
from ._lisflood import LisfloodParameterSet

CONSTRUCTORS = {
    "Lisflood": LisfloodParameterSet,
}


def _parse_parametersets():

    parametersets = {}
    for name, options in CFG["parameter_sets"].items():
        model = options["target_model"]
        constructor = CONSTRUCTORS.get(model, ParameterSet)

        parameterset = constructor(name=name, **options)
        parametersets[name] = parameterset

    return parametersets


def available_parameter_sets(target_model: str) -> Iterable[str]:
    # TODO how to get valid target_model string?
    all_parameter_sets = _parse_parametersets()
    return (
        name
        for name, ps in all_parameter_sets.items()
        if ps.is_available and ps.target_model == target_model
    )


def get_parameter_set(name: str):

    all_parameter_sets = _parse_parametersets()

    ps = all_parameter_sets.get(name)
    if ps is None:
        raise KeyError(f"No parameter set available with name {name}")

    if not ps.is_available:
        raise ValueError(f"Cannot find parameter set with attributes {ps}")

    return ps


def download_parameter_sets():
    raise NotImplementedError(
        "Auto download of parameter sets not yet supported"
    )


def download_example_parameter_sets():
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
