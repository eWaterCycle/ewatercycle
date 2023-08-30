"""Forcing related functionality for marrmot."""

from datetime import datetime
from pathlib import Path
from typing import Optional

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

    Examples:

        From existing forcing data:

        .. code-block:: python

            from ewatercycle.forcing import sources

            forcing = sources.MarrmotForcing(
                directory='/data/marrmot-forcings-case1',
                start_time='1989-01-02T00:00:00Z',
                end_time='1999-01-02T00:00:00Z',
                forcing_file='marrmot-1989-1999.mat'
            )

        Generate from ERA5 forcing dataset and Rhine.

        .. code-block:: python

            from ewatercycle.forcing import sources
            from ewatercycle.testing.fixtures import rhine_shape

            shape = rhine_shape()
            forcing = sources.MarrmotForcing.generate(
                dataset='ERA5',
                start_time='2000-01-01T00:00:00Z',
                end_time='2001-01-01T00:00:00Z',
                shape=shape,
            )
    """

    forcing_file: Optional[str] = "marrmot.mat"

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str | dict,
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
        # key in recipe_output is concat of dataset, shape start year and end year
        # for example 'marrmot_ERA5_Rhine_2000_2001.mat'
        # instead of constructing key just use first and only value of dict
        first_forcing_file = next(iter(recipe_output.values()))
        return {"forcing_file": first_forcing_file}

    def to_xarray(self) -> xr.Dataset:
        """Load forcing data from a matlab file into an xarray dataset.

        Returns:
            Dataset with forcing data.
        """
        if self.directory is None or self.forcing_file is None:
            raise ValueError("Directory or forcing_file is not set")
        fn = self.directory / self.forcing_file
        dataset = loadmat(fn, mat_dtype=True)
        # Generated forcing with ewatercycle has shape (1, <nr timestamps>)
        # Mat files from elsewhere can have shape (<nr timestamps>, 1)
        precip = dataset["forcing"]["precip"][0][0].flatten()
        temp = dataset["forcing"]["temp"][0][0].flatten()
        pet = dataset["forcing"]["pet"][0][0].flatten()
        time_start = dataset["time_start"][0][:3]
        forcing_start = datetime(*map(int, time_start))  # type: ignore
        time_end = dataset["time_end"][0][:3]
        forcing_end = datetime(*map(int, time_end))  # type: ignore
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
    dataset: Dataset | str | dict,
) -> Recipe:
    """Build a recipe for generating forcing for the Marrmot hydrological model.

    Args:
        start_year: Start year of forcing.
        end_year: End year of forcing.
        shape: Path to a shape file. Used for spatial selection.
        dataset: Dataset to get forcing data from.
            When string is given a predefined dataset is looked up in
            :py:const:`ewatercycle.esmvaltool.datasets.DATASETS`.
            When dict given it is passed to
            :py:class:`ewatercycle.esmvaltool.models.Dataset` constructor.
    """
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
