import logging
from pathlib import Path
from typing import Literal, Optional, Union

from esmvalcore.config import Session
from esmvalcore.experimental import CFG
from pydantic import BaseModel, validator
from ruamel.yaml import YAML

from ewatercycle.util import to_absolute_path

logger = logging.getLogger(__name__)
FORCING_YAML = "ewatercycle_forcing.yaml"


class DefaultForcing(BaseModel):
    """Container for forcing data.

    Args:
        directory: Directory where forcing data files are stored.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
    """

    model: Literal["default"] = "default"
    start_time: str
    end_time: str
    directory: Optional[Path] = None
    shape: Optional[Path] = None

    @validator("directory")
    def _absolute_directory(cls, v: Union[str, Path, None]):
        return to_absolute_path(v) if v is not None else v

    @validator("shape")
    def _absolute_shape(cls, v: Union[str, Path, None], values: dict):
        return (
            to_absolute_path(v, parent=values["directory"], must_be_in_parent=False)
            if v is not None
            else v
        )

    @classmethod
    def generate(
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        directory: Optional[str] = None,
        **model_specific_options,
    ) -> "DefaultForcing":
        """Generate forcing data with ESMValTool."""
        raise NotImplementedError("No default forcing generator available.")

    def save(self):
        """Export forcing data for later use."""
        yaml = YAML()
        target = self.directory / FORCING_YAML
        # We want to make the yaml and its parent movable,
        # so the directory and shape should not be included in the yaml file
        clone = self.copy(exclude={"directory"})

        if clone.shape:
            try:
                clone.shape = str(clone.shape.relative_to(self.directory))
            except ValueError:
                clone.shape = None
                logger.info(
                    f"Shapefile {self.shape} is not in forcing directory "
                    f"{self.directory}. So, it won't be saved in {target}."
                )

        fdict = clone.dict(exclude_none=True)
        with open(target, "w") as f:
            yaml.dump(fdict, f)
        return target

    @classmethod
    def load(cls, directory: str | Path):
        """Load previously generated or imported forcing data.

        Args:
            directory: forcing data directory; must contain
                `ewatercycle_forcing.yaml` file

        Returns: Forcing object
        """
        data_source = to_absolute_path(directory)
        meta = data_source / FORCING_YAML
        yaml = YAML(typ="safe")

        if not meta.exists():
            raise FileNotFoundError(
                f"Forcing file {meta} not found. "
                f"Perhaps you want to use {cls.__name__}(...)?"
            )
        metadata = meta.read_text()
        # Workaround for legacy forcing files having !PythonClass tag.
        #     Get model name of non-initialized BaseModel with Pydantic class property:
        modelname = cls.__fields__["model"].default
        metadata = metadata.replace(f"!{cls.__name__}", f"model: {modelname}")

        fdict = yaml.load(metadata)
        fdict["directory"] = data_source

        return cls(**fdict)

    @classmethod
    def plot(self):
        raise NotImplementedError("No generic plotting method available.")

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def _session(directory: Optional[str] = None) -> Optional[Session]:
    """When directory is set return a ESMValTool session that will write recipe output to that directory."""
    if directory is None:
        return None

    class TimeLessSession(Session):
        def __init__(self, output_dir: Path):
            super().__init__(CFG.copy())
            self.output_dir = output_dir

        @property
        def session_dir(self):
            return self.output_dir

    return TimeLessSession(Path(directory).absolute())


DATASETS = {
    "ERA5": {
        "dataset": "ERA5",
        "project": "OBS6",
        "tier": 3,
        "type": "reanaly",
        "version": 1,
    },
    "ERA-Interim": {
        "dataset": "ERA-Interim",
        "project": "OBS6",
        "tier": 3,
        "type": "reanaly",
        "version": 1,
    },
}
