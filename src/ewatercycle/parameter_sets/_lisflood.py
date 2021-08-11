from typing import Iterable

from ._example import ExampleParameterSet


def example_parameter_sets() -> Iterable[ExampleParameterSet]:
    return [
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
            supported_model_versions={"20.10"}
        )
    ]
