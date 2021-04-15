import shutil
import time
from os import PathLike
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle.models.abstract import AbstractModel
from ewatercycle.parametersetdb.config import CaseConfigParser

# from ewatercycle import CFG

# mock CFG until the CFG PR is merged.
CFG = {
    "container_engine": "docker",
    "singularity_images.wflow": "ewatercycle-wflow-grpc4bmi.sif",
    "docker_images.wflow": "ewatercycle/wflow-grpc4bmi:latest",
    "scratch_dir": "./"
}


class Wflow(AbstractModel):
    """eWaterCycle implementation of WFLOW hydrological model.

    Attributes
        bmi (Bmi): GRPC4BMI Basic Modeling Interface object
    """
    def setup(  # type: ignore
            self, cfg_dir: PathLike, cfg_file: PathLike,
            **kwargs) -> Tuple[PathLike, PathLike]:
        """Start the model inside a container and return a valid config file.

        Args:

            - cfg_dir: path to a valid wflow model spec.

            - cfg_file: path to the configuration file, typically somethig like
            `wflow_sbm.ini`. This overwrites any existing files in cfg_dir with
            the same filename.

            - **kwargs (optional, dict): any settings in the cfg_file that you want
            to overwrite programmatically. Should be passed as a dict, e.g.
            `run = {"starttime": "1995-01-31 00:00:00 GMT"}` where run is the
            section in which the starttime option may be found.

        Returns:
            Path to config file and config dir
        """
        self._setup_cfg_dir(cfg_dir=cfg_dir)
        self._setup_cfg_file(cfg_file=cfg_file, **kwargs)
        self._start_container()

        return self.cfg_file, self.cfg_dir,

    def _setup_cfg_dir(self, cfg_dir: PathLike):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        work_dir = Path(CFG["scratch_dir"]) / f'wflow_{timestamp}'
        shutil.copytree(src=cfg_dir, dst=work_dir)
        self.cfg_dir = work_dir.resolve()
        print(f"Working directory created: {work_dir}")

    def _setup_cfg_file(self, cfg_file: PathLike, **kwargs):
        cfg = CaseConfigParser()
        cfg.read(cfg_file)
        self.cfg = cfg

        for section, options in kwargs.items():
            for option, value in options.items():
                cfg.set(section, option, value)

        new_cfg_file = Path(self.cfg_dir) / "wflow_ewatercycle.ini"
        with new_cfg_file.open("w") as filename:
            cfg.write(filename)

        self.cfg_file = new_cfg_file.resolve()
        print(f"Created {self.cfg_file}.")

    def _start_container(self):
        if CFG["container_engine"] == "docker":
            self.bmi = BmiClientDocker(
                image=CFG["docker_images.wflow"],
                image_port=55555,
                work_dir=str(self.cfg_dir),
                timeout=10,
            )
        elif CFG["container_engine"] == "singularity":
            image = CFG["singularity_images.wflow"]

            message = f"No singularity image found at {image}"
            assert Path(image).exists(), message

            self.bmi = BmiClientSingularity(
                image=image,
                work_dir=str(self.cfg_dir),
                timeout=10,
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )
        print(f"Started wflow container with working directory {self.cfg_dir}")

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
                "No default parameters available for wflow. To see the "
                "parameters, first run setup with a valid .ini file.")

        return [(f"{section}.{option}", f"{self.cfg.get(section, option)}")
                for section in self.cfg.sections()
                for option in self.cfg.options(section)]
