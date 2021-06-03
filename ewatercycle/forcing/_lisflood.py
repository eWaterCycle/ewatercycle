"""Forcing related functionality for lisflood"""

from pathlib import Path
from typing import Optional

from esmvalcore.experimental import get_recipe

from ..util import data_files_from_recipe_output, get_extents, get_time
from ._default import DefaultForcing
from .datasets import DATASETS


class LisfloodForcing(DefaultForcing):
    """Container for lisflood forcing data."""

    # TODO check whether start/end time are same as in the files
    def __init__(
        self,
        start_time: str,
        end_time: str,
        directory: str,
        shape: str,
        PrefixPrecipitation: Optional[str] = 'pr.nc',
        PrefixTavg: Optional[str] = 'tas.nc',
        PrefixE0: Optional[str] = 'e0.nc',
        PrefixES0: Optional[str] = 'es0.nc',
        PrefixET0: Optional[str] = 'et0.nc',
    ):
        """
            PrefixPrecipitation: Path to a NetCDF or pcraster file with precipitation data
            PrefixTavg: Path to a NetCDF or pcraster file with average temperature data
            PrefixE0: Path to a NetCDF or pcraster file with potential evaporation rate from open water surface data
            PrefixES0: Path to a NetCDF or pcraster file with potential evaporation rate from bare soil surface data
            PrefixET0: Path to a NetCDF or pcraster file with potential (reference) evapotranspiration rate data
        """
        super().__init(start_time, end_time, directory, shape)
        self.PrefixPrecipitation = PrefixPrecipitation
        self.PrefixTavg = PrefixTavg
        self.PrefixE0 = PrefixE0
        self.PrefixES0 = PrefixES0
        self.PrefixET0 = PrefixET0

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        extract_region: dict = None,
    ) -> 'LisfloodForcing':
        """
            extract_region (dict): Region specification, dictionary must contain `start_longitude`,
                `end_longitude`, `start_latitude`, `end_latitude`
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
        recipe.data['diagnostics']['diagnostic_daily']['scripts']['script'][
            'catchment'] = basin

        if extract_region is None:
            extract_region = get_extents(shape)
        for preproc_name in preproc_names:
            recipe.data['preprocessors'][preproc_name][
                'extract_region'] = extract_region

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
        return LisfloodForcing(
            directory=directory,
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
