"""Builder and runner for ESMValTool recipes, the recipes can be used to generate forcings."""
from pathlib import Path
from typing import Sequence

from ewatercycle.esmvaltool.datasets import DATASETS
from ewatercycle.esmvaltool.diagnostic import copy
from ewatercycle.esmvaltool.models import (
    ClimateStatistics,
    Dataset,
    Diagnostic,
    Documentation,
    Recipe,
    Script,
    Variable,
)
from ewatercycle.util import get_extents

DIAGNOSTIC_NAME = "diagnostic"
SPATIAL_PREPROCESSOR_NAME = "spatial"
SCRIPT_NAME = "script"
DEFAULT_DIAGNOSTIC_SCRIPT = copy.__file__


class RecipeBuilder:
    """Builder for ESMValTool recipes tailored to generate forcings.

    Example:

        ```pycon
        >>> from ewatercycle.forcing import RecipeBuilder
        >>> recipe = (
        ...     RecipeBuilder()
        ...     .title("Generic distributed forcing recipe")
        ...     .description("Generic distributed forcing recipe")
        ...     .dataset("ERA5")
        ...     .start(2000)
        ...     .end(2001)
        ...     .shape("shapefile.shp")
        ...     .add_variable("pr")
        ...     .build()
        ... )
        ```

    """

    _recipe: Recipe
    _start_year: int = 0
    _end_year: int = 10000

    def __init__(self) -> None:
        self._recipe = Recipe(
            documentation=Documentation(
                description="",
                title="",
                authors=["unmaintained"],
                projects=["ewatercycle"],
            ),
            preprocessors={},
            diagnostics={
                DIAGNOSTIC_NAME: Diagnostic(
                    variables={},
                    scripts={
                        SCRIPT_NAME: {"script": DEFAULT_DIAGNOSTIC_SCRIPT, "args": {}}
                    },
                )
            },
        )

    def build(self) -> Recipe:
        return self._recipe

    def description(self, description: str) -> "RecipeBuilder":
        self._recipe.documentation.description = description
        return self

    def title(self, title: str) -> "RecipeBuilder":
        self._recipe.documentation.title = title
        return self

    def dataset(self, dataset: Dataset | str) -> "RecipeBuilder":
        # Can only have one dataset
        if isinstance(dataset, str):
            dataset = Dataset(**DATASETS[dataset])
        self._recipe.datasets = [dataset]
        return self

    def start(self, value: int) -> "RecipeBuilder":
        # TODO also accept datetime object
        self._start_year = value
        return self

    def end(self, value: int) -> "RecipeBuilder":
        # TODO also accept datetime object
        self._end_year = value
        return self

    @property
    def _preprocessors(self):
        if self._recipe.preprocessors is None:
            raise ValueError("Recipe has no preprocessors")
        return self._recipe.preprocessors

    def shape(
        self, file: Path, crop: bool = True, decomposed: bool = False
    ) -> "RecipeBuilder":

        self._preprocessors[SPATIAL_PREPROCESSOR_NAME] = {
            "extract_shape": {
                "shapefile": str(file),
                "crop": crop,
                "decomposed": decomposed,
            }
        }
        return self

    def region(
        self,
        start_longitude: float,
        end_longitude: float,
        start_latitude: float,
        end_latitude: float,
    ) -> "RecipeBuilder":
        self._preprocessors[SPATIAL_PREPROCESSOR_NAME] = {
            "extract_region": {
                "start_longitude": start_longitude,
                "end_longitude": end_longitude,
                "start_latitude": start_latitude,
                "end_latitude": end_latitude,
            }
        }
        return self

    def region_by_shape(self, shape: Path, pad=0) -> "RecipeBuilder":
        extents = get_extents(shape, pad)
        return self.region(**extents)

    @property
    def _diagnostic(self) -> Diagnostic:
        if self._recipe.diagnostics is None:
            raise ValueError("Recipe has no diagnostics")
        return self._recipe.diagnostics[DIAGNOSTIC_NAME]

    def add_unit(self, name: str, units: str) -> "RecipeBuilder":
        self._preprocessors[name] = {"convert_units": {"units": units}}
        return self

    def add_variables(self, variables: Sequence[str]) -> "RecipeBuilder":
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
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> "RecipeBuilder":
        # TODO check variable is in dataset
        # Each variable needs its own single preprocessor
        preprocessor_name = self._add_preprocessor(variable, units, stats)
        if self._diagnostic.variables is None:
            raise ValueError("Recipe has no variables")
        self._diagnostic.variables[variable] = Variable(
            mip=mip,
            preprocessor=preprocessor_name,
            start_year=start_year or self._start_year,
            # TODO check if end_year is exclusive or inclusive
            end_year=end_year or self._end_year,
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

    def script(self, script: str, arguments: dict[str, str]) -> "RecipeBuilder":
        if self._diagnostic.scripts is None:
            raise ValueError("Recipe has no scripts")
        self._diagnostic.scripts[SCRIPT_NAME] = Script(script=script, **arguments)
        return self


def build_generic_distributed_forcing_recipe(
    start_year: int,
    end_year: int,
    shape: Path,
    dataset: Dataset | str = "ERA5",
    variables: Sequence[str] = ("pr", "tas", "tasmin", "tasmax"),
):
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
