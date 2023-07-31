"""eWaterCycle wrapper around Lisflood BMI."""

import datetime
import logging
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple, Type

from pydantic import PrivateAttr, model_validator, root_validator

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

    # TODO: consider combining all settings in a single _config attribute
    _config: XmlConfig = PrivateAttr()
    _forcing_start_time: datetime.datetime = PrivateAttr()
    _forcing_end_time: datetime.datetime = PrivateAttr()
    _model_start_time: datetime.datetime = PrivateAttr()
    _model_end_time: datetime.datetime = PrivateAttr()
    _irrigation_efficiency: str | None = PrivateAttr(None)
    _mask_map: Path = PrivateAttr()

    @model_validator(mode="after")
    def _check_forcing(self) -> "Lisflood":
        """Check forcing argument and get path, start/end time of forcing data."""
        # TODO check if mask has same grid as forcing files,
        # if not warn users to run reindex_forcings

        # TODO directory should not be optional

        self._forcing_start_time = get_time(self.forcing.start_time)
        self._model_start_time = self._forcing_start_time
        self._forcing_end_time = get_time(self.forcing.end_time)
        self._model_end_time = self._forcing_end_time

        return self

    @model_validator(mode="after")
    def _update_config(self) -> "Lisflood":
        self._config = XmlConfig(self.parameter_set.config)
        return self

    def _get_textvar_value(self, name: str):
        for textvar in self._config.config.iter("textvar"):
            textvar_name = textvar.attrib["name"]
            if name == textvar_name:
                return textvar.get("value")
        raise KeyError(f"Name {name} not found in the config file.")

    def setup(
        self,
        IrrigationEfficiency: Optional[str] = None,  # noqa: N803
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        MaskMap: Optional[str] = None,
        **kwargs,
    ) -> Tuple[str, str]:
        """Configure model run.

        1. Creates config file and config directory
           based on the forcing variables and time range.
        2. Start bmi container and store as :py:attr:`bmi`

        Args:
            IrrigationEfficiency: Field application irrigation efficiency.
                max 1, ~0.90 drip irrigation, ~0.75 sprinkling
            start_time: Start time of model in UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing start time is used.
            end_time: End time of model in  UTC and ISO format string
                e.g. 'YYYY-MM-DDTHH:MM:SSZ'.
                If not given then forcing end time is used.
            MaskMap: Mask map to use instead of one supplied in parameter set.
                Path to a NetCDF or pcraster file with
                same dimensions as parameter set map files and a boolean variable.
            cfg_dir: a run directory given by user or created for user.

        Returns:
            Path to config file and path to config directory
        """
        # TODO: move parsing these kwargs to an "_update_config" method.
        if IrrigationEfficiency is not None:
            self._irrigation_efficiency = IrrigationEfficiency

        if start_time is not None:
            start = get_time(start_time)
            if self._forcing_start_time <= start <= self._forcing_end_time:
                self._model_start_time = start
            else:
                raise ValueError("start_time outside forcing time range")
        if end_time is not None:
            end = get_time(end_time)
            if self._forcing_start_time <= end <= self._forcing_end_time:
                self._model_end_time = end
            else:
                raise ValueError("end_time outside forcing time range")

        if MaskMap is not None:
            self._mask_map = to_absolute_path(input_path=MaskMap)
            try:
                self._mask_map.relative_to(self.parameter_set.directory)
            except ValueError:
                # If not relative add dir
                self._additional_input_dirs.append(str(self._mask_map.parent))

        return super().setup(**kwargs)

    def _make_cfg_file(self, **kwargs) -> Path:
        """Create lisflood config file."""
        assert self.parameter_set is not None
        assert self.forcing is not None

        settings = {
            "CalendarDayStart": self._model_start_time.strftime("%d/%m/%Y 00:00"),
            "StepStart": "1",
            "StepEnd": str((self._model_end_time - self._model_start_time).days),
            "PathRoot": str(self.parameter_set.directory),
            "PathMeteo": str(self.forcing.directory),
            "PathOut": str(self._cfg_dir),
        }

        if self._irrigation_efficiency is not None:
            settings["IrrigationEfficiency"] = self._irrigation_efficiency
        if hasattr(self, "_mask_map") and self._mask_map is not None:
            mask_map = to_absolute_path(self._mask_map)
            settings["MaskMap"] = str(mask_map.with_suffix(""))

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
    def parameters(self) -> dict[str, Any]:
        """List the parameters for this model."""
        return {
            "IrrigationEfficiency": self._get_textvar_value("IrrigationEfficiency"),
            "MaskMap": self._get_textvar_value("MaskMap"),
            "start_time": self._model_start_time.strftime(ISO_TIMEFMT),
            "end_time": self._model_end_time.strftime(ISO_TIMEFMT),
        }

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
