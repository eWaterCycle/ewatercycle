"""Forcing related functionality for marrmot"""


def update_recipe(
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
