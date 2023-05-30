from esmvalcore.experimental import CFG
from esmvalcore.experimental.config import Session
from ewatercycle.util import to_absolute_path

import logging
from pydantic import BaseModel, validator
from ruamel.yaml import YAML


from pathlib import Path
from typing import Literal, Optional, Union


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