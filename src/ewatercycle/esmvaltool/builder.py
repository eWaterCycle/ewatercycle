"""Builder and runner for ESMValTool recipes.

The recipes can be used to generate forcings.
"""
import logging
from pathlib import Path
from typing import Literal, Sequence

from ewatercycle.esmvaltool.datasets import DATASETS
from ewatercycle.esmvaltool.diagnostic import copier
from ewatercycle.esmvaltool.schema import (
    ClimateStatistics,
    Dataset,
    Diagnostic,
    Documentation,
    Recipe,
    Script,
    TargetGrid,
    Variable,
)
from ewatercycle.util import get_extents

DIAGNOSTIC_NAME = "diagnostic"
SPATIAL_PREPROCESSOR_NAME = "spatial"
SCRIPT_NAME = "script"
DEFAULT_DIAGNOSTIC_SCRIPT = copier.__file__

logger = logging.getLogger(__name__)


class RecipeBuilder:
    """Builder for ESMValTool recipes tailored to generate forcings.

    Example:

        To create a recipe from ERA5 dataset and the Rhine basin:

        .. code-block:: python

            >>> from ewatercycle.testing.fixtures import rhine_shape
            >>> from ewatercycle.forcing import RecipeBuilder
            >>> recipe = (
            ...     RecipeBuilder()
            ...     .title("Generic distributed forcing recipe")
            ...     .dataset("ERA5")
            ...     .start(2000)
            ...     .end(2001)
            ...     .shape(rhine_shape())
            ...     .add_variable("pr")
            ...     .build()
            ... )
            >>> recipe.save("recipe.yml")

        To run the recipe:

        .. code-block:: bash

            esmvaltool recipe.yml

    Order in which methods are called matters in the following cases:

    * regrid before adding variables
    * lump after spatial selection and before adding variables
    * temporal selection before adding variables
    * spatial selection before adding variables

    """

    _recipe: Recipe
    _start_year: int = 0
    _end_year: int = 10000
    _mip: str = "day"

    def __init__(self) -> None:
        self._recipe = Recipe(
            documentation=Documentation(
                description="",
                title="",
                authors=["unmaintained"],
                projects=["ewatercycle"],
            ),
            preprocessors={
                SPATIAL_PREPROCESSOR_NAME: {},
            },
            diagnostics={
                DIAGNOSTIC_NAME: Diagnostic(
                    variables={},
                    scripts={SCRIPT_NAME: {"script": DEFAULT_DIAGNOSTIC_SCRIPT}},
                )
            },
        )

    def build(self) -> Recipe:
        """Build the recipe.

        Should be called after all other methods.
        """
        # TODO de-duplicate preprocessors
        if self._recipe.datasets is None or len(self._recipe.datasets) == 0:
            raise ValueError("Recipe has no dataset")
        return self._recipe

    def description(self, description: str) -> "RecipeBuilder":
        """Set the description of the recipe.

        Args:
            description: Description of the recipe.
        """
        self._recipe.documentation.description = description
        return self

    def title(self, title: str) -> "RecipeBuilder":
        """Set the title of the recipe.

        Args:
            title: Title of the recipe.
        """
        self._recipe.documentation.title = title
        return self

    def dataset(self, dataset: Dataset | str | dict) -> "RecipeBuilder":
        """Set the dataset of the recipe.

        Args:
            dataset: Dataset to use for the recipe.
                When string is given a predefined dataset is looked up in
                :py:const:`ewatercycle.esmvaltool.datasets.DATASETS`.
                When dict given it is passed to
                :py:class:`ewatercycle.esmvaltool.models.Dataset` constructor.

        Only one dataset is allowed when generating eWaterCycle forcings.
        Calling this method again will overwrite the previous dataset.
        """
        # Can only have one dataset
        if isinstance(dataset, str):
            dataset = DATASETS[dataset]
        elif isinstance(dataset, dict):
            dataset = Dataset(**dataset)
        if not isinstance(dataset, Dataset):
            raise ValueError(
                f"dataset must be a Dataset, str or dict, got {type(dataset)}"
            )
        self._recipe.datasets = [dataset]
        return self

    def mip(self, value: str) -> "RecipeBuilder":
        """Set the default time frequency for all later added variables.

        Args:
            value: time frequency, e.g. 'day', 'Eday', 'CFday', 'fx'.
                Defaults to 'day'.
        """
        self._mip = value
        return self

    def start(self, value: int) -> "RecipeBuilder":
        """Set the start year of the recipe.

        Args:
            value: Start year of the recipe.
        """
        # TODO also accept datetime object
        self._start_year = value
        return self

    def end(self, value: int) -> "RecipeBuilder":
        """Set the end year of the recipe.

        Args:
            value: End year of the recipe.
        """
        # TODO also accept datetime object
        # TODO is end year inclusive or exclusive?
        self._end_year = value
        return self

    @property
    def _preprocessors(self):
        if self._recipe.preprocessors is None:
            raise ValueError("Recipe has no preprocessors")
        return self._recipe.preprocessors

    def regrid(self, scheme: str, target_grid: TargetGrid) -> "RecipeBuilder":
        """Regrid the data from the dataset to a different grid.

        Args:
            schema: Regridding scheme to use. See
                https://docs.esmvaltool.org/projects/ESMValCore/en/latest/recipes/recipe_file.html#regrid
            target_grid: Target grid to regrid to.
        """
        self._preprocessors[SPATIAL_PREPROCESSOR_NAME]["regrid"] = {
            "scheme": scheme,
            "target_grid": target_grid,
        }
        return self

    def shape(
        self, file: Path | str, crop: bool = True, decomposed: bool = False
    ) -> "RecipeBuilder":
        """Select data within a shapefile.

        Args:
            file: Path to shapefile.
            crop: Crop data to shapefile extent. Otherwise data outside shapefile extent is set to NaN.
            decomposed: Decompose shapefile into separate polygons.
        """
        self._preprocessors[SPATIAL_PREPROCESSOR_NAME]["extract_shape"] = {
            "shapefile": str(file),
            "crop": crop,
            "decomposed": decomposed,
        }
        return self

    def region(
        self,
        start_longitude: float,
        end_longitude: float,
        start_latitude: float,
        end_latitude: float,
    ) -> "RecipeBuilder":
        """Select data within a region.

        Args:
            start_longitude: Start longitude of the region.
            end_longitude: End longitude of the region.
            start_latitude: Start latitude of the region.
            end_latitude: End latitude of the region.
        """
        self._preprocessors[SPATIAL_PREPROCESSOR_NAME]["extract_region"] = {
            "start_longitude": start_longitude,
            "end_longitude": end_longitude,
            "start_latitude": start_latitude,
            "end_latitude": end_latitude,
        }
        return self

    def region_by_shape(self, shape: Path, pad=0) -> "RecipeBuilder":
        """Select data within a region defined by extents of a shapefile.

        Args:
            shape: Path to shapefile.
            pad: Pad the region with this many degrees.
        """
        extents = get_extents(shape, pad)
        return self.region(**extents)

    def lump(
        self,
        operator: Literal[
            "mean", "median", "std_dev", "sum", "variance", "min", "max", "rms"
        ] = "mean",
    ) -> "RecipeBuilder":
        """Lump gridded data into a single value spatially.

        See
        https://docs.esmvaltool.org/projects/ESMValCore/en/latest/api/esmvalcore.preprocessor.html#esmvalcore.preprocessor.area_statistics

        Args:
            operator: The operator to use for lumping.
        """
        # TODO do we need different operator for different variables?
        # TODO should lumping come after unit conversion? Or does it not matter?
        self._preprocessors[SPATIAL_PREPROCESSOR_NAME]["area_statistics"] = {
            "operator": operator
        }
        return self

    @property
    def _diagnostic(self) -> Diagnostic:
        if self._recipe.diagnostics is None:
            raise ValueError("Recipe has no diagnostics")
        return self._recipe.diagnostics[DIAGNOSTIC_NAME]

    def add_variables(self, variables: Sequence[str]) -> "RecipeBuilder":
        """Add variables to the recipe.

        Args:
            variables: Names of variables to add to the recipe.
        """
        for variable in variables:
            self.add_variable(variable)
        return self

    def add_variable(
        self,
        variable: str,
        mip: str | None = None,
        units: str | None = None,
        stats: ClimateStatistics | None = None,
        short_name: str | None = None,
        start_year: int | None | Literal[False] = None,
        end_year: int | None | Literal[False] = None,
    ):
        """Add a variable to the recipe.

        Args:
            variable: The name of the variable to add.
            mip: The MIP table to use for the variable.
                If not given then defaults to what was set with self.mip(value).
            units: The unit to convert the variable to.
                Default no conversion. See
                https://docs.esmvaltool.org/projects/ESMValCore/en/latest/recipes/recipe_file.html#convert-units
            stats: The climate statistics to apply to the variable.
                Defaults to not applying any statistics.
            short_name: A short name for the variable. Defaults to variable name.
            start_year: The start year of the variable.
                Defaults to start year of dataset.
                Use False to disable temporal selection.
            end_year: The end year of the variable. Defaults to end year of dataset.
                Use False to disable temporal selection.

        """
        # TODO check variable is in dataset
        # Each variable needs its own single preprocessor
        preprocessor_name = self._add_preprocessor(variable, units, stats)
        if self._diagnostic.variables is None:
            raise ValueError("Recipe has no variables")
        if mip is None:
            mip = self._mip
        if start_year is None:
            start_year = self._start_year
        if start_year is False:
            start_year = None
        if end_year is None:
            end_year = self._end_year
        if end_year is False:
            end_year = None
        self._diagnostic.variables[variable] = Variable(
            mip=mip,
            preprocessor=preprocessor_name,
            start_year=start_year,
            # TODO check if end_year is exclusive or inclusive
            end_year=end_year,
            short_name=short_name,
        )
        return self

    def _add_preprocessor(self, preprocessor_name, units, stats):
        if preprocessor_name not in self._preprocessors:
            preprocessor = {}
            # TODO allow spatial preprocessor to be configured after adding variables
            if SPATIAL_PREPROCESSOR_NAME in self._preprocessors:
                preprocessor = {**self._preprocessors[SPATIAL_PREPROCESSOR_NAME]}
            if units is not None:
                preprocessor["convert_units"] = {"units": units}
            if stats is not None:
                preprocessor["climate_statistics"] = {
                    "operator": stats.operator,
                    "period": stats.period,
                }
            self._preprocessors[preprocessor_name] = preprocessor
        return preprocessor_name

    def script(
        self, script: str, arguments: dict[str, str] | None = None
    ) -> "RecipeBuilder":
        """Set script of recipe.

        When script has not been set will default to copying
        the ESMValTool preprocessed files to the output directory
        using the :py:mod:`ewatercycle.esmvaltool.diagnostic.copier` script.

        Args:
            script: Path to script to run.
            arguments: Arguments to pass to the script.
        """
        if self._diagnostic.scripts is None:
            raise ValueError("Recipe has no scripts")
        self._diagnostic.scripts[SCRIPT_NAME] = Script(script=script, **arguments or {})
        return self


