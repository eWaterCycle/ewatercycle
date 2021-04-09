import shutil
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

import numpy as np
import xarray as xr
from cftime import num2date
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle.models.abstract import AbstractModel

# from ewatercycle import CFG

# mock CFG until the CFG PR is merged.
CFG = {
    "container_engine": "docker",
    "singularity_images.wflow": "ewatercycle-wflow-grpc4bmi.sif",
    "docker_images.wflow": "ewatercycle/wflow-grpc4bmi:latest",
}


class Wflow(AbstractModel):
    """eWaterCycle implementation of WFLOW hydrological model.

    Attributes
        bmi (Bmi): GRPC4BMI Basic Modeling Interface object
    """
    def setup(self,
              work_dir: str,
              inifile: str,
              parameterset: Optional[str] = None,
              forcing_data: Optional[str] = None):
        """Start the model inside a container and return a valid config file.

        Args:

            - work_dir: a writable folder that will be used as the main working
            directory for running the model. This directory should either be
            pre-populated with valid parametersets and forcing, or the user
            should specify the additional arguments `parameterset` and
            `forcing_data`.

            - inifile: path to the configuration file, typically somethig like
            `wflow_sbm.ini`.

            - parameterset (optional): path to a valid wflow model spec. If
            given, the parameterset will be copied to `work_dir`. This is useful
            if you can't or don't want to write to this folder.

            - forcing_data: path to meteorological forcing data (.nc) file. If
            given, will be copied to work_dir. If not given, it should already
            be there.

        Returns:
            Path to config file
        """
        config_file = Path(work_dir) / Path(inifile).name

        if parameterset is not None:
            shutil.copytree(src=parameterset, dst=work_dir)

        if forcing_data is not None:
            shutil.copy(src=forcing_file, dst=work_dir)

            cfg = ConfigParser()
            cfg.optionxform = lambda x: x
            cfg.read(inifile)
            cfg.set("framework", "netcdfinput", Path(forcing_file).name)

            with open(config_file, "w") as filename:
                cfg.write(filename)

        # Start the container
        if CFG["container_engine"] == "docker":
            self.bmi = BmiClientDocker(
                image=CFG["docker_images.wflow"],
                image_port=55555,
                work_dir=work_dir,
                timeout=10,
            )
        elif CFG["container_engine"] == "singularity":
            image = CFG["singularity_images.wflow"]
            assert Path(
                image).exists(), f"No singularity image found at {image}"
            self.bmi = BmiClientSingularity(
                image=image,
                work_dir=work_dir,
                timeout=10,
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )

        print(f"Started Wflow container with working directory {work_dir}")
        return config_file.name

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
    def parameters(self):
        """List the variable names that are available for this model."""
        return self.bmi.get_output_var_names()
