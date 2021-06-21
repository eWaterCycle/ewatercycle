from pathlib import Path

from ewatercycle import CFG


class ParameterSet:
    """Container object for parameter set options."""

    def __init__(
        self,
        name,
        directory: str,
        config: str,
        doi="N/A",
        target_model="generic",
    ):
        self.name = name
        self.directory = make_absolute(directory)
        self.config = make_absolute(config)
        self.doi = doi
        self.target_model = target_model

    def __repr__(self):
        attrs = self.__dict__.copy()
        model = attrs.pop("target_model").capitalize()
        options = ", ".join([f"{k}={v!r}" for k, v in attrs.items()])
        return f"{model}ParameterSet({options})"

    def __str__(self):
        """Nice formatting of parameter set."""
        attrs = self.__dict__.copy()
        model = attrs.pop("target_model").capitalize()
        return "\n".join(
            [
                f"{model} parameterset",
                "--------------------------",
            ]
            + [f"{k}={v!r}" for k, v in attrs.items()]
        )

    @property
    def is_available(self):
        return self.directory.exists() and self.config.exists()


def make_absolute(input_path: str) -> Path:
    pathlike = Path(input_path)
    return (
        pathlike
        if pathlike.is_absolute()
        else CFG["parameterset_dir"] / pathlike
    )
