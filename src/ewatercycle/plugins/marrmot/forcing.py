"""Forcing related functionality for marrmot."""

from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
import xarray as xr
from esmvalcore.experimental import get_recipe
from scipy.io import loadmat

from ewatercycle.base.forcing import (
    DATASETS,
    DefaultForcing,
    _session,
    run_esmvaltool_recipe,
)
from ewatercycle.util import get_time, to_absolute_path


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
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        directory: Optional[str] = None,
    ) -> "MarrmotForcing":
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_marrmot.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        basin = to_absolute_path(shape).stem
        recipe.data["preprocessors"]["daily"]["extract_shape"]["shapefile"] = shape
        recipe.data["diagnostics"]["diagnostic_daily"]["scripts"]["script"][
            "basin"
        ] = basin

        recipe.data["diagnostics"]["diagnostic_daily"]["additional_datasets"] = [
            DATASETS[dataset]
        ]

        variables = recipe.data["diagnostics"]["diagnostic_daily"]["variables"]
        var_names = "tas", "pr", "psl", "rsds", "rsdt"

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]["start_year"] = startyear

        endyear = get_time(end_time).year
        for var_name in var_names:
            variables[var_name]["end_year"] = endyear

        # generate forcing data and retrieve useful information
        recipe_output = run_esmvaltool_recipe(recipe, directory)
        task_output = recipe_output["diagnostic_daily/script"]

        # check that recipe output contains only one .mat file
        matlab_files = []
        for datafile in task_output.files:
            if datafile.path.suffix == ".mat":
                matlab_files.append(datafile)

        if len(matlab_files) == 0:
            raise FileNotFoundError(
                "No .mat files found in output directory: " + str(directory)
            )
        if len(matlab_files) > 1:
            raise FileNotFoundError(
                "More than one .mat files found in output directory: " + str(directory)
            )

        # everything ok so retreive paths
        forcing_file: Path = matlab_files[0].path
        directory = str(forcing_file.parent)

        # instantiate forcing object based on generated data
        generated_forcing = MarrmotForcing(
            directory=directory,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            forcing_file=forcing_file.name,
        )
        generated_forcing.save()
        return generated_forcing


# TODO could be nice to have plot function
# that loads the mat file into a xarray dataset and plots it


# TODO make method of MarrmotForcing class? What to call it?
# TODO allow MarrmotForcing to be given as argument.
def load_forcing_file(fn: Path) -> xr.Dataset:
    """Load forcing data from a matlab file into an xarray dataset.

    Args:
        fn: Path to matlab file.

    Returns:
        Dataset with forcing data.

    Example:

        >>> fn = forcing.directory / forcing.forcing_file
        >>> ds = load_forcing_file(fn)
        >>> ds

    """
    dataset = loadmat(fn, mat_dtype=True)
    precip = dataset["forcing"]["precip"][0][0][0]
    temp = dataset["forcing"]["temp"][0][0][0]
    pet = dataset["forcing"]["pet"][0][0][0]
    forcing_start = datetime(*map(int, dataset["time_start"][0][:3]))  # type: ignore
    forcing_end = datetime(*map(int, dataset["time_end"][0][:3]))  # type: ignore
    # store data as a pandas Series (deliberately keep default time: 00:00)
    index = pd.date_range(forcing_start, forcing_end, name="time")
    lat, lon = dataset["data_origin"][0]
    # TODO add units as attributes, what are the units actually?
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
            "history": f"Created by ewatercycle.forcing.sources.load_forcing_file({fn})",
        },
    )
