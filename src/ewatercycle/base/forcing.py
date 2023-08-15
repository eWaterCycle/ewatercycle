import logging
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Literal, Optional, Union

from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_output import RecipeOutput
from pydantic import BaseModel, field_validator
from pydantic.functional_validators import AfterValidator
from ruamel.yaml import YAML

from ewatercycle.base.esmvaltool_wrapper import Dataset
from ewatercycle.base.esmvaltool_wrapper import Recipe as WrappedRecipe
from ewatercycle.base.forcing_recipe import (
    _session,
    build_generic_distributed_forcing_recipe,
    run_recipe,
)
from ewatercycle.util import data_files_from_recipe_output, get_time, to_absolute_path

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
            dataset: Name of the source dataset. See :py:const:`~ewatercycle.base.forcing_recipe.DATASETS`.
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
            start_time=get_time(start_time),
            end_time=get_time(end_time),
            shape=shape,
            **model_specific_options,
        )
        recipe_output = cls._run_recipe(recipe, directory=directory)
        return cls._from_recipe_output(start_time, end_time, shape, recipe_output)

    @classmethod
    def _from_recipe_output(cls, start_time, end_time, shape, recipe_output):
        forcing_args = {"start_time": start_time, "end_time": end_time, "shape": shape}
        forcing_args.update(_parse_recipe_output(recipe_output))
        forcing = cls(**forcing_args)
        forcing.save()
        return forcing

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str = "ERA5",
        **model_specific_options,
    ):
        # TODO move to GenericDistributedForcing, but what should be here then?
        return build_generic_distributed_forcing_recipe(
            start_year=start_time.year,
            end_year=end_time.year,
            shape=shape,
            dataset=dataset,
        )

    @classmethod
    def _run_recipe(
        cls,
        recipe: WrappedRecipe,
        directory: Optional[str] = None,
    ) -> RecipeOutput:
        return run_recipe(recipe, directory)

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


class GenericDistributedForcing(DefaultForcing):
    """Generic forcing data for a distributed model.

    Attributes:
        pr: Path to NetCDF file with precipitation data.
        tas: Path to NetCDF file with air temperature data.
        tasmin: Path to NetCDF file with minimum air temperature data.
        tasmax: Path to NetCDF file with maximum air temperature data.

    Example:

        To generate forcing from ERA5 for the Rhine catchment for 2000-2001:

        ```pycon
        from pathlib import Path
        from rich import print
        from ewatercycle.base.forcing import GenericDistributedForcing

        shape = Path("./src/ewatercycle/testing/data/Rhine/Rhine.shp")
        forcing = GenericDistributedForcing.generate(
            dataset='ERA5',
            start_time='2000-01-01T00:00:00Z',
            end_time='2001-01-01T00:00:00Z',
            shape=shape.absolute(),
        )
        print(forcing)
        ```

        Gives something like:

        ```pycon
        GenericDistributedForcing(
            model='generic_distributed',
            start_time='2000-01-01T00:00:00Z',
            end_time='2001-01-01T00:00:00Z',
            directory=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/esmvaltool_output/tmp05upitxoewcrep_20230815_154640/work/diagnostic/script'),
            shape=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/src/ewatercycle/testing/data/Rhine/Rhine.shp'),
            pr='OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc',
            tas='OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc',
            tasmin='OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc',
            tasmax='OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc'
        )
        ```
    """

    model: Literal["generic_distributed"] = "generic_distributed"
    pr: str
    tas: str
    tasmin: str
    tasmax: str

    # TODO add helper method to get forcing data as xarray.Dataset?


def _parse_recipe_output(recipe_output):
    """Parse ESMValTool recipe output into a dictionary.

    Returns:
        Dictionary with forcing data variables as keys and file names as values
        and a key called directory with is the parent directory of the file names.
    """
    directory, variables = data_files_from_recipe_output(recipe_output)
    # Mold ESMValTool output into the format needed for GenericDistributedForcing
    return {"directory": directory, **variables}


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
