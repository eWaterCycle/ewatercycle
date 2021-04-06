from pathlib import Path
from typing import Callable
from esmvalcore.experimental import get_recipe


DATASETS = {
    'ERA5': {
        'dataset': 'ERA5',
        'project': 'OBS6',
        'tier': 3,
        'type': 'reanaly',
        'version': 1
    },
    'ERA-Interim': {
        'dataset': 'ERA-Interim',
        'project': 'OBS6',
        'tier': 3,
        'type': 'reanaly',
        'version': 1
    },
}


def update_hype(
    recipe_dict: dict,
    *,
    dataset: str = None,
    startyear: int = None,
    endyear: int = None,
    shapefile: str = None,
):
    """
    Update hype recipe data in-place.

    Parameters
    ----------
    recipe_dict : dict
        Dictionary with the recipe data
    dataset : str
        Name of the dataset to use
    startyear : int
        Start year for the forcing data
    endyear : int
        End year for the observation data
    shapefile : str
        Name of the shapefile to use.
    """
    preproc_names = ('preprocessor', 'temperature', 'water')

    if shapefile is not None:
        for preproc_name in preproc_names:
            recipe_dict['preprocessors'][preproc_name]['extract_shape'][
                'shapefile'] = shapefile

    if dataset is not None:
        recipe_dict['datasets'] = [DATASETS[dataset]]

    variables = recipe_dict['diagnostics']['hype']['variables']
    var_names = 'tas', 'tasmin', 'tasmax', 'pr'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    return recipe_dict


def update_lisflood(
    recipe_dict: dict,
    *,
    dataset: str = None,
    startyear: int = None,
    endyear: int = None,
    shapefile: str = None,
    extract_region: dict = None,
):
    """
    Update lisflood recipe data in-place.

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
    basin : str
        Name of the basin to use. Defines the shapefile.
    extract_region : dict
        Region specification, must contain `start_longitude`,
        `end_longitude`, `start_latitude`, `end_latitude`
    """
    preproc_names = ('general', 'daily_water', 'daily_temperature',
                     'daily_radiation', 'daily_windspeed')

    if shapefile is not None:
        basin = Path(shapefile).stem
        for preproc_name in preproc_names:
            recipe_dict['preprocessors'][preproc_name]['extract_shape'][
                'shapefile'] = shapefile
        recipe_dict['diagnostics']['diagnostic_daily']['scripts']['script'][
            'catchment'] = basin

    if extract_region is not None:
        for preproc_name in preproc_names:
            recipe_dict['preprocessors'][preproc_name][
                'extract_region'] = extract_region

    if dataset is not None:
        recipe_dict['datasets'] = [DATASETS[dataset]]

    variables = recipe_dict['diagnostics']['diagnostic_daily']['variables']
    var_names = 'pr', 'tas', 'tasmax', 'tasmin', 'tdps', 'uas', 'vas', 'rsds'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    return recipe_dict


def update_marrmot(
    recipe_dict: dict,
    *,
    dataset: str = None,
    startyear: int = None,
    endyear: int = None,
    shapefile: str = None,
):
    """
    Update marmott recipe data in-place.

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
    basin : str
        Name of the basin to use. Defines the shapefile.
    """

    if shapefile is not None:
        basin = Path(shapefile).stem
        recipe_dict['preprocessors']['daily']['extract_shape'][
            'shapefile'] = shapefile
        recipe_dict['diagnostics']['diagnostic_daily']['scripts']['script'][
            'basin'] = basin

    if dataset is not None:
        recipe_dict['diagnostics']['diagnostic_daily'][
            'additional_datasets'] = [DATASETS[dataset]]

    variables = recipe_dict['diagnostics']['diagnostic_daily']['variables']
    var_names = 'tas', 'pr', 'psl', 'rsds', 'rsdt'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    return recipe_dict


def update_pcrglobwb(recipe_dict: dict,
                     *,
                     dataset: str = None,
                     basin: str = None,
                     startyear: int = None,
                     endyear: int = None,
                     startyear_climatology: int = None,
                     endyear_climatology: int = None,
                     extract_region: dict = None):
    """
    Update pcrglobwb recipe data in-place.

    Parameters
    ----------
    recipe_dict : dict
        Dictionary with the recipe data
    dataset : str
        Name of the dataset to use
    basin : str
        Name of the basin (used for data output filename only)
    startyear : int
        Start year for the observation data
    endyear : int
        End year for the observation data
    startyear_climatology : int
        Start year for the climatology data
    endyear_climatology : int
        End year for the climatology data
    extract_region : dict
        Region specification, must contain `start_longitude`,
        `end_longitude`, `start_latitude`, `end_latitude`
    """
    preproc_names = ('crop_basin', 'preproc_pr', 'preproc_tas',
                     'preproc_pr_clim', 'preproc_tas_clim')

    if dataset is not None:
        recipe_dict['diagnostics']['diagnostic_daily'][
            'additional_datasets'] = [DATASETS[dataset]]

    if basin is not None:
        recipe_dict['diagnostics']['diagnostic_daily']['scripts']['script'][
            'basin'] = basin

    if extract_region is not None:
        for preproc_name in preproc_names:
            recipe_dict['preprocessors'][preproc_name][
                'extract_region'] = extract_region

    variables = recipe_dict['diagnostics']['diagnostic_daily']['variables']
    var_names = 'tas', 'pr'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    var_names_climatology = 'pr_climatology', 'tas_climatology'

    if startyear_climatology is not None:
        for var_name in var_names_climatology:
            variables[var_name]['start_year'] = startyear_climatology

    if endyear_climatology is not None:
        for var_name in var_names_climatology:
            variables[var_name]['end_year'] = endyear_climatology

    return recipe_dict


def update_wflow(
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
            DATASETS[dataset]]

    variables = recipe_dict['diagnostics']['wflow_daily']['variables']
    var_names = 'tas', 'pr', 'psl', 'rsds', 'rsdt'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    return recipe_dict


class RecipeGenerator:
    def __init__(self, model: str, update_func: Callable, recipe_name: str):
        self.recipe_name = recipe_name
        self.update_func = update_func
        self.model = model
        self.recipe = get_recipe(recipe_name)

    def __call__(self, **kwargs):
        """Return recipe updated with new keyword arguments."""
        # update recipe in-place
        self.update_func(self.recipe.data, **kwargs)
        return self.recipe

    def __repr__(self):
        """Return canonical class representation."""
        return (f'{self.__class__.__name__}(model={self.model!r}, '
                f'update_func={self.update_func!r}, '
                f'recipe_name={self.recipe_name!r})')


MODELS = {
    'hype': RecipeGenerator(model='hype', update_func=update_hype, recipe_name='hydrology/recipe_hype.yml'),
    'lisflood': RecipeGenerator(model='lisflood', update_func=update_lisflood, recipe_name='hydrology/recipe_lisflood.yml'),
    'marrmot': RecipeGenerator(model='marrmot', update_func=update_marrmot, recipe_name='hydrology/recipe_marrmot.yml'),
    'pcrglobwb': RecipeGenerator(model='pcrglobwb', update_func=update_pcrglobwb, recipe_name='hydrology/recipe_pcrglobwb.yml'),
    'wflow': RecipeGenerator(model='wflow', update_func=update_wflow, recipe_name='hydrology/recipe_wflow.yml')
}
