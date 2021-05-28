"""Forcing related functionality for hype"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from esmvalcore.experimental import get_recipe

from .datasets import DATASETS
from .default import DefaultForcing
from ..util import get_time

GENERATE_DOCS = """Hype does not have model specific options."""


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
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str
    ) -> 'HypeForcing':
        """Generate HypeForcing with ESMValTool.

        Args:
            dataset: Name of the dataset to use
            start_time: Start time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: End time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            shape: Path to a shape file. Used for spatial selection.
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_hype.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = ('preprocessor', 'temperature', 'water')

        for preproc_name in preproc_names:
            recipe.data['preprocessors'][preproc_name]['extract_shape'][
                'shapefile'] = shape

        recipe.data['datasets'] = [DATASETS[dataset]]

        variables = recipe.data['diagnostics']['hype']['variables']
        var_names = 'tas', 'tasmin', 'tasmax', 'pr'

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

        endyear = get_time(end_time).year
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
