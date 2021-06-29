from typing import Iterable

from ._example import ExampleParameterSet


def example_parameter_sets() -> Iterable[ExampleParameterSet]:
    return [
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
            supported_model_versions={"2020.1.1"}
        )
    ]
