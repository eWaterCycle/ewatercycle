from typing import Optional

from ._default import ParameterSet, make_absolute


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
        self.MaskMap = make_absolute(MaskMap) if MaskMap is not None else None

    @property
    def is_available(self):
        return super().is_available and self.MaskMap.exists()
