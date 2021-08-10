"""Forcing related functionality for wflow"""
from pathlib import Path
from typing import Dict, Optional

from esmvalcore.experimental import get_recipe

from ..util import get_extents, get_time, to_absolute_path
from ._default import DefaultForcing
from .datasets import DATASETS


class WflowForcing(DefaultForcing):
    """Container for wflow forcing data."""
    def __init__(
        self,
        start_time: str,
        end_time: str,
        directory: str,
        shape: Optional[str] = None,
        netcdfinput: str = "inmaps.nc",
        Precipitation: str = "/pr",
        EvapoTranspiration: str = "/pet",
        Temperature: str = "/tas",
        Inflow: Optional[str] = None,
    ):
        """
            netcdfinput (str) = "inmaps.nc": Path to forcing file."
            Precipitation (str) = "/pr": Variable name of precipitation data in
                input file.
            EvapoTranspiration (str) = "/pet": Variable name of
                evapotranspiration data in input file.
            Temperature (str) = "/tas": Variable name of temperature data in
                input file.
            Inflow (str) = None: Variable name of inflow data in input file.
        """
        super().__init__(start_time, end_time, directory, shape)
        self.netcdfinput = netcdfinput
        self.Precipitation = Precipitation
        self.EvapoTranspiration = EvapoTranspiration
        self.Temperature = Temperature
        self.Inflow = Inflow

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        dem_file: str,
        extract_region: Dict[str, float] = None,
    ) -> 'WflowForcing':
        """
            dem_file (str): Name of the dem_file to use. Also defines the basin
                param.
            extract_region (dict): Region specification, dictionary must
                contain `start_longitude`, `end_longitude`, `start_latitude`,
                `end_latitude`
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_wflow.yml"
        recipe = get_recipe(recipe_name)

        basin = to_absolute_path(shape).stem
        recipe.data['diagnostics']['wflow_daily']['scripts']['script'][
            'basin'] = basin

        # model-specific updates
        script = recipe.data['diagnostics']['wflow_daily']['scripts']['script']
        script['dem_file'] = dem_file

        if extract_region is None:
            extract_region = get_extents(shape)
        recipe.data['preprocessors']['rough_cutout'][
            'extract_region'] = extract_region

        recipe.data['diagnostics']['wflow_daily']['additional_datasets'] = [
            DATASETS[dataset]
        ]

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

        forcing_file = forcing_data.path
        directory = str(forcing_file.parent)

        # instantiate forcing object based on generated data
        return WflowForcing(directory=directory,
                            start_time=start_time,
                            end_time=end_time,
                            shape=shape,
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
