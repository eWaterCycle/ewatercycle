from esmvalcore.experimental.recipe_output import DataFile, ImageFile, RecipeOutput


def parse_recipe_output(recipe_output: RecipeOutput) -> dict[str, str]:
    """Parse ESMValTool recipe output into a dictionary.

    This method assumes:

    * Recipe had at least one diagnostic
    * Diagnostic produced at least one file
    * All files are in the same directory
    * The first variable name in a NetCDF file is the primary one

    Returns:
        Dictionary with forcing data variables as keys and file names as values
        and a key called directory with value the parent directory of the file names.
    """
    first_diagnostic_output = list(recipe_output.values())[0]
    output_files = first_diagnostic_output.files
    if not output_files:
        raise ValueError("No recipe output files found")
    forcing_files = {}
    for file in output_files:
        if isinstance(file, DataFile):
            # Datafile means ends with .nc
            # Use first variable name from inside file as key
            dataset = file.load_xarray()
            var_name = list(dataset.data_vars.keys())[0]
            dataset.close()
        elif isinstance(file, ImageFile):
            # Skip image files
            continue
        else:
            # Fall back to using file name without extension as key
            var_name = file.path.stem
        # Assume all files are in the same directory
        forcing_files[var_name] = file.path.name
        directory = str(file.path.parent)
    return {"directory": directory, **forcing_files}
