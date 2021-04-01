from esmvalcore.experimental import get_recipe
from pathlib import Path

FORCINGS = {
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
    data: dict,
    *,
    forcings: list = None,
    startyear: int = None,
    endyear: int = None,
    shapefile: str = None,
):
    """
    Update hype recipe data in-place.
    
    Parameters
    ----------
    forcings : list
        List of forcings to use
    startyear : int
        Start year for the observation data
    endyear : int
        End year for the observation data
    shapefile : str
        Name of the shapefile to use.
    """
    preproc_names = ('preprocessor', 'temperature', 'water')

    if shapefile is not None:
        for preproc_name in preproc_names:
            data['preprocessors'][preproc_name]['extract_shape'][
                'shapefile'] = shapefile

    if forcings is not None:
        datasets = [FORCINGS[forcing] for forcing in forcings]
        data['datasets'] = datasets

    variables = data['diagnostics']['hype']['variables']
    var_names = 'tas', 'tasmin', 'tasmax', 'pr'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    return data


def update_lisflood(
    data: dict,
    *,
    forcings: list = None,
    startyear: int = None,
    endyear: int = None,
    shapefile: str = None,
    extract_region: dict = None,
):
    """
    Update lisflood recipe data in-place.

    Parameters
    ----------
    forcings : list
        List of forcings to use
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
            data['preprocessors'][preproc_name]['extract_shape'][
                'shapefile'] = shapefile
        data['diagnostics']['diagnostic_daily']['scripts']['script'][
            'catchment'] = basin

    if extract_region is not None:
        for preproc_name in preproc_names:
            data['preprocessors'][preproc_name][
                'extract_region'] = extract_region

    if forcings is not None:
        datasets = [FORCINGS[forcing] for forcing in forcings]
        data['datasets'] = datasets

    variables = data['diagnostics']['diagnostic_daily']['variables']
    var_names = 'pr', 'tas', 'tasmax', 'tasmin', 'tdps', 'uas', 'vas', 'rsds'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    return data


def update_marrmot(
    data: dict,
    *,
    forcings: list = None,
    startyear: int = None,
    endyear: int = None,
    shapefile: str = None,
):
    """
    Update marmott recipe data in-place.

    Parameters
    ----------
    forcings : list
        List of forcings to use
    startyear : int
        Start year for the observation data
    endyear : int
        End year for the observation data
    basin : str
        Name of the basin to use. Defines the shapefile.
    """

    if shapefile is not None:
        basin = Path(shapefile).stem
        data['preprocessors']['daily']['extract_shape'][
            'shapefile'] = shapefile
        data['diagnostics']['diagnostic_daily']['scripts']['script'][
            'basin'] = basin

    if forcings is not None:
        datasets = [FORCINGS[forcing] for forcing in forcings]
        data['diagnostics']['diagnostic_daily'][
            'additional_datasets'] = datasets

    variables = data['diagnostics']['diagnostic_daily']['variables']
    var_names = 'tas', 'pr', 'psl', 'rsds', 'rsdt'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    return data


def update_pcrglobwb(data: dict,
                     *,
                     forcings: list = None,
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
    forcings : list
        List of forcings to use
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

    if forcings is not None:
        datasets = [FORCINGS[forcing] for forcing in forcings]
        data['diagnostics']['diagnostic_daily'][
            'additional_datasets'] = datasets

    if basin is not None:
        data['diagnostics']['diagnostic_daily']['scripts']['script'][
            'basin'] = basin

    if extract_region is not None:
        for preproc_name in preproc_names:
            data['preprocessors'][preproc_name][
                'extract_region'] = extract_region

    variables = data['diagnostics']['diagnostic_daily']['variables']
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

    return data


def update_wflow(
    data: dict,
    *,
    forcings: list = None,
    startyear: int = None,
    endyear: int = None,
    extract_region: dict = None,
    dem_file: str = None,
):
    """
    Update wflow recipe data in-place.

    Parameters
    ----------
    forcings : list
        List of forcings to use
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
        script = data['diagnostics']['wflow_daily']['scripts']['script']
        script['dem_file'] = dem_file
        script['basin'] = Path(dem_file).stem

    if extract_region is not None:
        data['preprocessors']['rough_cutout'][
            'extract_region'] = extract_region

    if forcings is not None:
        datasets = [FORCINGS[forcing] for forcing in forcings]
        data['diagnostics']['wflow_daily']['additional_datasets'] = datasets

    variables = data['diagnostics']['wflow_daily']['variables']
    var_names = 'tas', 'pr', 'psl', 'rsds', 'rsdt'

    if startyear is not None:
        for var_name in var_names:
            variables[var_name]['start_year'] = startyear

    if endyear is not None:
        for var_name in var_names:
            variables[var_name]['end_year'] = endyear

    return data


MODEL_DATA = {
    'hype': {
        'recipe_name': 'hydrology/recipe_hype.yml',
        'update_func': update_hype,
    },
    'lisflood': {
        'recipe_name': 'hydrology/recipe_lisflood.yml',
        'update_func': update_lisflood,
    },
    'marrmot': {
        'recipe_name': 'hydrology/recipe_marrmot.yml',
        'update_func': update_marrmot,
    },
    'pcrglobwb': {
        'recipe_name': 'hydrology/recipe_pcrglobwb.yml',
        'update_func': update_pcrglobwb,
    },
    'wflow': {
        'recipe_name': 'hydrology/recipe_wflow.yml',
        'update_func': update_wflow,
    },
}


def generate(model: str, **kwargs):
    """
    Parameters
    ----------
    model : str
        Name of the model
    **kwargs :
        Model specific parameters
    """
    model_data = MODEL_DATA[model]
    recipe_name = model_data['recipe_name']
    recipe = get_recipe(recipe_name)

    update_func = model_data['update_func']
    update_func(recipe.data, **kwargs)
    recipe.run()
