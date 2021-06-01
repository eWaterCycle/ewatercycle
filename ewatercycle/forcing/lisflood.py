"""Forcing related functionality for lisflood"""

from dataclasses import dataclass
from pathlib import Path

from esmvalcore.experimental import get_recipe

from .datasets import DATASETS
from .default import DefaultForcing
from ..util import get_time, get_extents, data_files_from_recipe_output

GENERATE_DOCS = """
Options:
    extract_region (dict): Region specification, dictionary must contain `start_longitude`,
        `end_longitude`, `start_latitude`, `end_latitude`
"""
LOAD_DOCS = """
Fields:
    PrefixPrecipitation: Path to a NetCDF or pcraster file with precipitation data
    PrefixTavg: Path to a NetCDF or pcraster file with average temperature data
    PrefixE0: Path to a NetCDF or pcraster file with potential evaporation rate from open water surface data
    PrefixES0: Path to a NetCDF or pcraster file with potential evaporation rate from bare soil surface data
    PrefixET0: Path to a NetCDF or pcraster file with potential (reference) evapotranspiration rate data
"""


@dataclass
class LisfloodForcing(DefaultForcing):
    """Container for lisflood forcing data."""

    # Model-specific attributes (preferably with default values):
    PrefixPrecipitation: str = 'pr.nc'
    PrefixTavg: str = 'tas.nc'
    PrefixE0: str = 'e0.nc'
    PrefixES0: str = 'es0.nc'
    PrefixET0: str = 'et0.nc'
    # TODO check whether start/end time are same as in the files

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
            dataset: Name of the source dataset. See :py:data:`.DATASETS`.
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
        directory, forcing_files = data_files_from_recipe_output(recipe_output)

        # TODO run lisvap
        # TODO forcing_files['e0'] = ...

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

    def plot(self):
        raise NotImplementedError('Dont know how to plot')
