from pathlib import Path
from typing import Optional, Iterable

from ._example import ExampleParameterSet
from .default import ParameterSet, _make_absolute


class LisfloodParameterSet(ParameterSet):
    def __init__(
        self,
        name,
        directory: str,
        config: str,
        doi="N/A",
        target_model="Lisflood",
        MaskMap: Optional[str] = None,
    ):
        super().__init__(
            name,
            directory,
            config,
            doi=doi,
            target_model=target_model,
        )
        self.MaskMap: Optional[Path] = _make_absolute(MaskMap) if MaskMap is not None else None

    @property
    def is_available(self):
        return super().is_available and (self.MaskMap is None or self.MaskMap.exists())


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
        )
    ]
