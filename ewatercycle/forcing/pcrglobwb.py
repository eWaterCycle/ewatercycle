"""Forcing related functionality for pcrglobwb"""

def update_recipe(recipe_dict: dict,
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
