"""eWaterCycle wrapper around Lisflood BMI."""

import logging
from pathlib import Path
from typing import Any, ItemsView

from pydantic import PrivateAttr, model_validator

from ewatercycle.base.model import ISO_TIMEFMT, ContainerizedModel
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.container import ContainerImage
from ewatercycle.plugins.lisflood.config import XmlConfig
from ewatercycle.plugins.lisflood.forcing import LisfloodForcing
from ewatercycle.util import get_time, to_absolute_path

logger = logging.getLogger(__name__)


class Lisflood(ContainerizedModel):
    """eWaterCycle implementation of Lisflood hydrological model.

    Args:
      version: pick a version for which an grpc4bmi docker image is available.
      parameter_set: LISFLOOD input files. Any included forcing data will be ignored.
      forcing: a LisfloodForcing object.

    Example:
        See examples/lisflood.ipynb in
        `ewatercycle repository <https://github.com/eWaterCycle/ewatercycle>`_
    """

    forcing: LisfloodForcing  # not optional for this model
    parameter_set: ParameterSet  # not optional for this model
    bmi_image: ContainerImage = ContainerImage("ewatercycle/lisflood-grpc4bmi:20.10")

    _config: XmlConfig = PrivateAttr()

    @model_validator(mode="after")
    def _update_config(self: "Lisflood") -> "Lisflood":
        self._config = XmlConfig(self.parameter_set.config)
        return self

    def _get_textvar_value(self, name: str):
        for textvar in self._config.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]
            if name == textvar_name:
                return textvar.get("value")
        raise KeyError(f"Name {name} not found in the config file.")

    def _make_cfg_file(self, **kwargs) -> Path:
        """Create lisflood config file."""

        # Update times
        model_start = get_time(self.forcing.start_time)
        model_end = get_time(self.forcing.end_time)
        if "start_time" in kwargs:
            start = get_time(kwargs["start_time"])
            if (
                get_time(self.forcing.start_time)
                <= start
                <= get_time(self.forcing.end_time)
            ):
                model_start = start
            else:
                raise ValueError("start_time outside forcing time range")
        if "end_time" in kwargs:
            end = get_time(kwargs["end_time"])
            if (
                get_time(self.forcing.start_time)
                <= end
                <= get_time(self.forcing.end_time)
            ):
                model_end = end
            else:
                raise ValueError("end_time outside forcing time range")

        settings = {
            "CalendarDayStart": model_start.strftime("%d/%m/%Y 00:00"),
            "StepStart": "1",
            "StepEnd": str((model_end - model_start).days),
            "PathRoot": str(self.parameter_set.directory),
            "PathMeteo": str(self.forcing.directory),
            "PathOut": str(self._cfg_dir),
        }

        if "IrrigationEfficiency" in kwargs:
            settings["IrrigationEfficiency"] = kwargs["IrrigationEfficiency"]

        if "MaskMap" in kwargs:
            mask_map = to_absolute_path(input_path=kwargs["MaskMap"])
            settings["MaskMap"] = str(mask_map.with_suffix(""))
            try:
                mask_map.relative_to(self.parameter_set.directory)
            except ValueError:
                # If not relative add dir
                self._additional_input_dirs.append(str(mask_map.parent))

        for textvar in self._config.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]

            # general settings
            for key, value in settings.items():
                if key in textvar_name:
                    textvar.set("value", value)

            # input for lisflood
            if "PrefixPrecipitation" in textvar_name:
                textvar.set("value", Path(self.forcing.PrefixPrecipitation).stem)
            if "PrefixTavg" in textvar_name:
                textvar.set("value", Path(self.forcing.PrefixTavg).stem)

            # maps_prefixes dictionary contains lisvap filenames in lisflood config
            maps_prefixes = {
                "E0Maps": {
                    "name": "PrefixE0",
                    "value": Path(self.forcing.PrefixE0).stem,
                },
                "ES0Maps": {
                    "name": "PrefixES0",
                    "value": Path(self.forcing.PrefixES0).stem,
                },
                "ET0Maps": {
                    "name": "PrefixET0",
                    "value": Path(self.forcing.PrefixET0).stem,
                },
            }
            # output of lisvap
            for map_var, prefix in maps_prefixes.items():
                if prefix["name"] in textvar_name:
                    textvar.set("value", prefix["value"])
                if map_var in textvar_name:
                    textvar.set("value", f"$(PathMeteo)/$({prefix['name']})")

        # Write to new setting file
        lisflood_file = self._cfg_dir / "lisflood_setting.xml"
        self._config.save(str(lisflood_file))
        return lisflood_file

    @property
    def parameters(self) -> ItemsView[str, Any]:
        """List the parameters for this model.

        Exposed Lisflood parameters:
            IrrigationEfficiency: Field application irrigation efficiency.
                max 1, ~0.90 drip irrigation, ~0.75 sprinkling
            MaskMap: Mask map to use instead of one supplied in parameter set.
                Path to a NetCDF or pcraster file with
                same dimensions as parameter set map files and a boolean variable.
            start_time: Start time of model in UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing end time is used.
        """
        return {
            "IrrigationEfficiency": self._get_textvar_value("IrrigationEfficiency"),
            "MaskMap": self._get_textvar_value("MaskMap"),
            "start_time": get_time(self.forcing.start_time).strftime(ISO_TIMEFMT),
            "end_time": get_time(self.forcing.end_time).strftime(ISO_TIMEFMT),
        }.items()

    def finalize(self) -> None:
        """Perform tear-down tasks for the model."""
        # Finalize function of bmi class of lisflood is kaput, so not calling it
        del self._bmi


# TODO it needs fix regarding forcing
# def reindex_forcings(
#     mask_map: Path, forcing: LisfloodForcing, output_dir: Path = None
# ) -> Path:
#     """Reindex forcing files to match mask map grid

#     Args:
#         mask_map: Path to NetCDF file used a boolean map that defines model
#             boundaries.
#         forcing: Forcing data from ESMValTool
#         output_dir: Directory where to write the re-indexed files, given by user
#             or created for user

#     Returns:
#         Output dir with re-indexed files.
#     """
#     output_dir = _generate_workdir(output_dir)
#     mask = xr.open_dataarray(mask_map).load()
#     data_files = list(forcing.recipe_output.values())[0].data_files
#     for data_file in data_files:
#         dataset = data_file.load_xarray()
#         out_fn = output_dir / data_file.filename.name
#         var_name = list(dataset.data_vars.keys())[0]
#         encoding = {
#             var_name: {
#                 "zlib": True,
#                 "complevel": 4,
#                 "chunksizes": (1,) + dataset[var_name].shape[1:],
#             }
#         }
#         dataset.reindex(
#             {"lat": mask["lat"], "lon": mask["lon"]},
#             method="nearest",
#             tolerance=1e-2,
#         ).to_netcdf(out_fn, encoding=encoding)
#     return output_dir
