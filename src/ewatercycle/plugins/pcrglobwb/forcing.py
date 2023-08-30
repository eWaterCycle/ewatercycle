"""Forcing related functionality for pcrglobwb."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.esmvaltool.builder import RecipeBuilder
from ewatercycle.esmvaltool.models import ClimateStatistics, Dataset, ExtractRegion
from ewatercycle.util import get_time


class PCRGlobWBForcing(DefaultForcing):
    """Container for pcrglobwb forcing data.

    Args:
        directory: Directory where forcing data files are stored.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
        precipitationNC (optional): Input file for precipitation data. Defaults to
            'precipitation.nc'.
        temperatureNC (optional): Input file for temperature data. Defaults to
            'temperature.nc'

    Example:

        To generate forcing from ERA5 for the Rhine catchment for 2000-2001:

        ```pycon
        from pathlib import Path

        from rich import print

        from ewatercycle.plugins.pcrglobwb.forcing import PCRGlobWBForcing

        shape = Path("./src/ewatercycle/testing/data/Rhine/Rhine.shp")

        forcing = PCRGlobWBForcing.generate(
            dataset='ERA5',
            start_time='2000-01-01T00:00:00Z',
            end_time='2001-01-01T00:00:00Z',
            shape=shape.absolute(),
            start_time_climatology='2000-01-01T00:00:00Z',
            end_time_climatology='2001-01-01T00:00:00Z',
        )
        print(forcing)
        ```

        Gives something like:

        ```pycon
        PCRGlobWBForcing(
            model='pcrglobwb',
            start_time='2000-01-01T00:00:00Z',
            end_time='2001-01-01T00:00:00Z',
            directory=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/esmvaltool_output/ewcrephogjj0pt_20230816_095928/work/diagnostic/script'),
            shape=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/src/ewatercycle/testing/data/Rhine/Rhine.shp'),
            precipitationNC='pcrglobwb_OBS6_ERA5_reanaly_*_day_pr_2000-2001_Rhine.nc',
            temperatureNC='pcrglobwb_OBS6_ERA5_reanaly_*_day_tas_2000-2001_Rhine.nc'
        )
        ```
    """

    precipitationNC: Optional[str] = "precipitation.nc"
    temperatureNC: Optional[str] = "temperature.nc"

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str | Dataset | dict,
        start_time: str,
        end_time: str,
        shape: str,
        start_time_climatology: str,  # TODO make optional, default to start_time
        end_time_climatology: str,  # TODO make optional, defaults to start_time + 1 y
        extract_region: Optional[dict] = None,
        directory: Optional[str] = None,
    ) -> "PCRGlobWBForcing":
        """Generate forcings for a model.

        The forcing is generated with help of
        `ESMValTool <https://esmvaltool.org/>`_.

        Args:
            dataset: Dataset to get forcing data from.
                When string is given a predefined dataset is looked up in
                :py:const:`ewatercycle.esmvaltool.datasets.DATASETS`.
                When dict given it is passed to
                :py:class:`ewatercycle.esmvaltool.models.Dataset` constructor.
            start_time: Start time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: nd time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            shape: Path to a shape file. Used for spatial selection.
            directory:  Directory in which forcing should be written.
                If not given will create timestamped directory.
            start_time_climatology: Start time for the climatology data
            end_time_climatology: End time for the climatology data
            extract_region: Region specification, dictionary must
                contain `start_longitude`, `end_longitude`, `start_latitude`,
                `end_latitude`
        """
        # method is replicated here to document the model specific options
        return super(PCRGlobWBForcing, cls).generate(
            dataset=dataset,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            start_time_climatology=start_time_climatology,
            end_time_climatology=end_time_climatology,
            extract_region=extract_region,
            directory=directory,
        )

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str | dict = "ERA5",
        **model_specific_options,
    ):
        start_time_climatology = model_specific_options["start_time_climatology"]
        end_time_climatology = model_specific_options["end_time_climatology"]
        extract_region = model_specific_options["extract_region"]
        return build_recipe(
            start_year=start_time.year,
            end_year=end_time.year,
            shape=shape,
            dataset=dataset,
            start_year_climatology=get_time(start_time_climatology).year,
            end_year_climatology=get_time(end_time_climatology).year,
            extract_region=extract_region,
        )

    @classmethod
    def _recipe_output_to_forcing_arguments(cls, recipe_output, model_specific_options):
        # TODO dont rename recipe output, but use standard name from ESMValTool
        return {
            "precipitationNC": recipe_output["pr"],
            "temperatureNC": recipe_output["tas"],
        }


def build_recipe(
    start_year: int,
    end_year: int,
    shape: Path,
    start_year_climatology: int,
    end_year_climatology: int,
    dataset: Dataset | str | dict,
    extract_region: ExtractRegion | None = None,
):
    """
    Builds a recipe for PCRGlobWB forcing.

    Args:
        start_year: The start year of the recipe.
        end_year: The end year of the recipe.
        shape: The shape of the region to extract.
        start_year_climatology: The start year of the climatology.
        end_year_climatology: The end year of the climatology.
        dataset: The dataset to use.
        extract_region: The region to extract.
            When not given uses extents of shape.

    Returns:
        The recipe for PCRGlobWB forcing.
    """
    partial = (
        RecipeBuilder()
        .title("PCRGlobWB forcing recipe")
        .description("PCRGlobWB forcing recipe")
        .dataset(dataset)
        .start(start_year)
        .end(end_year)
    )
    if extract_region is None:
        partial = partial.region_by_shape(shape)
    else:
        partial = partial.region(
            start_longitude=extract_region["start_longitude"],
            end_longitude=extract_region["end_longitude"],
            start_latitude=extract_region["start_latitude"],
            end_latitude=extract_region["end_latitude"],
        )
    return (
        partial.add_variable("pr", units="kg m-2 d-1")
        .add_variable("tas")
        .add_variable(
            "pr_climatology",
            units="kg m-2 d-1",
            stats=ClimateStatistics(operator="mean", period="day"),
            short_name="pr",
            start_year=start_year_climatology,
            end_year=end_year_climatology,
        )
        .add_variable(
            "tas_climatology",
            stats=ClimateStatistics(operator="mean", period="day"),
            short_name="tas",
            start_year=start_year_climatology,
            end_year=end_year_climatology,
        )
        .script("hydrology/pcrglobwb.py", {"basin": shape.stem})
        .build()
    )
