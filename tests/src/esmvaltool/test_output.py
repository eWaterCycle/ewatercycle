from pathlib import Path

import pytest
import xarray as xr
from esmvalcore.experimental.recipe_output import RecipeInfo, RecipeOutput

from ewatercycle.esmvaltool.output import parse_recipe_output


def test_parse_recipe_output_with_nc_files(tmp_path: Path):
    pr_ds = xr.Dataset({"pr": (["x"], [42])}, coords={"x": [1]})
    pr_fn = tmp_path / "pr.nc"
    pr_ds.to_netcdf(pr_fn)
    recipe_output = RecipeOutput(
        {"diagnostic/script": {pr_fn: {}}},
        info=RecipeInfo({"diagnostics": {"diagnostic": {}}}, "script"),
    )
    expected = {
        "directory": str(tmp_path),
        "pr": "pr.nc",
    }

    forcing_files = parse_recipe_output(recipe_output)
    assert forcing_files == expected


def test_parse_recipe_output_with_txt_files(tmp_path: Path):
    pr_fn = tmp_path / "pr.txt"
    recipe_output = RecipeOutput(
        {"diagnostic/script": {str(pr_fn): {}}},
        info=RecipeInfo({"diagnostics": {"diagnostic": {}}}, "script"),
    )
    expected = {
        "directory": str(tmp_path),
        "pr": "pr.txt",
    }
    forcing_files = parse_recipe_output(recipe_output)
    assert forcing_files == expected


def test_parse_recipe_output_with_no_files():
    recipe_output = RecipeOutput(
        {"diagnostic/script": {}},
        info=RecipeInfo({"diagnostics": {"diagnostic": {}}}, "script"),
    )
    with pytest.raises(ValueError):
        parse_recipe_output(recipe_output)


def test_parse_recipe_output_with_no_diagnostic():
    recipe_output = RecipeOutput({}, info=RecipeInfo({"diagnostics": {}}, "script"))
    with pytest.raises(IndexError):
        parse_recipe_output(recipe_output)
