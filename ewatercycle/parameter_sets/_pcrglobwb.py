from typing import Iterable

from ._example import ExampleParameterSet


def example_parameter_sets() -> Iterable[ExampleParameterSet]:
    return [
        ExampleParameterSet(
            # Relative to CFG['parameterset_dir']
            directory="pcrglobwb_rhinemeuse_30min",
            name="pcrglobwb_rhinemeuse_30min",
            # Relative to CFG['parameterset_dir']
            config="pcrglobwb_rhinemeuse_30min/setup_natural_test.ini",
            datafiles_url="https://github.com/UU-Hydro/PCR-GLOBWB_input_example/trunk/RhineMeuse30min",
            # Raw url to config file
            config_url="https://raw.githubusercontent.com/UU-Hydro/PCR-GLOBWB_input_example/master/ini_and_batch_files_for_pcrglobwb_course/rhine_meuse_30min_using_input_example/setup_natural_test.ini",
            doi="https://doi.org/10.5281/zenodo.1045339",
            target_model="pcrglobwb",
            supported_model_versions={"setters"}
        )
    ]
