"""Forcing related functionality for marrmot"""

from pathlib import Path
from typing import Optional

from esmvalcore.experimental import get_recipe

from ..util import get_time, to_absolute_path
from ._default import DefaultForcing
from .datasets import DATASETS


class MarrmotForcing(DefaultForcing):
    """Container for marrmot forcing data."""
    def __init__(
        self,
        start_time: str,
        end_time: str,
        directory: str,
        shape: Optional[str] = None,
        forcing_file: Optional[str] = 'marrmot.mat',
    ):
        """
            forcing_file: Matlab file that contains forcings for Marrmot
                models. See format forcing file in `model implementation
                <https://github.com/wknoben/MARRMoT/blob/8f7e80979c2bef941c50f2fb19ce4998e7b273b0/BMI/lib/marrmotBMI_oct.m#L15-L19>`_.
        """
        super().__init__(start_time, end_time, directory, shape)
        self.forcing_file = forcing_file

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
    ) -> 'MarrmotForcing':
        """
            None: Marrmot does not have model-specific generate options.
        """

        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_marrmot.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        basin = to_absolute_path(shape).stem
        recipe.data['preprocessors']['daily']['extract_shape'][
            'shapefile'] = shape
        recipe.data['diagnostics']['diagnostic_daily']['scripts']['script'][
            'basin'] = basin

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

        # generate forcing data and retrieve useful information
        recipe_output = recipe.run()
        forcing_file: Path = list(recipe_output.values())[0].files[0].path

        directory = str(Path(forcing_file).parent)

        # instantiate forcing object based on generated data
        return MarrmotForcing(directory=directory,
                              start_time=start_time,
                              end_time=end_time,
                              shape=shape,
                              forcing_file=forcing_file.name)

    def plot(self):
        raise NotImplementedError('Dont know how to plot')
