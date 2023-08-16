"""Forcing related functionality for marrmot."""

from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
import xarray as xr
from scipy.io import loadmat

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.esmvaltool.builder import RecipeBuilder
from ewatercycle.esmvaltool.models import Dataset, Recipe


class MarrmotForcing(DefaultForcing):
    """Container for marrmot forcing data.

    Args:
        directory: Directory where forcing data files are stored.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
        forcing_file: Matlab file that contains forcings for Marrmot
            models. See format forcing file in `model implementation
            <https://github.com/wknoben/MARRMoT/blob/8f7e80979c2bef941c50f2fb19ce4998e7b273b0/BMI/lib/marrmotBMI_oct.m#L15-L19>`_.

    .. code-block:: python

        from ewatercycle.forcing import sources

        forcing = sources.MarrmotForcing(
            'marmot',
            directory='/data/marrmot-forcings-case1',
            start_time='1989-01-02T00:00:00Z',
            end_time='1999-01-02T00:00:00Z',
            forcing_file='marrmot-1989-1999.mat'
        )
    """

    # type ignored because pydantic wants literal in base class while mypy does not
    model: Literal["marrmot"] = "marrmot"  # type: ignore
    forcing_file: Optional[str] = "marrmot.mat"

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str,
        **model_specific_options,
    ):
        return build_recipe(
            start_year=start_time.year,
            end_year=end_time.year,
            shape=shape,
            dataset=dataset,
        )

    @classmethod
    def _recipe_output_to_forcing_arguments(cls, recipe_output, model_specific_options):
        print(recipe_output)
        return {
            # TODO check key is correct
            "forcing_file": recipe_output["marrmot"],
        }

    def to_xarray(self) -> xr.Dataset:
        """Load forcing data from a matlab file into an xarray dataset.

        Returns:
            Dataset with forcing data.

        Example:

            >>> fn = forcing.directory / forcing.forcing_file
            >>> ds = load_forcing_file(fn)
            >>> ds

        """
        dataset = loadmat(self.forcing_file, mat_dtype=True)
        precip = dataset["forcing"]["precip"][0][0][0]
        temp = dataset["forcing"]["temp"][0][0][0]
        pet = dataset["forcing"]["pet"][0][0][0]
        forcing_start = datetime(*map(int, dataset["time_start"][0][:3]))  # type: ignore
        forcing_end = datetime(*map(int, dataset["time_end"][0][:3]))  # type: ignore
        # store data as a pandas Series (deliberately keep default time: 00:00)
        index = pd.date_range(forcing_start, forcing_end, name="time")
        lat, lon = dataset["data_origin"][0]
        # TODO use netcdf-cf conventions
        return xr.Dataset(
            {
                "precipitation": (
                    ["longitude", "latitude", "time"],
                    [[precip]],
                    {"units": "mm/day"},
                ),
                "temperature": (
                    ["longitude", "latitude", "time"],
                    [[temp]],
                    {"units": "C"},
                ),
                "evspsblpot": (
                    ["longitude", "latitude", "time"],
                    [[pet]],
                    {"units": "mm/day"},
                ),
            },
            coords={
                "lon": (["longitude", "latitude"], [[lon]]),
                "lat": (["longitude", "latitude"], [[lat]]),
                "time": index,
            },
            attrs={
                "title": "MARRMoT forcing data",
                "history": "Created by ewatercycle.plugins.marrmot.forcing.MarrmotForcing.to_xarray()",
            },
        )


def build_recipe(
    start_year: int,
    end_year: int,
    shape: Path,
    dataset: Dataset | str,
) -> Recipe:
    return (
        RecipeBuilder()
        .title("Generate forcing for the Marrmot hydrological model")
        .description("Generate forcing for the Marrmot hydrological model")
        .dataset(dataset)
        .start(start_year)
        .end(end_year)
        .shape(shape)
        # TODO do lumping in recipe instead of in diagnostic script
        # .lump()
        .add_variables(("tas", "pr", "psl", "rsds"))
        .add_variable("rsdt", mip="CFday")
        .script("hydrology/marrmot.py", {"basin": shape.stem})
        .build()
    )
