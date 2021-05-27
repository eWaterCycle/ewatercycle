"""Forcing related functionality for pcrglobwb"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from esmvalcore.experimental import get_recipe

from .datasets import DATASETS
from .default import DefaultForcing


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
    # ...

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str = None,
        startyear: int = None,
        endyear: int = None,
        startyear_climatology: int = None,
        endyear_climatology: int = None,
        basin: str = None,
        extract_region: dict = None,
    ) -> 'PCRGlobWBForcing':
        """Generate WflowForcing data with ESMValTool.

        Attributes:
            dataset: Name of the dataset to use
            startyear: Start year for the observation data
            endyear: End year for the observation data
            startyear_climatology: Start year for the climatology data
            endyear_climatology: End year for the climatology data
            basin: Name of the basin (used for data output filename only)
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

        if basin is not None:
            recipe.data['diagnostics']['diagnostic_daily']['scripts'][
                'script']['basin'] = basin

        if extract_region is not None:
            for preproc_name in preproc_names:
                recipe.data['preprocessors'][preproc_name][
                    'extract_region'] = extract_region

        variables = recipe.data['diagnostics']['diagnostic_daily']['variables']
        var_names = 'tas', 'pr'

        if startyear is not None:
            for var_name in var_names:
                variables[var_name]['start_year'] = startyear

        if endyear is not None:
            for var_name in var_names:
                variables[var_name]['end_year'] = endyear

        var_names_climatology = 'pr_climatology', 'tas_climatology'

        if startyear_climatology is not None:
            for var_name in var_names_climatology:
                variables[var_name]['start_year'] = startyear_climatology

        if endyear_climatology is not None:
            for var_name in var_names_climatology:
                variables[var_name]['end_year'] = endyear_climatology

        # generate forcing data and retreive useful information
        recipe_output = recipe.run()
        forcing_path = list(recipe_output['............']).data_files[0]

        forcing_file = Path(forcing_path).name
        directory = str(Path(forcing_path).parent)

        # instantiate forcing object based on generated data
        return PCRGlobWBForcing(directory=directory,
                                start_time=str(startyear),
                                end_time=str(endyear))
