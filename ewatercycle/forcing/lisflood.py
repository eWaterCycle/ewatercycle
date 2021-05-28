"""Forcing related functionality for lisflood"""

from dataclasses import dataclass
from pathlib import Path

from esmvalcore.experimental import get_recipe

from .datasets import DATASETS
from .default import DefaultForcing
from ..util import get_time, get_extents


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
    PrefixPrecipitation: str
    """"""
    PrefixTavg: str
    """"""
    PrefixE0: str
    PrefixES0: str
    PrefixET0: str

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        extract_region: dict = None,
    ) -> 'LisfloodForcing':
        """Generate LisfloodForcing with ESMValTool.

        Args:
            dataset: Name of the dataset to use
            start_time: Start time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: End time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            shape: Path to a shape file. Used for spatial selection.
            extract_region: Region specification, must contain `start_longitude`,
                `end_longitude`, `start_latitude`, `end_latitude`

            TODO add regrid options so forcing can be generated for parameter set
            TODO that is not on a 0.1x0.1 grid
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_hype.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = ('general', 'daily_water', 'daily_temperature',
                         'daily_radiation', 'daily_windspeed')

        basin = Path(shape).stem
        for preproc_name in preproc_names:
            recipe.data['preprocessors'][preproc_name]['extract_shape'][
                'shapefile'] = shape
        recipe.data['diagnostics']['diagnostic_daily']['scripts'][
            'script']['catchment'] = basin

        if extract_region is None:
            extract_region = get_extents(shape)
        for preproc_name in preproc_names:
            recipe.data['preprocessors'][preproc_name]['extract_region'] = extract_region

        recipe.data['datasets'] = [DATASETS[dataset]]

        variables = recipe.data['diagnostics']['diagnostic_daily']['variables']
        var_names = 'pr', 'tas', 'tasmax', 'tasmin', 'tdps', 'uas', 'vas', 'rsds'

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

        endyear = get_time(end_time).year
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

        # generate forcing data and retrieve useful information
        recipe_output = recipe.run()

        # TODO run lisvap

        data_files = list(recipe_output.values())[0].data_files
        forcing_files = {}
        for data_file in data_files:
            dataset = data_file.load_xarray()
            var_name = list(dataset.data_vars.keys())[0]
            forcing_files[var_name] = data_file.filename.name

        # TODO simplify (recipe_output.location) when next esmvalcore release is made
        directory = str(Path(data_files[0]).parent)

        # instantiate forcing object based on generated data
        return LisfloodForcing(directory=directory,
                               start_time=str(startyear),
                               end_time=str(endyear),
                               PrefixPrecipitation=forcing_files["pr"],
                               PrefixTavg=forcing_files["tas"],
                               PrefixE0=forcing_files['e0'],
                               PrefixES0=forcing_files['es0'],
                               PrefixET0=forcing_files['et0'],
                               )
