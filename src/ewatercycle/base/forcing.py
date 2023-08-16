from datetime import datetime
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Literal, Optional, Union

from esmvalcore.config import Session
from esmvalcore.experimental import CFG, Recipe
from esmvalcore.experimental.recipe_output import RecipeOutput
from pydantic import BaseModel, field_validator
from pydantic.functional_validators import AfterValidator
from ruamel.yaml import YAML

from ewatercycle.util import to_absolute_path

from ewatercycle.base.esmvaltool_wrapper import Dataset, Recipe

logger = logging.getLogger(__name__)
FORCING_YAML = "ewatercycle_forcing.yaml"


def _to_absolute_path(v: Union[str, Path]):
    """Wraps to_absolute_path to a single-arg function, to use as Pydantic validator."""
    return to_absolute_path(v)


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
    directory: Optional[Annotated[Path, AfterValidator(_to_absolute_path)]] = None
    shape: Optional[Path] = None

    @field_validator("shape")
    @classmethod
    def _absolute_shape(cls, v, info):
        if v is None:
            return v
        return to_absolute_path(
            v, parent=info.data["directory"], must_be_in_parent=False
        )

    @classmethod
    def generate(
        cls,
        dataset: str | Dataset,
        start_time: str,
        end_time: str,
        shape: str,
        directory: Optional[str] = None,
        **model_specific_options,
    ) -> "DefaultForcing":
        """Generate forcings for a model.

        The forcing is generated with help of
        `ESMValTool <https://esmvaltool.org/>`_.

        Args:
            dataset: Name of the source dataset. See :py:const:`~ewatercycle.base.forcing.DATASETS`.
            start_time: Start time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: nd time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            shape: Path to a shape file. Used for spatial selection.
            directory:  Directory in which forcing should be written.
                If not given will create timestamped directory.
        """
        # TODO make data set build function
        recipe = cls._build_recipe(
            dataset=dataset,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            **model_specific_options,
        )
        return cls._run_recipe(recipe, directory=directory)


    @classmethod
    def _build_recipe(cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str = Dataset("ERA5", project="OBS6", tier=3, type="reanaly", version=1),
        **model_specific_options,):
        yaml = YAML(typ="safe")
        fn = Path(__file__).parent / "recipe_generic_distributed.yml"
        data = yaml.load(fn)

        if isinstance(dataset, str):
            dataset = Dataset(**DATASETS[dataset])
        data['datasets'] = [dataset]

        for preprocessor in data["preprocessors"].values():
            if 'extract_shape' in preprocessor:
                preprocessor["extract_shape"]["shapefile"] = str(shape)

        variables = data["diagnostics"]["diagnostic"]["variables"]
        for variable in variables.values():
            variable['start_year'] = start_time.year
            variable['end_year'] = end_time.year
        return Recipe(**data)

    
    @classmethod
    def _run_recipe(cls, recipe: Recipe, directory: Optional[str] = None,):
        # TODO see 
        # https://github.com/eWaterCycle/ewatercycle/blob/8f1caf11a13c4761c07b7aa4fb9310865d999d41/src/ewatercycle/base/forcing.py#L155
        # in https://github.com/eWaterCycle/ewatercycle/pull/362
        # or use CLI with `esmvaltool run <written recipe>`, will need to find output files ourselves
        return run_esmvaltool_recipe(recipe, directory=directory)

    def save(self):
        """Export forcing data for later use."""
        yaml = YAML()
        if self.directory is None:
            raise ValueError("Cannot save forcing without directory.")
        target = self.directory / FORCING_YAML
        # We want to make the yaml and its parent movable,
        # so the directory and shape should not be included in the yaml file
        clone = self.model_copy()

        # TODO: directory should not be optional, can we remove the directory
        # from the fdict instead?
        if clone.shape:
            try:
                clone.shape = clone.shape.relative_to(self.directory)
            except ValueError:
                clone.shape = None
                logger.info(
                    f"Shapefile {self.shape} is not in forcing directory "
                    f"{self.directory}. So, it won't be saved in {target}."
                )

        fdict = clone.model_dump(exclude={"directory"}, exclude_none=True, mode="json")
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
        modelname = cls.model_fields["model"].default  # type: ignore
        metadata = metadata.replace(f"!{cls.__name__}", f"model: {modelname}")

        fdict = yaml.load(metadata)
        fdict["directory"] = data_source

        return cls(**fdict)

    @classmethod
    def plot(cls):
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


def run_esmvaltool_recipe(recipe: Recipe, output_dir: str | None) -> RecipeOutput:
    """Run an ESMValTool recipe.

    The recipe.data dictionary can be modified before running the recipe.

    During run the recipe.path is overwritten with a temporary file containing the updated recipe.

    Args:
        recipe: ESMValTool recipe
        output_dir: Directory where output should be written to.
            If None then output is written to generated timestamped directory.

    Returns:
        ESMValTool recipe output

    Example:

        >>> from ewatercycle.forcing import run_esmvaltool_recipe
        >>> from esmvalcore.experimental.recipe import get_recipe
        >>> recipe = get_recipe('hydrology/recipe_wflow.yml')
        >>> recipe.data['scripts']['script']['dem_file'] = 'my_dem.nc'
        >>> output_dir = Path('./output_dir')
        >>> output = run_esmvaltool_recipe(recipe, output_dir)
    """
    # ESMVALCore 2.8.1 always runs original recipe,
    # write updated recipe to disk and use
    recipe.path = _write_recipe(recipe)
    # TODO write recipe in output_dir?
    # TODO fix in esmvalcore and wait for new version?

    session = _session(output_dir)
    output = recipe.run(session=session)

    # remove updated recipe file
    recipe.path.unlink()

    return output


def _write_recipe(recipe: Recipe) -> Path:
    updated_recipe_file = NamedTemporaryFile(
        suffix=recipe.path.name, mode="w", delete=False
    )
    yaml = YAML(typ="safe")
    yaml.dump(recipe.data, updated_recipe_file)
    updated_recipe_file.close()
    return Path(updated_recipe_file.name)


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
"""Dictionary of allowed forcing datasets.

Where key is the name of the dataset and
value is an `ESMValTool dataset section <https://docs.esmvaltool.org/projects/ESMValCore/en/latest/recipe/overview.html#datasets>`_.
"""

