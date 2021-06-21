from typing import Optional

from ._default import ParameterSet


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
            doi="N/A",
            target_model="generic",
        )
        self.MaskMap = MaskMap

    @property
    def is_available(self):
        return super().is_available and self.MaskMap.exists()
