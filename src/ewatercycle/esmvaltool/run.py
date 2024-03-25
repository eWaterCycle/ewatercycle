"""Run ESMValTool recipes."""
import logging
import warnings
from pathlib import Path
from tempfile import NamedTemporaryFile

from esmvalcore.config import CFG, Session
from esmvalcore.experimental.recipe import Recipe as ESMValToolRecipe
from esmvalcore.experimental.recipe_output import DataFile, ImageFile, RecipeOutput

from ewatercycle.esmvaltool.schema import Recipe

logger = logging.getLogger(__name__)


class _TimeLessSession(Session):
    """ESMValTool session that does not use time in session directory."""

    def __init__(self, output_dir: Path):
        super().__init__(CFG.copy())
        self.output_dir = output_dir

    @property
    def session_dir(self):
        return self.output_dir


def _session(directory: Path | str | None = None) -> Session | None:
    """Make ESMValTool session with optional output directory.

    Args:
        directory: Directory where output should be written to.
            If None then output is written to generated timestamped directory.
    """
    if directory is None:
        return None
    return _TimeLessSession(Path(directory).absolute())


def run_recipe(recipe: Recipe, output_dir: Path | None = None) -> dict[str, str]:
    """Run an ESMValTool recipe.

    Args:
        recipe: ESMValTool recipe
        output_dir: Directory where output should be written to.
            If None then output is written to generated timestamped directory.

    Returns:
        Dictionary with forcing data variables as keys and file names as values
        and a key called directory with value the parent directory of the file names.

    Example:

        To run a recipe that generates a distributed forcing dataset:

        >>> from ewatercycle.testing.fixtures import rhine_shape
        >>> from ewatercycle.esmvaltool.builder import (
        ...    build_generic_distributed_forcing_recipe
        ... )
        >>> from ewatercycle.esmvaltool.run import run_recipe
        >>> shape = rhine_shape()
        >>> recipe = build_generic_distributed_forcing_recipe(
        ...     start_year=2000,
        ...     end_year=2001,
        ...     shape=shape,
        ...     dataset='ERA5',
        ... )
        >>> output = run_recipe(recipe)
        >>> output
        diagnostic/script:
          DataFile('OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc')
          DataFile('OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc')
          DataFile('OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc')
          DataFile('OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc')
        <BLANKLINE>
        diagnostic/pr:
          DataFile('OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc')
        <BLANKLINE>
        diagnostic/tas:
          DataFile('OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc')
        <BLANKLINE>
        diagnostic/tasmin:
          DataFile('OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc')
        <BLANKLINE>
        diagnostic/tasmax:
          DataFile('OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc')

    """
    # Relax esmvalcore log warnings, otherwise the user is spammed with useless info
    logging.getLogger("esmvalcore").setLevel(logging.ERROR)

    with warnings.catch_warnings():
        # Note: the following filterwarnings doesn't seem to work:
        warnings.filterwarnings(  # Not relevant for end users.
            action="ignore",
            message="Thank you for trying out the new ESMValCore API",
        )
        warnings.filterwarnings(  # Hide Iris warning (upstream issue)
            action="ignore",
            message="Saving to netcdf with legacy-style attribute",
        )

        output = _save_and_run_recipe(recipe, output_dir)
        return _parse_recipe_output(output)


def _save_and_run_recipe(recipe: Recipe, output_dir: Path | None) -> RecipeOutput:
    """Save recipe to temporary file and run it with ESMValTool.

    Args:
        recipe: ESMValTool recipe
        output_dir: Directory where output should be written to.
            If None then output is written to generated timestamped directory.

    Returns:
        ESMValTool recipe output
    """
    recipe_file = NamedTemporaryFile(
        prefix="ewcrep", suffix=".yml", mode="w", delete=False
    )
    recipe_path = Path(recipe_file.name)

    try:
        recipe.save(recipe_path)

        logger.info("Running recipe %s with ESMValTool", recipe_path)

        # TODO don't like having to different Recipe classes, should fix upstream
        esmlvaltool_recipe = ESMValToolRecipe(recipe_path)
        session = _session(output_dir)
        output = esmlvaltool_recipe.run(session=session)
    finally:
        recipe_path.unlink()
    return output


def _parse_recipe_output(recipe_output: RecipeOutput) -> dict[str, str]:
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
    for output_file in output_files:
        var_name = output_file.path.stem
        if isinstance(output_file, DataFile):
            # Datafile means ends with .nc
            # Use first variable name from inside file as key
            dataset = output_file.load_xarray()
            var_name = list(dataset.data_vars.keys())[0]
            dataset.close()
        elif isinstance(output_file, ImageFile):
            # Skip image files
            continue
        # Assume all files are in the same directory
        forcing_files[var_name] = output_file.path.name
        directory = str(output_file.path.parent)
    return {"directory": directory, **forcing_files}
