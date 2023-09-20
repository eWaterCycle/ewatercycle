"""Forcing related functionality for hype."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import xarray as xr

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.esmvaltool.builder import RecipeBuilder
from ewatercycle.esmvaltool.schema import Dataset


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

    Pobs: str = "Pobs.txt"
    TMAXobs: str = "TMAXobs.txt"
    TMINobs: str = "TMINobs.txt"
    Tobs: str = "Tobs.txt"

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str | dict,
        **model_specific_options
    ):
        return build_hype_recipe(
            start_year=start_time.year,
            end_year=end_time.year,
            shape=shape,
            dataset=dataset,
        )

    def to_xarray(self) -> xr.Dataset:
        """Load forcing files into a xarray Dataset.

        Returns:
            xarray Dataset containing forcing data.
        """
        assert self.directory is not None, "Forcing directory is not set"

        # TODO add lats/lons to dataset maybe infer
        # from centers of subbasins in shapefile in ewatercycle_forcing.yaml?
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


def build_hype_recipe(
    start_year: int,
    end_year: int,
    shape: Path,
    dataset: Dataset | str | dict,
):
    """Build an ESMValTool recipe for Hype forcing data.

    Args:
        start_year: The start year of the recipe.
        end_year: The end year of the recipe.
        shape: The shape of the recipe.
        dataset: Dataset to get forcing data from.
            When string is given a predefined dataset is looked up in
            :py:const:`ewatercycle.esmvaltool.datasets.DATASETS`.
            When dict given it is passed to
            :py:class:`ewatercycle.esmvaltool.models.Dataset` constructor.

    Returns:
        The built recipe.
    """
    return (
        RecipeBuilder()
        .title("Hype forcing data")
        .dataset(dataset)
        .start(start_year)
        .end(end_year)
        .shape(shape, decomposed=True)
        .lump()
        .add_variable("tas", units="degC")
        .add_variable("tasmin", units="degC")
        .add_variable("tasmax", units="degC")
        .add_variable("pr", units="kg m-2 d-1")
        .script("hydrology/hype.py")
        .build()
    )
