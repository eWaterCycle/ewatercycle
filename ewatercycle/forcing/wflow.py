"""Forcing related functionality for wflow"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from esmvalcore.experimental import get_recipe

from .datasets import DATASETS
from .default import DefaultForcing
from ..util import get_time, get_extents

GENERATE_DOCS = """
Options:
    dem_file (str): Name of the dem_file to use. Also defines the basin param.
    extract_region (dict): Region specification, dictionary must contain `start_longitude`,
        `end_longitude`, `start_latitude`, `end_latitude`
"""
LOAD_DOCS = """
Fields:
    netcdfinput (str): Path to forcing file. Default is "inmaps.nc"
    Precipitation (str): Variable name of precipitation data in input file. Default is "/pr".
    EvapoTranspiration (str): Variable name of evapotranspiration data in input file. Default is"/pet".
    Temperature (str): Variable name of temperature data in input file. Default is "/tas".
    Inflow Optional[str]: Variable name of inflow data in input file.
"""

class PathParser:
    """Descriptor that converts input to pathlib.Path objects."""
    def __init__(self, default_value):
        self.default_value = default_value

    def __set_name__(self, owner: object, name: str):
        self.name = name

    def __set__(self, instance: object, value: Optional[str] = None):
        value = value if value is not None else self.default_value
        instance.__dict__[self.name] = Path(value).expanduser().resolve()


@dataclass
class WflowForcing(DefaultForcing):
    """Container for wflow forcing data."""

    # Model-specific attributes (ideally should have defaults):
    netcdfinput: str = PathParser(default_value='inmaps.nc')
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
    def generate(
        cls,  # type: ignore
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        dem_file: str,
        extract_region: Optional[str] = None,
    ) -> 'WflowForcing':
        """Generate WflowForcing data with ESMValTool.

        Args:
            dataset: Name of the source dataset. See :py:data:`.DATASETS`.
            start_time: Start time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: End time of forcing in UTC and ISO format string e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
            shape: Path to a shape file. Used for spatial selection.
            extract_region: Region specification, must contain `start_longitude`,
                `end_longitude`, `start_latitude`, `end_latitude`
            dem_file: Name of the dem_file to use. Also defines the basin param.
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_wflow.yml"
        recipe = get_recipe(recipe_name)

        basin = Path(shape).stem
        recipe.data['diagnostics']['wflow_daily']['scripts'][
            'script']['basin'] = basin

        # model-specific updates
        script = recipe.data['diagnostics']['wflow_daily']['scripts'][
            'script']
        script['dem_file'] = dem_file

        if extract_region is None:
            extract_region = get_extents(shape)
        recipe.data['preprocessors']['rough_cutout'][
            'extract_region'] = extract_region

        recipe.data['diagnostics']['wflow_daily'][
            'additional_datasets'] = [DATASETS[dataset]]

        variables = recipe.data['diagnostics']['wflow_daily']['variables']
        var_names = 'tas', 'pr', 'psl', 'rsds', 'rsdt'

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

        endyear = get_time(end_time).year
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

        # generate forcing data and retreive useful information
        recipe_output = recipe.run()
        forcing_data = recipe_output['wflow_daily/script'].data_files[0]

        forcing_file = forcing_data.filename
        directory = str(forcing_file.parent)

        # instantiate forcing object based on generated data
        return WflowForcing(directory=directory,
                            start_time=start_time,
                            end_time=end_time,
                            netcdfinput=forcing_file.name)

    def __str__(self):
        """Nice formatting of the forcing data object."""
        return "\n".join([
            "Forcing data for Wflow",
            "----------------------",
            f"Directory: {self.directory}",
            f"Start time: {self.start_time}",
            f"End time: {self.end_time}",
            f"Shapefile: {self.shape}",
            f"Additional information for model config:",
            f"  - netcdfinput: {self.netcdfinput}",
            f"  - Precipitation: {self.Precipitation}",
            f"  - Temperature: {self.Temperature}",
            f"  - EvapoTranspiration: {self.EvapoTranspiration}",
            f"  - Inflow: {self.Inflow}",
        ])

    def plot(self):
        raise NotImplementedError('Dont know how to plot')
