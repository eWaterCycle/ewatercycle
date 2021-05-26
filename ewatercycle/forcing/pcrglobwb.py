"""Forcing related functionality for pcrglobwb"""

from dataclasses import dataclass
from typing import Optional

from esmvalcore.experimental import get_recipe
from pathlib import Path

from .default import DefaultForcing
from .datasets import DATASETS


@dataclass
class PCRGlobWBForcing(DefaultForcing):
    """Container for pcrglobwb forcing data.

    Attributes
        directory: Location where the forcing data is stored
        start_time: Start time of the forcing data
        end_time: End time of the forcing data

    """
    @classmethod
    def generate(dataset, startyear, endyear, extract_region=None, dem_file=None):
        """Generate WflowForcing data with ESMValTool.

        Attributes:
            dataset: Name of the dataset to use
            basin: Name of the basin (used for data output filename only)
            startyear: Start year for the observation data
            endyear: End year for the observation data
            startyear_climatology: Start year for the climatology data
            endyear_climatology: End year for the climatology data
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
            recipe_dict['diagnostics']['diagnostic_daily'][
                'additional_datasets'] = [DATASETS[dataset]]

        if basin is not None:
            recipe_dict['diagnostics']['diagnostic_daily']['scripts']['script'][
                'basin'] = basin

        if extract_region is not None:
            for preproc_name in preproc_names:
                recipe_dict['preprocessors'][preproc_name][
                    'extract_region'] = extract_region

        variables = recipe_dict['diagnostics']['diagnostic_daily']['variables']
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
        directory = Path(forcing_path).dir

        # instantiate forcing object based on generated data
        return PCRGlobWBForcing(directory=directory, start_time=startyear, end_time=endyear, netcdfinput=forcing_file)
