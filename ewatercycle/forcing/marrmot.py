"""Forcing related functionality for marrmot"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from esmvalcore.experimental import get_recipe

from .datasets import DATASETS
from .default import DefaultForcing


@dataclass
class MarrmotForcing(DefaultForcing):
    """Container for marrmot forcing data."""

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
    ) -> 'MarrmotForcing':
        """Generate MarrmotForcing data with ESMValTool.

        Args:
            dataset: Name of the dataset to use
            startyear: Start year for the observation data
            endyear: End year for the observation data
            basin: Name of the basin to use. Defines the shapefile.
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_marrmot.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        if shapefile is not None:
            basin = Path(shapefile).stem
            recipe.data['preprocessors']['daily']['extract_shape'][
                'shapefile'] = shapefile
            recipe.data['diagnostics']['diagnostic_daily']['scripts'][
                'script']['basin'] = basin

        if dataset is not None:
            recipe.data['diagnostics']['diagnostic_daily'][
                'additional_datasets'] = [DATASETS[dataset]]

        variables = recipe.data['diagnostics']['diagnostic_daily']['variables']
        var_names = 'tas', 'pr', 'psl', 'rsds', 'rsdt'

        if startyear is not None:
            for var_name in var_names:
                variables[var_name]['start_year'] = startyear

        if endyear is not None:
            for var_name in var_names:
                variables[var_name]['end_year'] = endyear

        # generate forcing data and retreive useful information
        recipe_output = recipe.run()
        forcing_path = list(recipe_output['.............']).data_files[0]

        forcing_file = Path(forcing_path).name
        directory = str(Path(forcing_path).parent)

        # instantiate forcing object based on generated data
        return MarrmotForcing(directory=directory,
                              start_time=str(startyear),
                              end_time=str(endyear))
