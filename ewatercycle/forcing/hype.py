"""Forcing related functionality for hype"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from esmvalcore.experimental import get_recipe

from .datasets import DATASETS
from .default import DefaultForcing


@dataclass
class HypeForcing(DefaultForcing):
    """Container for hype forcing data."""

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
        shapefile: str = None,
    ) -> 'HypeForcing':
        """Generate HypeForcing with ESMValTool.

        Args:
            dataset: Name of the dataset to use
            startyear: Start year for the forcing data
            endyear: End year for the observation data
            shapefile: Name of the shapefile to use.
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_hype.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = ('preprocessor', 'temperature', 'water')

        if shapefile is not None:
            for preproc_name in preproc_names:
                recipe.data['preprocessors'][preproc_name]['extract_shape'][
                    'shapefile'] = shapefile

        if dataset is not None:
            recipe.data['datasets'] = [DATASETS[dataset]]

        variables = recipe.data['diagnostics']['hype']['variables']
        var_names = 'tas', 'tasmin', 'tasmax', 'pr'

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
        directory = str(Path(forcing_path).parent)

        # instantiate forcing object based on generated data
        return HypeForcing(directory=directory,
                           start_time=str(startyear),
                           end_time=str(endyear))
