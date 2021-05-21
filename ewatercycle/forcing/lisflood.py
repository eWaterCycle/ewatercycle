"""Forcing related functionality for lisflood"""

def update_recipe(
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
