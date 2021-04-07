from typing import Any, Iterable, Optional, Tuple

import numpy as np
import xarray as xr

from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity

from ewatercycle.models.abstract import AbstractModel
from ewatercycle import CFG


class Wflow(AbstractModel):
    """eWaterCycle implementation of WFLOW hydrological model.

    Attributes
        bmi (Bmi): Basic Modeling Interface object
    """
    def setup(self):
        """Performs model setup.

        1. Creates config file and config directory
        2. Start bmi container and store as self.bmi

        Args:
            *args: Positional arguments. Sub class should specify each arg.  # TODO
            **kwargs: Named arguments. Sub class should specify each arg.    # TODO

        Returns:
            Path to config file and path to config directory
        """
        config_file, config_dir = self._create_config()

        if CFG.container_engine.lower() == "docker":
            container_engine = BmiClientDocker
            container_image = "ewatercycle/wflow-grpc4bmi:latest"  # TODO Get from config?
        elif CFG.container_engine.lower() == "singularity":
            container_engine = BmiClientSingularity
            container_image = "ewatercycle-wflow-grpc4bmi.sif"     # TODO Get from config?
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG.container_engine}"
            )

        self.bmi = container_engine(
            image=container_image,
            work_dir=str(TEMP_DIR)                   # TODO Get from config
        )

        self.bmi.initialize(str(config_file))

    def _create_config(self):
        # TODO this is just copied from the comparison notebook.
        # TODO update this so it can work as standalone code
        INPUT_DIR = (
            PROJECT_HOME / "wflow_parameterset"
            / "calibrated_parameterset" / catchment.lower()
        )
        config_template = f"{INPUT_DIR}/wflow_sbm_{dataset.lower()}_warmup.ini"

        # Open default config file
        cfg = ConfigParser()
        cfg.optionxform = lambda x: x
        cfg.read(f"{TEMP_DIR}/wflow_sbm_{dataset.lower()}_warmup.ini")  # reinit=1

        # Modify settings
        start = PERIOD["start"].strftime("%Y-%m-%d")
        end = PERIOD["end"].strftime("%Y-%m-%d")
        cfg.set("framework", "netcdfinput", Path(forcing).name)
        cfg.set("run", "starttime", f"{start} 12:00:00 GMT")
        cfg.set("run", "endtime", f"{end} 12:00:00 GMT")
        cfg.set("inputmapstacks", "Precipitation", "/pr")
        cfg.set("inputmapstacks", "EvapoTranspiration", "/pet")
        cfg.set("inputmapstacks", "Temperature", "/tas")

        # Add API fields to the config file
        cfg["API"] = {
            "RiverRunoff": "2, m^3/s",
        }

        # Remove sections/options that break the BMI
        cfg.remove_option("framework", "netcdfoutput")
        cfg.remove_section("outputcsv_0")
        cfg.remove_section("outputcsv_1")
        cfg.remove_section("outputcsv_2")
        cfg.remove_section("outputcsv_3")
        cfg.remove_section("outputtss_0")

        # Write to new config file
        cfg_file = TEMP_DIR / f"wflow_sbm_{catchment}_{dataset}_warmup.ini"
        with open(cfg_file, "w") as file:
            cfg.write(file)

        return config_file, config_dir

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
            coords={"longitude": lon, "latitude": lat, "time": now},
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
