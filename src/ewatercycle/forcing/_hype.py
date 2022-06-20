"""Forcing related functionality for hype"""

from pathlib import Path
from typing import Optional

import pandas as pd
from esmvalcore.experimental import get_recipe

from ..util import get_time, to_absolute_path
from ._default import DefaultForcing, _session
from .datasets import DATASETS


class HypeForcing(DefaultForcing):
    """Container for hype forcing data."""

    def __init__(
        self,
        start_time: str,
        end_time: str,
        directory: str,
        shape: Optional[str] = None,
        Pobs: str = "Pobs.txt",
        TMAXobs: str = "TMAXobs.txt",
        TMINobs: str = "TMINobs.txt",
        Tobs: str = "Tobs.txt",
    ):
        """
        Pobs (str): Input file for precipitation data.
        TMAXobs (str): Input file for maximum temperature data.
        TMINobs (str): Input file for minimum temperature data.
        Tobs (str): Input file for temperature data.
        """
        super().__init__(start_time, end_time, directory, shape)
        self.Pobs = Pobs
        self.TMAXobs = TMAXobs
        self.TMINobs = TMINobs
        self.Tobs = Tobs

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        directory: Optional[str] = None,
    ) -> "HypeForcing":
        """
        None: Hype does not have model-specific generate options.
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_hype.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = ("preprocessor", "temperature", "water")

        for preproc_name in preproc_names:
            recipe.data["preprocessors"][preproc_name]["extract_shape"][
                "shapefile"
            ] = to_absolute_path(shape)

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
        recipe_output = recipe.run(session=_session(directory))

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
        return HypeForcing(
            directory=directory,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            Pobs=forcing_files["Pobs"].name,
            TMAXobs=forcing_files["TMAXobs"].name,
            TMINobs=forcing_files["TMINobs"].name,
            Tobs=forcing_files["Tobs"].name,
        )

    def plot(self):
        raise NotImplementedError("Dont know how to plot")
