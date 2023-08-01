"""Forcing related functionality for hype"""

from pathlib import Path
from typing import Literal, Optional

import pandas as pd
import xarray as xr
from esmvalcore.experimental import get_recipe

from ewatercycle.base.forcing import (
    DATASETS,
    DefaultForcing,
    _session,
    run_esmvaltool_recipe,
)
from ewatercycle.util import get_time, to_absolute_path


class HypeForcing(DefaultForcing):
    """Container for hype forcing data.

    Args:
        directory: Directory where forcing data files are stored.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
        Pobs (optional): Input file for precipitation data. Defaults to 'Pobs.txt'
        TMAXobs (optional): Input file for maximum temperature data. Defaults to
            'TMAXobs.txt'
        TMINobs (optional): Input file for minimum temperature data. Defaults to
            'TMINobs.txt'
        Tobs (optional): Input file for temperature data. Defaults to 'Tobs.txt'
    """

    # type ignored because pydantic wants literal in base class while mypy does not
    model: Literal["hype"] = "hype"  # type: ignore
    Pobs: str = "Pobs.txt"
    TMAXobs: str = "TMAXobs.txt"
    TMINobs: str = "TMINobs.txt"
    Tobs: str = "Tobs.txt"

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        directory: Optional[str] = None,
    ) -> "HypeForcing":
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_hype.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = ("preprocessor", "temperature", "water")

        for preproc_name in preproc_names:
            recipe.data["preprocessors"][preproc_name]["extract_shape"][
                "shapefile"
            ] = str(to_absolute_path(shape))

        recipe.data["datasets"] = [DATASETS[dataset]]

        variables = recipe.data["diagnostics"]["hype"]["variables"]
        var_names = "tas", "tasmin", "tasmax", "pr"

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]["start_year"] = startyear

        endyear = get_time(end_time).year
        for var_name in var_names:
            variables[var_name]["end_year"] = endyear

        # generate forcing data and retreive useful information
        recipe_output = run_esmvaltool_recipe(recipe, directory)

        # retrieve forcing files
        recipe_files = list(recipe_output.values())[0].files
        forcing_files = {f.path.stem: f.path for f in recipe_files}
        directory = str(forcing_files["Pobs"].parent)

        # Workaround: change subbasin id from 1234.0 to 1234 in all forcing files
        # Can removed once https://github.com/ESMValGroup/ESMValTool/issues/2678 is fixed
        for f in [
            forcing_files["Pobs"].name,
            forcing_files["Tobs"].name,
            forcing_files["TMAXobs"].name,
            forcing_files["TMINobs"].name,
        ]:
            p = Path(directory, f)
            ds = pd.read_csv(p, sep=" ", index_col="DATE")
            ds.rename(
                columns={x: x.replace(".0", "") for x in ds.columns}, inplace=True
            )
            ds.to_csv(p, sep=" ", index_label="DATE", float_format="%.3f")

        # instantiate forcing object based on generated data
        generated_forcing = HypeForcing(
            directory=directory,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            Pobs=forcing_files["Pobs"].name,
            TMAXobs=forcing_files["TMAXobs"].name,
            TMINobs=forcing_files["TMINobs"].name,
            Tobs=forcing_files["Tobs"].name,
        )
        generated_forcing.save()
        return generated_forcing


def load_forcing_files(forcing: HypeForcing) -> xr.Dataset:
    """Load forcing files into a xarray Dataset.

    Args:
        forcing: HypeForcing object.

    Returns:
        xarray Dataset containing forcing data.
    """
    # load forcing files
    forcing_file_lookup = {
        "Pobs": forcing.Pobs,
        "TMAXobs": forcing.TMAXobs,
        "TMINobs": forcing.TMINobs,
        "Tobs": forcing.Tobs,
    }
    assert forcing.directory is not None, "Forcing directory is not set"
    forcing_files = {k: forcing.directory / v for k, v in forcing_file_lookup.items()}

    # TODO add lat/lon to dataset
    # maybe infer from center of shapefile in ewatercycle_forcing.yaml?
    ds = xr.Dataset()
    for var, path in forcing_files.items():
        ds[var] = pd.read_csv(path, sep=" ", index_col="DATE", parse_dates=True)
    return ds
