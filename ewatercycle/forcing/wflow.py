"""Forcing related functionality for wflow"""

from dataclasses import dataclass
from typing import Optional

from esmvalcore.experimental import get_recipe
from pathlib import Path

from .default import DefaultForcing
from .datasets import DATASETS

@dataclass
class WflowForcing(DefaultForcing):
    """Container for wflow forcing data."""

    # Overwrite (repeat) the defaults so that the docstrings are included.
    directory: str
    """Location where the forcing data is stored."""
    start_time: str
    """Start time of the forcing data"""
    end_time: str
    """End time of the forcing data"""

    # Model-specific attributes (ideally should have defaults):
    netcdfinput: str = "inmaps.nc"
    """Input file path."""
    Precipitation: str = "/pr"
    """Variable name of precipitation data in input file."""
    EvapoTranspiration: str = "/pet"
    """Variable name of evapotranspiration data in input file."""
    Temperature: str = "/tas"
    """Variable name of temperature data in input file."""
    Inflow: Optional[str] = None
    """Variable name of inflow data in input file."""

    @classmethod
    def generate(cls, dataset, startyear, endyear, extract_region=None, dem_file=None) -> 'WflowForcing':
        """Generate WflowForcing data with ESMValTool.

        Args:
            dataset: Name of the source dataset. See :py:data:`.DATASETS`.
            startyear: Start year for the observation data
            endyear: End year for the observation data
            extract_region: Region specification, must contain `start_longitude`,
                `end_longitude`, `start_latitude`, `end_latitude`
            dem_file: Name of the dem_file to use. Also defines the basin param.
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_wflow.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates
        if dem_file is not None:
            script = recipe.data['diagnostics']['wflow_daily']['scripts']['script']
            script['dem_file'] = dem_file
            script['basin'] = Path(dem_file).stem

        if extract_region is not None:
            recipe.data['preprocessors']['rough_cutout'][
                'extract_region'] = extract_region

        if dataset is not None:
            recipe.data['diagnostics']['wflow_daily']['additional_datasets'] = [DATASETS[dataset]]

        variables = recipe.data['diagnostics']['wflow_daily']['variables']
        var_names = 'tas', 'pr', 'psl', 'rsds', 'rsdt'

        if startyear is not None:
            for var_name in var_names:
                variables[var_name]['start_year'] = startyear

        if endyear is not None:
            for var_name in var_names:
                variables[var_name]['end_year'] = endyear

        # generate forcing data and retreive useful information
        recipe_output = recipe.run()
        forcing_path = list(recipe_output['wflow_daily/script']).data_files[0]

        forcing_file = Path(forcing_path).name
        directory = Path(forcing_path).dir

        # instantiate forcing object based on generated data
        return WflowForcing(directory=directory, start_time=startyear, end_time=endyear, netcdfinput=forcing_file)
