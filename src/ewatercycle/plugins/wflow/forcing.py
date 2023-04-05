"""Forcing related functionality for wflow."""
from typing import Dict, Literal, Optional

from esmvalcore.experimental import get_recipe

from ewatercycle.forcing._default import DefaultForcing, _session
from ewatercycle.forcing.datasets import DATASETS
from ewatercycle.util import get_extents, get_time, to_absolute_path


class WflowForcing(DefaultForcing):
    """Container for wflow forcing data.

    Args:
        netcdfinput (str) = "inmaps.nc": Path to forcing file.
        Precipitation (str) = "/pr": Variable name of precipitation data in
            input file.
        EvapoTranspiration (str) = "/pet": Variable name of
            evapotranspiration data in input file.
        Temperature (str) = "/tas": Variable name of temperature data in
            input file.
        Inflow (str) = None: Variable name of inflow data in input file.
    """

    # type ignored because pydantic wants literal in base class while mypy does not
    model: Literal["wflow"] = "wflow"  # type: ignore
    netcdfinput: str = "inmaps.nc"
    Precipitation: str = "/pr"  # noqa: N803
    EvapoTranspiration: str = "/pet"
    Temperature: str = "/tas"
    Inflow: Optional[str] = None

    @classmethod
    def generate(  # type: ignore
        cls,
        dataset: str,
        start_time: str,
        end_time: str,
        shape: str,
        dem_file: str,
        directory: Optional[str] = None,
        extract_region: Optional[Dict[str, float]] = None,
    ) -> "WflowForcing":
        """
        dem_file (str): Name of the dem_file to use. Also defines the basin
            param.
        extract_region (dict): Region specification, dictionary must
            contain `start_longitude`, `end_longitude`, `start_latitude`,
            `end_latitude`
        """  # noqa docstrings are combined with forcing.generate()
        # load the ESMValTool recipe
        recipe_name = "hydrology/recipe_wflow.yml"
        recipe = get_recipe(recipe_name)

        basin = to_absolute_path(shape).stem
        recipe.data["diagnostics"]["wflow_daily"]["scripts"]["script"]["basin"] = basin

        # model-specific updates
        script = recipe.data["diagnostics"]["wflow_daily"]["scripts"]["script"]
        script["dem_file"] = dem_file

        if extract_region is None:
            extract_region = get_extents(shape, pad=3)
        recipe.data["preprocessors"]["rough_cutout"]["extract_region"] = extract_region

        recipe.data["diagnostics"]["wflow_daily"]["additional_datasets"] = [
            DATASETS[dataset]
        ]

        variables = recipe.data["diagnostics"]["wflow_daily"]["variables"]
        var_names = "tas", "pr", "psl", "rsds", "rsdt"

        startyear = get_time(start_time).year
        for var_name in var_names:
            variables[var_name]["start_year"] = startyear

        endyear = get_time(end_time).year
        for var_name in var_names:
            variables[var_name]["end_year"] = endyear

        # generate forcing data and retreive useful information
        recipe_output = recipe.run(session=_session(directory))
        forcing_data = recipe_output["wflow_daily/script"].data_files[0]

        forcing_file = forcing_data.path
        directory = str(forcing_file.parent)

        # instantiate forcing object based on generated data
        return WflowForcing(
            directory=directory,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            netcdfinput=forcing_file.name,
        )
