from pathlib import Path
from typing import Set, Optional

from ewatercycle import CFG
from ewatercycle.util import to_absolute_path


class ParameterSet:
    """Container object for parameter set options.

    Attributes:
        name (str): Name of parameter set
        directory (Path): Location on disk where files of parameter set are stored.
            If Path is relative then relative to CFG['parameterset_dir'].
        config (Path): Model configuration file which uses files from :py:attr:`~directory`.
            If Path is relative then relative to CFG['parameterset_dir'].
        doi (str): Persistent identifier of parameter set. For a example a DOI for a Zenodo record.
        target_model (str): Name of model that parameter set can work with
        supported_model_versions (Set[str]): Set of model versions that are supported by this parameter set.
            If not set then parameter set will be supported by all versions of model
    """

    def __init__(
        self,
        name: str,
        directory: str,
        config: str,
        doi="N/A",
        target_model="generic",
        supported_model_versions: Optional[Set[str]] = None,
    ):
        self.name = name
        self.directory = to_absolute_path(directory, parent = CFG.get("parameterset_dir"), must_be_in_parent=False)
        self.config = to_absolute_path(config, parent = CFG.get("parameterset_dir"), must_be_in_parent=False)
        self.doi = doi
        self.target_model = target_model
        self.supported_model_versions = set() if supported_model_versions is None else supported_model_versions

    def __repr__(self):
        options = ", ".join(f"{k}={v!s}" for k, v in self.__dict__.items())
        return f"ParameterSet({options})"

    def __str__(self):
        """Nice formatting of parameter set."""
        return "\n".join(
            [
                "Parameter set",
                "-------------",
            ]
            + [f"{k}={v!s}" for k, v in self.__dict__.items()]
        )

    @property
    def is_available(self) -> bool:
        """Tests if directory and config file is available on this machine"""
        return self.directory.exists() and self.config.exists()

