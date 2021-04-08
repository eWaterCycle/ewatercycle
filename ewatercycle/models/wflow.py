from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

import numpy as np
import xarray as xr
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle.models.abstract import AbstractModel

# from ewatercycle import CFG

# mock CFG until the CFG PR is merged.
CFG = {
    "container_engine": "singularity",
    "singularity_images.wflow": "ewatercycle-wflow-grpc4bmi.sif",
    "docker_images.wflow": "ewatercycle/wflow-grpc4bmi:latest",
}


class Wflow(AbstractModel):
    """eWaterCycle implementation of WFLOW hydrological model.

    Attributes
        bmi (Bmi): GRPC4BMI Basic Modeling Interface object
    """
    def setup(self,
              work_dir: Path,
              inifile: Path,
              parameterset: Optional[Path] = None,
              forcing_data: Optional[Path] = None):
        """Performs model setup.

        1. Creates config file and config directory
        2. Start bmi container and store as self.bmi

        Args:

            - work_dir: a writable folder that will be used as the main working
            directory for running the model

            - inifile: path to the configuration file, typically somethig like
            `work_dir/wflow_sbm.ini`

            - parameterset (optional): path to a valid wflow model spec. If
            given, the parameterset will be copied to `work_dir`

            - forcing_data: path to meteorological forcing data (.nc) file. If
            given, will be copied to work_dir. If not given, it should already
            be there.

        Returns:
            Path to config file and path to config directory
        """
        # work_dir = ....
        config_file = work_dir / inifile.name

        # For Wflow we have to copy the input (which is unwritable)
        # to a working directory (what is writable)
        shutil.copytree(src=parameterset, dst=work_dir)
        shutil.copy(src=forcing_file, dst=work_dir)

        # Modify the path to the forcing data in the config file
        cfg = ConfigParser()
        cfg.optionxform = lambda x: x
        cfg.read(inifile)
        cfg.set("framework", "netcdfinput", forcing_file.name)
        with open(config_file, "w") as filename:
            cfg.write(filename)

        # Start the container
        if CFG.container_engine.lower() == "docker":
            self.bmi = BmiClientDocker(
                image=CFG["docker_images.wflow"],
                image_port=55555,
                work_dir=work_dir,
            )
        elif CFG.container_engine.lower() == "singularity":
            self.bmi = BmiClientSingularity(
                image=CFG["singularity_images.wflow"],
                work_dir=work_dir,
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG['container_engine']}"
            )

        return config_file

    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        # TODO this is just copied from the comparison notebook.
        # TODO update this so it can work as standalone code

        # Let's analyse runoff
        variable = "RiverRunoff"

        # Get time information
        time_units = model.get_time_units()
        now = num2date(model.get_current_time(), time_units)

        # Get data (and convert to something that's nice in xarray)
        grid = model.get_var_grid(variable)

        # Get the model's internal configuration
        lat = model.get_grid_x(grid)
        lon = model.get_grid_y(grid)
        shape = model.get_grid_shape(grid)

        # Extract the data and store it in an xarray DataArray
        data = np.reshape(model.get_value(variable), shape)
        da = xr.DataArray(
            data,
            coords={
                "longitude": lon,
                "latitude": lat,
                "time": now
            },
            dims=["latitude", "longitude"],
            name=variable,
            attrs={"units": model.get_var_units(variable)},
        )

        da.data = np.reshape(model.get_value(variable), shape)
        da.time.values = num2date(model.get_current_time(), time_units)
        return da.where(da != -999)

    @property
    def parameters(self):
        """List the variable names that are available for this model."""
        return self.model.get_output_var_names()
