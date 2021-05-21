"""Forcing related functionality for wflow"""

from dataclasses import dataclass
from typing import Optional

from .default import DefaultForcing


@dataclass
class WflowForcing(DefaultForcing):
    """Forcing container for forcing data extended with wflow-specific options.

    Model-specific options:
        netcdfinput (str): Input file path.
        Precipitation (str): Variable name of precipitation data in input file.
        EvapoTranspiration (str): Variable name of evapotranspiration data in input file.
        Temperature (str): Variable name of temperature data in input file.
        Inflow (str): Variable name of inflow data in input file.
    """
    # Note: these will be added AFTER the parameters in DefaultForcing.
    netcdfinput: str = "inmaps.nc"
    Precipitation: str = "/pr"
    EvapoTranspiration: str = "/pet"
    Temperature: str = "/tas"
    Inflow: Optional[str] = None

    @classmethod
    def from_recipe(recipe_output):
        """Set model-specific config options based on ESMValTool output."""
        forcing_file = list(
            wflow_output.recipe_output['wflow_daily/script']).data_files[0]
        return WflowForcingConfig(netcdfinput=forcing_file.path, recipe=...)


def update_recipe(
    recipe_dict: dict,
    *,
    dataset: str = None,
    startyear: int = None,
    endyear: int = None,
    extract_region: dict = None,
    dem_file: str = None,
):
    """
    Update wflow recipe data in-place.

    Parameters
    ----------
    recipe_dict : dict
        Dictionary with the recipe data
    dataset : str
        Name of the dataset to use
    startyear : int
        Start year for the observation data
    endyear : int
        End year for the observation data
    extract_region : dict
        Region specification, must contain `start_longitude`,
        `end_longitude`, `start_latitude`, `end_latitude`
    dem_file : str
        Name of the dem_file to use. Also defines the basin param.
    """
    if dem_file is not None:
        script = recipe_dict['diagnostics']['wflow_daily']['scripts']['script']
        script['dem_file'] = dem_file
        script['basin'] = Path(dem_file).stem

    if extract_region is not None:
        recipe_dict['preprocessors']['rough_cutout'][
            'extract_region'] = extract_region

    if dataset is not None:
        recipe_dict['diagnostics']['wflow_daily']['additional_datasets'] = [
            DATASETS[dataset]
        ]

    variables = recipe_dict['diagnostics']['wflow_daily']['variables']
    var_names = 'tas', 'pr', 'psl', 'rsds', 'rsdt'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    return recipe_dict
