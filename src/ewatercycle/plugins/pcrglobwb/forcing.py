"""Forcing related functionality for pcrglobwb"""

from typing import Literal, Optional

from esmvalcore.experimental import get_recipe

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.esmvaltool.datasets import DATASETS
from ewatercycle.esmvaltool.output import data_files_from_recipe_output
from ewatercycle.esmvaltool.run import run_esmvaltool_recipe
from ewatercycle.util import get_extents, get_time, to_absolute_path


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
            start_time_climatology: Start time for the climatology data
            end_time_climatology: End time for the climatology data
            extract_region: Region specification, dictionary must
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
        recipe_output = run_esmvaltool_recipe(recipe, directory)
        # TODO dont open recipe output, but use standard name from ESMValTool
        directory, forcing_files = data_files_from_recipe_output(recipe_output)

        # instantiate forcing object based on generated data
        generated_forcing = PCRGlobWBForcing(
            directory=directory,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            precipitationNC=forcing_files["pr"],
            temperatureNC=forcing_files["tas"],
        )
        generated_forcing.save()
        return generated_forcing
