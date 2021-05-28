"""Forcing related functionality for pcrglobwb"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from esmvalcore.experimental import get_recipe

from .datasets import DATASETS
from .default import DefaultForcing
from ..util import get_time, get_extents, data_files_from_recipe_output

GENERATE_DOCS = """
Options:
    start_time_climatology (str): Start time for the climatology data
    end_time_climatology (str): End time for the climatology data
    extract_region (dict): Region specification, dictionary must contain `start_longitude`,
        `end_longitude`, `start_latitude`, `end_latitude`
"""
LOAD_DOCS = """
Fields:
    precipitationNC (str): Input file for precipitation data.
    temperatureNC (str): Input file for temperature data.
"""


@dataclass
class PCRGlobWBForcing(DefaultForcing):
    """Container for pcrglobwb forcing data."""

    # Overwrite (repeat) the defaults so that the docstrings are included
    directory: str
    """Location where the forcing data is stored."""
    start_time: str
    """Start time of the forcing data"""
    end_time: str
    """End time of the forcing data"""

    # Model-specific attributes (preferably with default values):
    precipitationNC: str
    """Input file for precipitation data."""
    temperatureNC: str
    """Input file for temperature data."""

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        start_time_climatology: str,
        end_time_climatology: str,
        extract_region: dict = None,
    ) -> 'PCRGlobWBForcing':
        """Generate WflowForcing data with ESMValTool.

        Attributes:
            dataset: Name of the source dataset. See :py:data:`.DATASETS`.
            start_time: Start time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: End time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            shape: Path to a shape file. Used for spatial selection.
            start_time_climatology: Start time for the climatology data
            end_time_climatology: End time for the climatology data
            extract_region: Region specification, must contain `start_longitude`,
                `end_longitude`, `start_latitude`, `end_latitude`
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_pcrglobwb.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = ('crop_basin', 'preproc_pr', 'preproc_tas',
                         'preproc_pr_clim', 'preproc_tas_clim')

        if dataset is not None:
            recipe.data['diagnostics']['diagnostic_daily'][
                'additional_datasets'] = [DATASETS[dataset]]

        basin = Path(shape).stem
        recipe.data['diagnostics']['diagnostic_daily']['scripts'][
            'script']['basin'] = basin

        if extract_region is None:
            extract_region = get_extents(shape)
        for preproc_name in preproc_names:
            recipe.data['preprocessors'][preproc_name][
                'extract_region'] = extract_region

        variables = recipe.data['diagnostics']['diagnostic_daily']['variables']
        var_names = 'tas', 'pr'

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

        endyear = get_time(end_time).year
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

        var_names_climatology = 'pr_climatology', 'tas_climatology'

        startyear_climatology = get_time(start_time_climatology)
        for var_name in var_names_climatology:
            variables[var_name]['start_year'] = startyear_climatology

        endyear_climatology = get_time(end_time_climatology)
        for var_name in var_names_climatology:
            variables[var_name]['end_year'] = endyear_climatology

        # generate forcing data and retrieve useful information
        recipe_output = recipe.run()
        directory, forcing_files = data_files_from_recipe_output(recipe_output)

        # instantiate forcing object based on generated data
        return PCRGlobWBForcing(directory=directory,
                                start_time=start_time,
                                end_time=end_time,
                                precipitationNC=forcing_files['pr'],
                                temperatureNC=forcing_files['tas'])
