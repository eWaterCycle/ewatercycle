from pathlib import Path

from ewatercycle import CFG


class ParameterSet:
    """Container object for parameter set options.

    Attributes:
        name (str): Name of parameter set
        directory (Path): Location on disk where files of parameter set are stored
        config (Path): Model configuration file which uses files from :py:attr:`~directory`
        doi (str): Persistent identifier of parameter set. For a example a DOI for a Zenodo record.
        target_model (str): Name of model that parameter set can work with
    """

    def __init__(
        self,
        name: str,
        directory: str,
        config: str,
        doi="N/A",
        target_model="generic",
    ):
        self.name = name
        self.directory = _make_absolute(directory)
        self.config = _make_absolute(config)
        self.doi = doi
        self.target_model = target_model
        # TODO add supported_model_versions attribute

    def __repr__(self):
        options = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"ParameterSet({options})"

    def __str__(self):
        """Nice formatting of parameter set."""
        return "\n".join(
            [
                "Parameter set",
                "-------------",
            ]
            + [f"{k}={v!r}" for k, v in self.__dict__.items()]
        )

    @property
    def is_available(self) -> bool:
        """Tests if directory and config file is available on this machine"""
        return self.directory.exists() and self.config.exists()


def _make_absolute(input_path: str) -> Path:
    pathlike = Path(input_path)
    return pathlike if pathlike.is_absolute() else CFG["parameterset_dir"] / pathlike