def build_generic_distributed_forcing_recipe(
    start_year: int,
    end_year: int,
    shape: Path,
    dataset: Dataset | str | dict = "ERA5",
    variables: Sequence[str] = ("pr", "tas", "tasmin", "tasmax"),
):
    """Build a generic distributed forcing recipe.

    Args:
        start_year: Start year of the data to retrieve.
        end_year: End year of the data to retrieve.
        shape: Path to shapefile. Used for spatial selection.
        dataset: Dataset to use for the recipe.
        variables: Names of variables to add to the recipe.

    Recipe will return a NetCDF file for each variable.
    """
    return (
        RecipeBuilder()
        .title("Generic distributed forcing recipe")
        .description("Generic distributed forcing recipe")
        .dataset(dataset)
        .start(start_year)
        .end(end_year)
        .shape(shape)
        .add_variables(variables)
        .build()
    )


def build_generic_lumped_forcing_recipe(
    start_year: int,
    end_year: int,
    shape: Path,
    dataset: Dataset | str | dict = "ERA5",
    variables: Sequence[str] = ("pr", "tas", "tasmin", "tasmax"),
):
    """Build a generic lumped forcing recipe.

    Args:
        start_year: Start year of the data to retrieve.
        end_year: End year of the data to retrieve.
        shape: Path to shapefile. Used for spatial selection.
        dataset: Dataset to use for the recipe.
        variables: Names of variables to add to the recipe.

    Recipe will return a NetCDF file for each variable.
    """
    return (
        RecipeBuilder()
        .title("Generic lumped forcing recipe")
        .description("Generic lumped forcing recipe")
        .dataset(dataset)
        .start(start_year)
        .end(end_year)
        .shape(shape)
        .lump()
        .add_variables(variables)
        .build()
    )
