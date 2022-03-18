"""Forcing related functionality for lisflood"""

import logging
from pathlib import Path
from typing import Optional

from esmvalcore.experimental import get_recipe

from ..util import (
    data_files_from_recipe_output,
    get_extents,
    get_time,
    reindex,
    to_absolute_path,
)
from ._default import DefaultForcing
from ._lisvap import create_lisvap_config, lisvap
from .datasets import DATASETS

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
        run_lisvap: dict = None,
    ) -> "LisfloodForcing":
        """
        extract_region (dict): Region specification, dictionary must contain
            `start_longitude`, `end_longitude`, `start_latitude`, `end_latitude`
        run_lisvap (dict): Lisvap specification. Default is None. If lisvap should be run then
            give a dictionary with following key/value pairs:

                - lisvap_config: Name of Lisvap configuration file.
                - mask_map: A mask for the spatial selection.
                    This file should have same extent and resolution as parameter-set.
                - version: LISVAP/LISFLOOD model version supported by ewatercycle.
                    Pick from :py:obj:`~ewatercycle.models.lisflood.Lisflood.available_versions`.
                - parameterset_dir: Directory of the parameter set.
                    Directory should contains the Lisvap config file and files the config points to.

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

        # set crop to false to keep the entire globe (time consuming)
        # because lisflood parameter set is global i.e.
        # recipe.data["preprocessors"]["general"]["extract_shape"]["crop"] = False
        # However, lisflood diagnostics line 144 gives error
        # ValueError: The 'longitude' DimCoord points array must be strictly monotonic.

        # generate forcing data and retrieve useful information
        recipe_output = recipe.run()
        directory, forcing_files = data_files_from_recipe_output(recipe_output)

        if run_lisvap:
            # Get lisvap specific options and make paths absolute
            lisvap_config = str(to_absolute_path(run_lisvap["lisvap_config"]))
            mask_map = str(to_absolute_path(run_lisvap["mask_map"]))
            version = run_lisvap["version"]
            parameterset_dir = str(to_absolute_path(run_lisvap["parameterset_dir"]))

            # Reindex data because recipe cropped the data
            # Also, create a sub dir for reindexed dataset because xarray does not
            # let to overwrite!
            reindexed_forcing_directory = Path(f"{directory}/reindexed")
            reindexed_forcing_directory.mkdir(parents=True, exist_ok=True)
            for var_name in {"pr", "tas", "tasmax", "tasmin", "sfcWind", "rsds", "e"}:
                reindex(
                    f"{directory}/{forcing_files[var_name]}",
                    var_name,
                    mask_map,
                    f"{reindexed_forcing_directory}/{forcing_files[var_name]}",
                )
            # Add lisvap file names
            for var_name in {"e0", "es0", "et0"}:
                forcing_files[
                    var_name
                ] = f"lisflood_{dataset}_{basin}_{var_name}_{startyear}_{endyear}.nc"

            config_file = create_lisvap_config(
                parameterset_dir,
                str(reindexed_forcing_directory),
                dataset,
                lisvap_config,
                mask_map,
                start_time,
                end_time,
                forcing_files,
            )
            lisvap(
                version,
                parameterset_dir,
                str(reindexed_forcing_directory),
                mask_map,
                config_file,
            )
            # TODO add a logger message about the results of lisvap using
            # exit_code, stdout, stderr
            # Instantiate forcing object based on generated data
            return LisfloodForcing(
                directory=str(reindexed_forcing_directory),
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
