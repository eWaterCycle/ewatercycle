"""Forcing related functionality for wflow."""
from datetime import datetime
from pathlib import Path
from typing import Dict, Literal, Optional

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.esmvaltool.builder import RecipeBuilder
from ewatercycle.esmvaltool.models import Dataset


class WflowForcing(DefaultForcing):
    """Container for wflow forcing data.

    Args:
        directory: Directory where forcing data files are stored.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
        netcdfinput (str) = "inmaps.nc": Path to forcing file.
        Precipitation (str) = "/pr": Variable name of precipitation data in
            input file.
        EvapoTranspiration (str) = "/pet": Variable name of
            evapotranspiration data in input file.
        Temperature (str) = "/tas": Variable name of temperature data in
            input file.
        Inflow (str) = None: Variable name of inflow data in input file.
    """

    # type ignored because pydantic wants literal in base class while mypy does not
    model: Literal["wflow"] = "wflow"  # type: ignore
    netcdfinput: str = "inmaps.nc"
    Precipitation: str = "/pr"  # noqa: N803
    EvapoTranspiration: str = "/pet"
    Temperature: str = "/tas"
    Inflow: Optional[str] = None

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        dem_file: str,
        directory: Optional[str] = None,
        extract_region: Optional[Dict[str, float]] = None,
    ) -> "WflowForcing":
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
            dem_file: Name of the dem_file to use.
            extract_region: Region specification, dictionary must
                contain `start_longitude`, `end_longitude`, `start_latitude`,
                `end_latitude`
        """
        return super(WflowForcing, cls).generate(
            dataset=dataset,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            dem_file=dem_file,
            directory=directory,
            extract_region=extract_region,
        )

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str,
        **model_specific_options
    ):
        extract_region = model_specific_options["extract_region"]
        return build_recipe(
            start_year=start_time.year,
            end_year=end_time.year,
            shape=shape,
            dataset=dataset,
            dem_file=model_specific_options["dem_file"],
            extract_region=extract_region,
        )

    @classmethod
    def _recipe_output_to_forcing_arguments(cls, recipe_output, model_specific_options):
        first_file = list(recipe_output.values())[0]
        return {
            "netcdfinput": first_file,
        }


def build_recipe(
    start_year: int,
    end_year: int,
    shape: Path,
    dataset: Dataset | str,
    dem_file: str,
    extract_region: Optional[Dict[str, float]] = None,
):
    partial = (
        RecipeBuilder()
        .title("Generate forcing for the WFlow hydrological model")
        .dataset(dataset)
        .start(start_year)
        .end(end_year)
    )
    if extract_region is None:
        MAGIC_PAD = 3  # TODO why 3?
        partial = partial.region_by_shape(shape, pad=MAGIC_PAD)
    else:
        partial = partial.region(
            start_longitude=extract_region["start_longitude"],
            end_longitude=extract_region["end_longitude"],
            start_latitude=extract_region["start_latitude"],
            end_latitude=extract_region["end_latitude"],
        )
    return (
        partial.add_variables(["tas", "pr", "psl", "rsds"])
        .add_variable("orog", mip="fix")
        .add_variable("rsdt", mip="CFday")
        .script(
            "hydrology/wflow.py",
            {
                "basin": shape.stem,
                "dem_file": dem_file,
                "regrid": "area_weighted",
            },
        )
        .build()
    )
