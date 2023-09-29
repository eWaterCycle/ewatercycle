from pathlib import Path

from ewatercycle.esmvaltool.schema import Recipe
from ewatercycle.testing.helpers import reyamlify


def test_recipe_load(tmp_path: Path):
    """Test Recipe.load."""
    recipe_path = tmp_path / "recipe.yml"
    recipe_path.write_text(
        """\
documentation:
    title: Test recipe
    description: Test recipe
    authors:
        - Test author
    projects:
        - Test project
    references:
        - Test reference
"""
    )

    recipe = Recipe.load(recipe_path)

    expected = Recipe(
        documentation={
            "title": "Test recipe",
            "description": "Test recipe",
            "authors": ["Test author"],
            "projects": ["Test project"],
            "references": ["Test reference"],
        },
    )
    assert recipe == expected


def test_recipe_save(tmp_path: Path):
    """Test Recipe.save."""
    recipe = Recipe(
        documentation={
            "title": "Test recipe",
            "description": "Test recipe",
            "authors": ["Test author"],
            "projects": ["Test project"],
            "references": ["Test reference"],
        },
    )
    recipe_path = tmp_path / "recipe.yml"
    recipe.save(recipe_path)

    expected = """\
documentation:
  title: Test recipe
  description: Test recipe
  authors:
    - Test author
  projects:
    - Test project
  references:
    - Test reference
"""
    content = recipe_path.read_text()

    assert content == reyamlify(expected)
