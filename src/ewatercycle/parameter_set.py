from pathlib import Path
from typing import Set

from pydantic import BaseModel

from ewatercycle.util import to_absolute_path


class ParameterSet(BaseModel):
    """Container object for parameter set options."""

    name: str = ""
    """Name of parameter set"""
    directory: Path
    """Location on disk where files of parameter set are stored.
    If Path is relative then relative to CFG.parameterset_dir."""
    config: Path
    """Model configuration file which uses files from
    :py:attr:`~directory`. If Path is relative then relative to
    CFG.parameterset_dir."""
    doi: str = "N/A"
    """Persistent identifier of parameter set. For a example a DOI
    for a Zenodo record."""
    target_model: str = "generic"
    """Name of model that parameter set can work with."""
    supported_model_versions: Set[str] = set()
    """Set of model versions that are
    supported by this parameter set. If not set then parameter set will be
    supported by all versions of model"""

    def __str__(self):
        """Nice formatting of parameter set."""
        return "\n".join(
            [
                "Parameter set",
                "-------------",
            ]
            + [f"{k}={v!s}" for k, v in self.__dict__.items()]
        )

    def make_absolute(self, parameterset_dir: Path):
        if not self.directory.is_absolute():
            self.directory = to_absolute_path(
                self.directory, parameterset_dir, must_be_in_parent=False
            )
        if not self.config.is_absolute():
            self.config = to_absolute_path(
                self.config, parameterset_dir, must_be_in_parent=False
            )
        return self
