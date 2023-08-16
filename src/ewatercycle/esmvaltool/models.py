"""ESMValTool recipe and preprocessor models."""
from io import StringIO
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from ruamel.yaml import YAML


class Dataset(BaseModel):
    """
    https://github.com/ESMValGroup/ESMValCore/blob/main/esmvalcore/_recipe/recipe_schema.yml

    dataset:
        dataset: str()
        project: str(required=False)
        start_year: int(required=False, min=0000, max=10000)
        end_year: int(required=False, min=0000, max=10000)
        ensemble: any(str(), list(str()), required=False)
        exp: any(str(), list(str()), required=False)
        mip: str(required=False)
        realm: str(required=False)
        shift: str(required=False)
        tier: int(min=1, max=3, required=False)
        type: str(required=False)
    """

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
    # TODO add min max
    tier: int | None = None
    type: str | None = None


class Variable(BaseModel):
    """
    project: str(required=False)
    start_year: int(required=False, min=0000, max=10000)
    end_year: int(required=False, min=0000, max=10000)
    ensemble: any(str(), list(str()), required=False)
    exp: any(str(), list(str()), required=False)
    mip: str(required=False)
    preprocessor: str(required=False)
    reference_dataset: str(required=False)
    alternative_dataset: str(required=False)
    fx_files: list(required=False)
    additional_datasets: list(include('dataset'), required=False)
    """

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
    """
    script: str()

    """

    model_config = ConfigDict(extra="allow")
    script: str


class Diagnostic(BaseModel):
    """
    From  https://github.com/ESMValGroup/ESMValCore/blob/main/esmvalcore/_recipe/recipe_schema.yml

        scripts: any(null(), map(include('script')))
        additional_datasets: list(include('dataset'), required=False)
        title: str(required=False)
        description: str(required=False)
        themes: list(str(), required=False)
        realms: list(str(), required=False)
        variables: map(include('variable'), null(), required=False)
    """

    scripts: dict[str, Script] | None = None
    additional_datasets: list[Dataset] | None = None
    title: str | None = None
    description: str | None = None
    themes: list[str] | None = None
    realms: list[str] | None = None
    variables: dict[str, Variable] | None = None


class Documentation(BaseModel):
    """
    title: str()
    description: str()
    authors: list(str(), min=1)
    projects: list(str(), required=False)
    references: list(str(), required=False)
    """

    title: str
    description: str
    # TODO add min 1
    authors: list[str]
    projects: list[str] | None = None
    references: list[str] | None = None


class Recipe(BaseModel):
    """
    documentation: include('documentation')
    datasets: list(include('dataset'), required=False)
    preprocessors: map(map(), required=False)
    diagnostics: map(include('diagnostic'), required=False)
    """

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
    """Arguments for the `climate_statistics` preprocessor."""

    operator: Literal["mean", "std", "min", "max", "median", "sum"] = "mean"
    period: Literal["hour", "day", "month", "year"] = "day"


ExtractRegion = dict[
    Literal["start_longitude", "end_longitude", "start_latitude", "end_latitude"], float
]
"""Arguments for the `extract_region` preprocessor."""
