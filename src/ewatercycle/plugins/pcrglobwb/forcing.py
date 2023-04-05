"""Forcing related functionality for pcrglobwb"""

from typing import Literal, Optional

from esmvalcore.experimental import get_recipe

from ewatercycle.forcing._default import DefaultForcing, _session
from ewatercycle.forcing.datasets import DATASETS
from ewatercycle.util import (
    data_files_from_recipe_output,
    get_extents,
    get_time,
    to_absolute_path,
)


class PCRGlobWBForcing(DefaultForcing):
    """Container for pcrglobwb forcing data.

    Args:
        precipitationNC (str): Input file for precipitation data.
        temperatureNC (str): Input file for temperature data.
    """

    # type ignored because pydantic wants literal in base class while mypy does not
    model: Literal["pcrglobwb"] = "pcrglobwb"  # type: ignore
    precipitationNC: Optional[str] = "precipitation.nc"
    temperatureNC: Optional[str] = "temperature.nc"

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        start_time_climatology: str,  # TODO make optional, default to start_time
        end_time_climatology: str,  # TODO make optional, defaults to start_time + 1 y
        extract_region: Optional[dict] = None,
        directory: Optional[str] = None,
    ) -> "PCRGlobWBForcing":
        """
        start_time_climatology (str): Start time for the climatology data
        end_time_climatology (str): End time for the climatology data
        extract_region (dict): Region specification, dictionary must
            contain `start_longitude`, `end_longitude`, `start_latitude`,
            `end_latitude`
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_pcrglobwb.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = (
            "crop_basin",
            "preproc_pr",
            "preproc_tas",
            "preproc_pr_clim",
            "preproc_tas_clim",
        )

        if dataset is not None:
            recipe.data["diagnostics"]["diagnostic_daily"]["additional_datasets"] = [
                DATASETS[dataset]
            ]

        basin = to_absolute_path(shape).stem
        recipe.data["diagnostics"]["diagnostic_daily"]["scripts"]["script"][
            "basin"
        ] = basin

        if extract_region is None:
            extract_region = get_extents(shape)
        for preproc_name in preproc_names:
            recipe.data["preprocessors"][preproc_name][
                "extract_region"
            ] = extract_region

        variables = recipe.data["diagnostics"]["diagnostic_daily"]["variables"]
        var_names = "tas", "pr"

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]["start_year"] = startyear

        endyear = get_time(end_time).year
        for var_name in var_names:
            variables[var_name]["end_year"] = endyear

        var_names_climatology = "pr_climatology", "tas_climatology"

        startyear_climatology = get_time(start_time_climatology).year
        for var_name in var_names_climatology:
            variables[var_name]["start_year"] = startyear_climatology

        endyear_climatology = get_time(end_time_climatology).year
        for var_name in var_names_climatology:
            variables[var_name]["end_year"] = endyear_climatology

        # generate forcing data and retrieve useful information
        recipe_output = recipe.run(session=_session(directory))
        # TODO dont open recipe output, but use standard name from ESMValTool
        directory, forcing_files = data_files_from_recipe_output(recipe_output)

        # instantiate forcing object based on generated data
        return PCRGlobWBForcing(
            directory=directory,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            precipitationNC=forcing_files["pr"],
            temperatureNC=forcing_files["tas"],
        )
