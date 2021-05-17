import shutil
import time
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

from dataclasses import dataclass
import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle import CFG
from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import CaseConfigParser


@dataclass
class PCRGlobWBParameterSet:
    """Parameter set for the PCRGlobWB model class.

    A valid pcrglobwb parameter set consists of a folder with input data files
    and should always include a default configuration file.
    """
    input_dir: Union[str, PathLike]
    """Input folder path."""
    default_config: Union[str, PathLike]
    """Path to (default) model configuration file consistent with `input_data`."""

    def __setattr__(self, name: str, value: Union[str, PathLike]):
        self.__dict__[name] = Path(value).expanduser().resolve()


class PCRGlobWB(AbstractModel):
    """eWaterCycle implementation of PCRGlobWB hydrological model.

    Attributes
        bmi (Bmi): GRPC4BMI Basic Modeling Interface object
    """
    def setup(  # type: ignore
            self,
            input_dir: PathLike,
            cfg_file: PathLike,
            additional_input_dirs: Iterable[PathLike] = [],
            **kwargs) -> Tuple[PathLike, PathLike]:
        """Start model inside container and return config file and work dir.

        Args:

            - input_dir: main input directory. Relative paths in the cfg_file
            should start from this directory.

            - cfg_file: path to a valid pcrglobwb configuration file,
            typically somethig like `setup.ini`.

            - additional_input_dirs: one or more additional data directories
            that the model will have access to.

            - **kwargs (optional, dict): any settings in the cfg_file that you
            want to overwrite programmatically. Should be passed as a dict,
            e.g. `meteoOptions = {"temperatureNC": "era5_tas_1990_2000.nc"}`
            where meteoOptions is the section in which the temperatureNC option
            may be found.

        Returns: Path to config file and work dir
        """
        self._setup_work_dir()
        self._setup_config(cfg_file, input_dir, **kwargs)
        self._start_container(input_dir, additional_input_dirs)

        return self.cfg_file, self.work_dir,

    def _setup_work_dir(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        work_dir = Path(CFG["output_dir"]) / f'pcrglobwb_{timestamp}'
        work_dir.mkdir()
        self.work_dir = work_dir.resolve()
        print(f"Created working directory: {work_dir}")

    def _setup_config(self, cfg_file: PathLike, input_dir: PathLike, **kwargs):
        cfg = CaseConfigParser()
        cfg.read(cfg_file)
        self.cfg = cfg

        full_input_path = Path(input_dir).resolve()
        cfg.set('globalOptions', 'inputDir', str(full_input_path))
        cfg.set('globalOptions', 'outputDir', str(self.work_dir))

        for section, options in kwargs.items():
            for option, value in options.items():
                cfg.set(section, option, value)

        new_cfg_file = Path(self.work_dir) / "pcrglobwb_ewatercycle.ini"
        with new_cfg_file.open("w") as filename:
            cfg.write(filename)

        self.cfg_file = new_cfg_file.resolve()
        print(f"Created config file {self.cfg_file} with inputDir "
              f"{full_input_path} and outputDir {self.work_dir}.")

    def _start_container(self,
                         input_dir: PathLike,
                         additional_input_dirs: Iterable[PathLike] = []):
        input_dirs = [input_dir] + list(additional_input_dirs)

        if CFG["container_engine"] == "docker":
            self.bmi = BmiClientDocker(
                image=CFG["pcrglobwb.docker_image"],
                image_port=55555,
                work_dir=str(self.work_dir),
                input_dirs=[str(input_dir) for input_dir in input_dirs],
                timeout=10,
            )
        elif CFG["container_engine"] == "singularity":
            image = CFG["pcrglobwb.singularity_image"]

            message = f"No singularity image found at {image}"
            assert Path(image).exists(), message

            self.bmi = BmiClientSingularity(
                image=image,
                work_dir=str(self.work_dir),
                input_dirs=[str(input_path) for input_path in input_dirs],
                timeout=10,
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )

        inputs = "\n".join([str(Path(p).resolve()) for p in input_dirs])
        print(
            f"Started model container with working directory {self.work_dir} "
            f"and access to the following input directories:\n{inputs}.")

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        """Return the value as xarray object."""
        # Get time information
        time_units = self.bmi.get_time_units()
        grid = self.bmi.get_var_grid(name)
        shape = self.bmi.get_grid_shape(grid)

        # Extract the data and store it in an xarray DataArray
        da = xr.DataArray(
            data=np.reshape(self.bmi.get_value(name), shape),
            coords={
                "longitude": self.bmi.get_grid_y(grid),
                "latitude": self.bmi.get_grid_x(grid),
                "time": num2date(self.bmi.get_current_time(), time_units)
            },
            dims=["latitude", "longitude"],
            name=name,
            attrs={"units": self.bmi.get_var_units(name)},
        )

        return da.where(da != -999)

    @property
    def parameters(self) -> Iterable[Tuple[str, Any]]:
        """List the configurable parameters for this model."""
        if not hasattr(self, "cfg"):
            raise NotImplementedError(
                "No default parameters available for pcrglobwb. To see the "
                "parameters, first run setup with a valid .ini file.")

        return [(f"{section}.{option}", f"{self.cfg.get(section, option)}")
                for section in self.cfg.sections()
                for option in self.cfg.options(section)]
