"""Forcing related functionality for wflow."""
from typing import Dict, Literal, Optional

from esmvalcore.experimental import get_recipe

from ewatercycle.base.forcing import DATASETS, DefaultForcing, _session
from ewatercycle.util import get_extents, get_time, to_absolute_path


class WflowForcing(DefaultForcing):
    """Container for wflow forcing data.

    Args:
        directory: Directory where forcing data files are stored.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
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
        """Generate forcings for a model.

        The forcing is generated with help of
        `ESMValTool <https://esmvaltool.org/>`_.

        Args:
            dataset: Name of the source dataset. See :py:const:`~ewatercycle.base.forcing.DATASETS`.
            start_time: Start time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: nd time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            shape: Path to a shape file. Used for spatial selection.
            directory:  Directory in which forcing should be written.
                If not given will create timestamped directory.
            dem_file: Name of the dem_file to use. Also defines the basin
                param.
            extract_region: Region specification, dictionary must
                contain `start_longitude`, `end_longitude`, `start_latitude`,
                `end_latitude`
        """
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
        generated_forcing = WflowForcing(
            directory=directory,
            start_time=start_time,
            end_time=end_time,
            shape=shape,
            netcdfinput=forcing_file.name,
        )
        generated_forcing.save()
        return generated_forcing
