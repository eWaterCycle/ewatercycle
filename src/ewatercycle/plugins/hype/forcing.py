"""Forcing related functionality for hype"""

from typing import Literal, Optional

import pandas as pd
import xarray as xr
from esmvalcore.experimental import get_recipe

from ewatercycle.base.forcing import DATASETS, DefaultForcing, run_esmvaltool_recipe
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

    def to_xarray(self) -> xr.Dataset:
        """Load forcing files into a xarray Dataset.

        Returns:
            xarray Dataset containing forcing data.
        """
        assert self.directory is not None, "Forcing directory is not set"

        # TODO add lats/lons to dataset
        # maybe infer from centers of subbasins in shapefile in ewatercycle_forcing.yaml?
        ds = xr.Dataset()
        ds["Pobs"] = pd.read_csv(
            self.directory / self.Pobs, sep=" ", index_col="DATE", parse_dates=True
        )
        ds["TMAXobs"] = pd.read_csv(
            self.directory / self.TMAXobs, sep=" ", index_col="DATE", parse_dates=True
        )
        ds["TMINobs"] = pd.read_csv(
            self.directory / self.TMINobs, sep=" ", index_col="DATE", parse_dates=True
        )
        ds["Tobs"] = pd.read_csv(
            self.directory / self.Tobs, sep=" ", index_col="DATE", parse_dates=True
        )
        ds = ds.rename({"DATE": "time", "dim_1": "subbasin"}).assign(
            subbasin=lambda ds: ds.subbasin.astype(int)
        )
        # TODO add units and long names to variables as attributes

        ds.attrs = {
            "title": "Hype forcing data",
            "history": "Created by ewatercycle.plugins.hype.forcing.HypeForcing.to_xarray()",
        }
        return ds
