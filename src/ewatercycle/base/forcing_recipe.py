from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Literal, Sequence

from esmvalcore.experimental.recipe import RecipeOutput
from ruamel.yaml import YAML

from ewatercycle.base.esmvaltool_wrapper import (
    Dataset,
    Diagnostic,
    Documentation,
    Recipe,
    Script,
    Variable,
)

DIAGNOSTIC_NAME = "diagnostic"
SPATIAL_PREPROCESSOR_NAME = "spatial"
SCRIPT_NAME = "script"


@dataclass
class Stats:
    operator: Literal["mean", "std", "min", "max", "median", "sum"] = "mean"
    period: Literal["hour", "day", "month", "year"] = "day"


def load_recipe(path: Path) -> Recipe:
    return string_to_recipe(path.read_text())


def save_recipe(recipe: Recipe, path: Path):
    path.write_text(recipe_to_string(recipe))


def recipe_to_string(recipe: Recipe) -> str:
    yaml = YAML(typ="rt")
    stream = StringIO()
    yaml.dump(recipe.dict(exclude_none=True), stream)
    return stream.getvalue()


def string_to_recipe(recipe_string: str) -> Recipe:
    yaml = YAML(typ="rt")
    raw_recipe = yaml.load(recipe_string)
    return Recipe(**raw_recipe)


def run_recipe(recipe: Recipe, output_dir: str | None) -> RecipeOutput:
    pass


class RecipeBuilder:
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
            diagnostics={DIAGNOSTIC_NAME: Diagnostic(variables={}, scripts={})},
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
            dataset = DATASETS[dataset]
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

    def shape(
        self, file: Path, crop: bool = True, decomposed: bool = False
    ) -> "RecipeBuilder":
        self._recipe.preprocessors[SPATIAL_PREPROCESSOR_NAME] = {
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
        self._recipe.preprocessors[SPATIAL_PREPROCESSOR_NAME] = {
            "extract_region": {
                "start_longitude": start_longitude,
                "end_longitude": end_longitude,
                "start_latitude": start_latitude,
                "end_latitude": end_latitude,
            }
        }
        return self

    @property
    def _diagnostic(self) -> Diagnostic:
        return self._recipe.diagnostics[DIAGNOSTIC_NAME]

    def add_unit(self, name: str, units: str) -> "RecipeBuilder":
        self._recipe.preprocessors[name] = {"convert_units": {"units": units}}
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
        stats: Stats | None = None,
        short_name: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> "RecipeBuilder":
        # TODO check variable is in dataset
        # Each variable needs its own single preprocessor
        preprocessor_name = self._add_preprocessor(variable, units, stats)
        self._diagnostic.variables[variable] = Variable(
            mip=mip,
            preprocessor=preprocessor_name,
            start_year=start_year or self._start_year,
            end_year=end_year or self._end_year,
            short_name=short_name,
        )
        return self

    def _add_preprocessor(self, preprocessor_name, units, stats):
        if preprocessor_name not in self._recipe.preprocessors:
            preprocessor = {}
            if SPATIAL_PREPROCESSOR_NAME in self._recipe.preprocessors:
                preprocessor = {**self._recipe.preprocessors[SPATIAL_PREPROCESSOR_NAME]}
            if units is not None:
                preprocessor["convert_units"] = {"units": units}
            if stats is not None:
                preprocessor["climate_statistics"] = {
                    "operator": stats.operator,
                    "period": stats.period,
                }
            self._recipe.preprocessors[preprocessor_name] = preprocessor
        return preprocessor_name

    def script(self, script: str, arguments: dict[str, str]) -> "RecipeBuilder":
        self._diagnostic.scripts = {SCRIPT_NAME: {"script": script, **arguments}}
        # If script is not set then should there be `scripts: null` in recipe yaml?
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


# TODO move to src/ewatercycle/plugins/pcrglobwb/forcing.py
def build_pcrglobwb_recipe(
    start_year: int,
    end_year: int,
    shape: Path,
    start_year_climatology: int,
    end_year_climatology: int,
    dataset: Dataset | str = "ERA5",
):
    return (
        RecipeBuilder()
        .title("PCRGlobWB forcing recipe")
        .description("PCRGlobWB forcing recipe")
        .dataset(dataset)
        .start(start_year)
        .end(end_year)
        # Instead of calculating extends of shape
        # and then using extract_region preprocessor
        # we use extract_shape with crop=True
        # to get less data
        .shape(shape, crop=True)
        .add_variable("pr", units="kg m-2 d-1")
        .add_variable("tas")
        .add_variable(
            "pr_climatology",
            units="kg m-2 d-1",
            stats=Stats(operator="mean", period="day"),
            short_name="pr",
            start_year=start_year_climatology,
            end_year=end_year_climatology,
        )
        .add_variable(
            "tas_climatology",
            stats=Stats(operator="mean", period="day"),
            short_name="tas",
            start_year=start_year_climatology,
            end_year=end_year_climatology,
        )
        .script("hydrology/pcrglobwb.py", {"basin": shape.stem})
        .build()
    )


def build_wflow_recipe():
    pass


DATASETS = {
    "ERA5": Dataset(
        **{
            "dataset": "ERA5",
            "project": "OBS6",
            "tier": 3,
            "type": "reanaly",
            "version": 1,
            "mip": "day",
        }
    ),
    "ERA-Interim": Dataset(
        **{
            "dataset": "ERA-Interim",
            "project": "OBS6",
            "tier": 3,
            "type": "reanaly",
            "version": 1,
            "mip": "day",
        }
    ),
}
"""Dictionary of ready to use forcing datasets.

Where key is the name of the dataset and
value is an `ESMValTool dataset section <https://docs.esmvaltool.org/projects/ESMValCore/en/latest/recipe/overview.html#datasets>`_.
"""
