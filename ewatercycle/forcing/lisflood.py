"""Forcing related functionality for lisflood"""

from dataclasses import dataclass
from typing import Optional

from esmvalcore.experimental import get_recipe
from pathlib import Path

from .default import DefaultForcing
from .datasets import DATASETS

@dataclass
class LisfloodForcing(DefaultForcing):
    """Container for lisflood forcing data."""

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
    def generate(
        cls,
        dataset: str = None,
        startyear: int = None,
        endyear: int = None,
        shapefile: str = None,
        extract_region: dict = None,
    ) -> 'LisfloodForcing':
        """Generate LisfloodForcing with ESMValTool.

        Args:
            dataset: Name of the dataset to use
            startyear: Start year for the observation data
            endyear: End year for the observation data
            basin: Name of the basin to use. Defines the shapefile.
            extract_region: Region specification, must contain `start_longitude`,
                `end_longitude`, `start_latitude`, `end_latitude`
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_hype.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = ('general', 'daily_water', 'daily_temperature',
                        'daily_radiation', 'daily_windspeed')

        if shapefile is not None:
            basin = Path(shapefile).stem
            for preproc_name in preproc_names:
                recipe_dict['preprocessors'][preproc_name]['extract_shape'][
                    'shapefile'] = shapefile
            recipe_dict['diagnostics']['diagnostic_daily']['scripts']['script'][
                'catchment'] = basin

        if extract_region is not None:
            for preproc_name in preproc_names:
                recipe_dict['preprocessors'][preproc_name][
                    'extract_region'] = extract_region

        if dataset is not None:
            recipe_dict['datasets'] = [DATASETS[dataset]]

        variables = recipe_dict['diagnostics']['diagnostic_daily']['variables']
        var_names = 'pr', 'tas', 'tasmax', 'tasmin', 'tdps', 'uas', 'vas', 'rsds'

        if startyear is not None:
            for var_name in var_names:
                variables[var_name]['start_year'] = startyear

        if endyear is not None:
            for var_name in var_names:
                variables[var_name]['end_year'] = endyear

        # generate forcing data and retreive useful information
        recipe_output = recipe.run()
        forcing_path = list(recipe_output['...........']).data_files[0]

        forcing_file = Path(forcing_path).name
        directory = Path(forcing_path).dir

        # instantiate forcing object based on generated data
        return LisfloodForcing(directory=directory, start_time=startyear, end_time=endyear)
