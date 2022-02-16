"""Forcing related functionality for lisflood"""

import logging
from typing import Optional

from esmvalcore.experimental import get_recipe

from ..util import (
    data_files_from_recipe_output,
    get_extents,
    get_time,
    to_absolute_path,
)
from ._default import DefaultForcing
from .datasets import DATASETS
from ._lisvap import create_lisvap_config, lisvap

logger = logging.getLogger(__name__)


class LisfloodForcing(DefaultForcing):
    """Container for lisflood forcing data."""

    # TODO check whether start/end time are same as in the files
    def __init__(
        self,
        start_time: str,
        end_time: str,
        directory: str,
        shape: Optional[str] = None,
        PrefixPrecipitation: str = "pr.nc",
        PrefixTavg: str = "tas.nc",
        PrefixE0: str = "e0.nc",
        PrefixES0: str = "es0.nc",
        PrefixET0: str = "et0.nc",
    ):
        """
        PrefixPrecipitation: Path to a NetCDF or pcraster file with
            precipitation data
        PrefixTavg: Path to a NetCDF or pcraster file with average
            temperature data
        PrefixE0: Path to a NetCDF or pcraster file with potential
            evaporation rate from open water surface data
        PrefixES0: Path to a NetCDF or pcraster file with potential
            evaporation rate from bare soil surface data
        PrefixET0: Path to a NetCDF or pcraster file with potential
            (reference) evapotranspiration rate data
        """
        super().__init__(start_time, end_time, directory, shape)
        self.PrefixPrecipitation = PrefixPrecipitation
        self.PrefixTavg = PrefixTavg
        self.PrefixE0 = PrefixE0
        self.PrefixES0 = PrefixES0
        self.PrefixET0 = PrefixET0

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        extract_region: dict = None,
        run_lisvap: bool = False,
        lisvap_config: str = None,
        mask_map: str = None,
        version: str = None,
        parameterset_dir: str = None,
    ) -> "LisfloodForcing":
        """
        extract_region (dict): Region specification, dictionary must contain
            `start_longitude`, `end_longitude`, `start_latitude`, `end_latitude`
        run_lisvap (bool): if lisvap should be run. Default is False.
            Running lisvap is not supported yet.
        TODO add regrid options so forcing can be generated for parameter set
        TODO that is not on a 0.1x0.1 grid
        """
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_lisflood.yml"
        recipe = get_recipe(recipe_name)

        # model-specific updates to the recipe
        preproc_names = (
            "general",
            "daily_water",
            "daily_temperature",
            "daily_radiation",
            "daily_windspeed",
        )

        basin = to_absolute_path(shape).stem
        for preproc_name in preproc_names:
            recipe.data["preprocessors"][preproc_name]["extract_shape"][
                "shapefile"
            ] = shape
        recipe.data["diagnostics"]["diagnostic_daily"]["scripts"]["script"][
            "catchment"
        ] = basin

        if extract_region is None:
            extract_region = get_extents(shape)
        for preproc_name in preproc_names:
            recipe.data["preprocessors"][preproc_name][
                "extract_region"
            ] = extract_region

        recipe.data["datasets"] = [DATASETS[dataset]]

        variables = recipe.data["diagnostics"]["diagnostic_daily"]["variables"]
        var_names = "pr", "tas", "tasmax", "tasmin", "tdps", "uas", "vas", "rsds"

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]["start_year"] = startyear

        endyear = get_time(end_time).year
        for var_name in var_names:
            variables[var_name]["end_year"] = endyear

        # generate forcing data and retrieve useful information
        recipe_output = recipe.run()
        directory, forcing_files = data_files_from_recipe_output(recipe_output)

        # TODO run lisvap
        # TODO forcing_files['e0'] = ...
        if run_lisvap:
            config_file = create_lisvap_config(
                parameterset_dir,
                directory,
                dataset,
                lisvap_config,
                mask_map,
                start_time,
                end_time
                )
            lisvap(
                version,
                parameterset_dir,
                directory,
                mask_map,
                config_file,
                )
            for cmor_name in {'e0', 'es0', 'et0'}:
                forcing_files[cmor_name] = f"lisflood_{cmor_name}_{startyear}_{endyear}.nc"

            # instantiate forcing object based on generated data
            return LisfloodForcing(
                directory=directory,
                start_time=start_time,
                end_time=end_time,
                shape=shape,
                PrefixPrecipitation=forcing_files["pr"],
                PrefixTavg=forcing_files["tas"],
                PrefixE0=forcing_files["e0"],
                PrefixES0=forcing_files["es0"],
                PrefixET0=forcing_files["et0"],
            )
        else:
            message = (
                "Parameter `run_lisvap` is set to False. No forcing data will be "
                "generated for 'e0', 'es0' and 'et0'. However, the recipe creates "
                f"LISVAP input data that can be found in {directory}."
            )
            logger.warning("%s", message)
            # instantiate forcing object based on generated data
            return LisfloodForcing(
                directory=directory,
                start_time=start_time,
                end_time=end_time,
                shape=shape,
                PrefixPrecipitation=forcing_files["pr"],
                PrefixTavg=forcing_files["tas"],
            )

    def plot(self):
        raise NotImplementedError("Dont know how to plot")
