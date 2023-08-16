from typing import Dict, Tuple

from esmvalcore.experimental.recipe_output import RecipeOutput


def data_files_from_recipe_output(
    recipe_output: RecipeOutput,
) -> Tuple[str, Dict[str, str]]:
    """Get data files from a ESMVaLTool recipe output

    Expects first diagnostic task to produce files with single var each.

    Args:
        recipe_output: ESMVaLTool recipe output

    Returns:
        Tuple with directory of files and a
        dict where key is cmor short name and value is relative path to NetCDF file
    """
    data_files = list(recipe_output.values())[0].data_files
    forcing_files = {}
    for data_file in data_files:
        dataset = data_file.load_xarray()
        var_name = list(dataset.data_vars.keys())[0]
        dataset.close()
        forcing_files[var_name] = data_file.path.name
    # TODO simplify (recipe_output.location) when next esmvalcore release is made
    directory = str(data_files[0].path.parent)
    return directory, forcing_files


def parse_recipe_output(recipe_output):
    """Parse ESMValTool recipe output into a dictionary.

    Returns:
        Dictionary with forcing data variables as keys and file names as values
        and a key called directory with is the parent directory of the file names.
    """
    directory, variables = data_files_from_recipe_output(recipe_output)
    # Mold ESMValTool output into the format needed for GenericDistributedForcing
    return {"directory": directory, **variables}
