"""Forcing related functionality for marrmot"""

from dataclasses import dataclass
from pathlib import Path

from esmvalcore.experimental import get_recipe

from .datasets import DATASETS
from .default import DefaultForcing
from ..util import get_time

GENERATE_DOCS = """Marrmot does not have model specific options."""
LOAD_DOCS = """
Fields:
    forcing_file: Matlab file that contains forcings for Marrmot models. See format forcing file in `model implementation <https://github.com/wknoben/MARRMoT/blob/8f7e80979c2bef941c50f2fb19ce4998e7b273b0/BMI/lib/marrmotBMI_oct.m#L15-L19>`_.
"""


@dataclass
class MarrmotForcing(DefaultForcing):
    """Container for marrmot forcing data."""

    # Model-specific attributes (preferably with default values):
    forcing_file: str = 'marrmot.mat'

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
    ) -> 'MarrmotForcing':
        """Generate Marrmot forcing data with ESMValTool.

        Args:
            dataset: Name of the source dataset. See :py:data:`.DATASETS`.
            start_time: Start time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: End time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            shape: Path to a shape file. Used for spatial selection.
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_marrmot.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        basin = Path(shape).stem
        recipe.data['preprocessors']['daily']['extract_shape'][
            'shapefile'] = shape
        recipe.data['diagnostics']['diagnostic_daily']['scripts'][
            'script']['basin'] = basin

        recipe.data['diagnostics']['diagnostic_daily'][
            'additional_datasets'] = [DATASETS[dataset]]

        variables = recipe.data['diagnostics']['diagnostic_daily']['variables']
        var_names = 'tas', 'pr', 'psl', 'rsds', 'rsdt'

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

        endyear = get_time(end_time).year
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

        # generate forcing data and retreive useful information
        recipe_output = recipe.run()
        forcing_file = list(recipe_output.values())[0].files[0].filename

        directory = str(Path(forcing_file).parent)

        # instantiate forcing object based on generated data
        return MarrmotForcing(directory=directory,
                              start_time=str(startyear),
                              end_time=str(endyear),
                              forcing_file=forcing_file)

    def plot(self):
        raise NotImplementedError('Dont know how to plot')
