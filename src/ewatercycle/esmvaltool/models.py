"""ESMValTool recipe and preprocessor models.

The classes and their attributes in this module are based
on the ESMValTool recipe schema at
https://github.com/ESMValGroup/ESMValCore/blob/main/esmvalcore/_recipe/recipe_schema.yml
.
"""
from io import StringIO
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from ruamel.yaml import YAML


class Dataset(BaseModel):
    """ESMValTool dataset section."""

    dataset: str
    project: str | None = None
    # TODO add min max
    start_year: int | None = None
    end_year: int | None = None
    ensemble: str | list[str] | None = None
    exp: str | list[str] | None = None
    mip: str | None = None
    realm: str | None = None
    shift: str | None = None
    tier: Literal[1, 2, 3] | None = None
    type: str | None = None
    grid: str | None = None


class Variable(BaseModel):
    """ESMValTool variable section."""

    project: str | None = None
    # TODO add min max
    start_year: int | None = None
    end_year: int | None = None
    ensemble: str | list[str] | None = None
    timerange: str | None = None  # note: not in yamale spec
    exp: str | list[str] | None = None
    mip: str | None = None
    preprocessor: str | None = None
    reference_dataset: str | None = None
    alternative_dataset: str | None = None
    fx_files: list[str] | None = None
    additional_datasets: list[Dataset] | None = None
    short_name: str | None = None


class Script(BaseModel):
    """ESMValTool script section."""

    model_config = ConfigDict(extra="allow")
    script: str


class Diagnostic(BaseModel):
    """ESMValTool diagnostic section."""

    scripts: dict[str, Script] | None = None
    additional_datasets: list[Dataset] | None = None
    title: str | None = None
    description: str | None = None
    themes: list[str] | None = None
    realms: list[str] | None = None
    variables: dict[str, Variable] | None = None


class Documentation(BaseModel):
    """ESMValTool documentation section."""

    title: str
    description: str
    # TODO add min 1
    authors: list[str]
    projects: list[str] | None = None
    references: list[str] | None = None


class Recipe(BaseModel):
    """ESMValTool recipe."""

    documentation: Documentation
    datasets: list[Dataset] | None = None
    # value depends on the key which is the name of the preprocessor
    # see https://docs.esmvaltool.org/projects/ESMValCore/en/v2.9.0/recipe/preprocessor.html
    preprocessors: dict[str, dict[str, Any]] | None = None
    diagnostics: dict[str, Diagnostic] | None = None

    @classmethod
    def load(cls, path: str) -> "Recipe":
        with open(path, encoding="utf-8") as f:
            return cls.from_yaml(f.read())

    @classmethod
    def from_yaml(cls, recipe_string: str) -> "Recipe":
        yaml = YAML(typ="rt")
        raw_recipe = yaml.load(recipe_string)
        return cls(**raw_recipe)

    def to_yaml(self) -> str:
        # use rt to preserve order of preprocessor keys
        yaml = YAML(typ="rt")
        stream = StringIO()
        yaml.dump(self.model_dump(exclude_none=True), stream)
        return stream.getvalue()

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.to_yaml())


class ClimateStatistics(BaseModel):
    """Arguments for the :py:func:`~esmvalcore.preprocessor.climate_statistics` preprocessor."""

    operator: Literal["mean", "std", "min", "max", "median", "sum"] = "mean"
    period: Literal["hour", "day", "month", "year"] = "day"


ExtractRegion = dict[
    Literal["start_longitude", "end_longitude", "start_latitude", "end_latitude"], float
]
"""Arguments for the :py:func:`~esmvalcore.preprocessor.extract_region` preprocessor."""

TargetGrid = dict[
    Literal[
        "start_longitude",
        "end_longitude",
        "start_latitude",
        "end_latitude",
        "step_longitude",
        "step_latitude",
    ],
    float,
]
"""Type for target_grid argument for the :py:func:`~esmvalcore.preprocessor.regrid` preprocessor."""
