"""Forcing related functionality for hype"""

from pathlib import Path
from typing import Optional

from esmvalcore.experimental import get_recipe

from ..util import get_time, to_absolute_path
from ._default import DefaultForcing
from .datasets import DATASETS


class HypeForcing(DefaultForcing):
    """Container for hype forcing data."""
    def __init__(
        self,
        start_time: str,
        end_time: str,
        directory: str,
        shape: Optional[str] = None,
    ):
        """
            None: Hype does not have model-specific load options.
        """
        super().__init__(start_time, end_time, directory, shape)

    @classmethod
    def generate(  # type: ignore
            cls, dataset: str, start_time: str, end_time: str,
            shape: str) -> 'HypeForcing':
        """
            None: Hype does not have model-specific generate options.
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_hype.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = ('preprocessor', 'temperature', 'water')

        for preproc_name in preproc_names:
            recipe.data['preprocessors'][preproc_name]['extract_shape'][
                'shapefile'] = to_absolute_path(shape)

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
        # TODO return files created by ESMValTOOL which are needed by Hype Model
        # forcing_path = list(recipe_output['...........']).data_files[0]
        forcing_path = '/foobar.txt'

        forcing_file = Path(forcing_path).name
        directory = str(Path(forcing_file).parent)

        # instantiate forcing object based on generated data
        return HypeForcing(directory=directory,
                           start_time=str(startyear),
                           end_time=str(endyear),
                           shape=shape)

    def plot(self):
        raise NotImplementedError('Dont know how to plot')
