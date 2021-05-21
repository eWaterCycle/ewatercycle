"""Forcing related functionality for hype"""

def update_recipe(
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
