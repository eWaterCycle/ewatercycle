import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from esmvalcore.config import CFG, Session
from esmvalcore.experimental import CFG
from esmvalcore.experimental import Recipe
from esmvalcore.experimental import Recipe as ESMValToolRecipe
from esmvalcore.experimental.recipe import RecipeOutput
from esmvalcore.experimental.recipe_output import RecipeOutput
from ruamel.yaml import YAML

from ewatercycle.esmvaltool.models import Recipe

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
    """When directory is set return a ESMValTool session that will write recipe output to that directory."""
    if directory is None:
        return None
    return _TimeLessSession(Path(directory).absolute())


def run_recipe(recipe: Recipe, output_dir: Path | None = None) -> RecipeOutput:
    recipe_file = NamedTemporaryFile(
        prefix="ewcrep", suffix=".yml", mode="w", delete=False
    )
    recipe_path = Path(recipe_file.name)

    try:
        recipe.save(recipe_path)

        logger.info(f"Running recipe {recipe_path} with ESMValTool")

        # TODO don't like having to different Recipe classes, should fix upstream
        esmlvaltool_recipe = ESMValToolRecipe(recipe_path)
        session = _session(output_dir)
        output = esmlvaltool_recipe.run(session=session)
    finally:
        recipe_path.unlink()

    return output


def _write_recipe(recipe: Recipe) -> Path:
    updated_recipe_file = NamedTemporaryFile(
        suffix=recipe.path.name, mode="w", delete=False
    )
    yaml = YAML(typ="safe")
    yaml.dump(recipe.data, updated_recipe_file)
    updated_recipe_file.close()
    return Path(updated_recipe_file.name)


def run_esmvaltool_recipe(recipe: Recipe, output_dir: str | None) -> RecipeOutput:
    """Run an ESMValTool recipe.

    The recipe.data dictionary can be modified before running the recipe.

    During run the recipe.path is overwritten with a temporary file containing the updated recipe.

    Args:
        recipe: ESMValTool recipe
        output_dir: Directory where output should be written to.
            If None then output is written to generated timestamped directory.

    Returns:
        ESMValTool recipe output

    Example:

        >>> from ewatercycle.forcing import run_esmvaltool_recipe
        >>> from esmvalcore.experimental.recipe import get_recipe
        >>> recipe = get_recipe('hydrology/recipe_wflow.yml')
        >>> recipe.data['scripts']['script']['dem_file'] = 'my_dem.nc'
        >>> output_dir = Path('./output_dir')
        >>> output = run_esmvaltool_recipe(recipe, output_dir)
    """
    # ESMVALCore 2.8.1 always runs original recipe,
    # write updated recipe to disk and use
    recipe.path = _write_recipe(recipe)
    # TODO write recipe in output_dir?
    # TODO fix in esmvalcore and wait for new version?

    session = _session(output_dir)
    output = recipe.run(session=session)

    # remove updated recipe file
    recipe.path.unlink()

    return output
