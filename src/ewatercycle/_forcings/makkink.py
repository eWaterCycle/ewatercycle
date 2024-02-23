from ewatercycle.base.forcing import (
    DefaultForcing, DistributedUserForcing, LumpedUserForcing
)
from pathlib import Path
import xarray as xr
import numpy as np

from ewatercycle.esmvaltool.schema import Dataset


def derive_e_pot(recipe_output: dict):
    ds_tas = xr.open_dataset(
        Path(recipe_output["directory"]) / recipe_output["tas"]
    )
    ds_rsds = xr.open_dataset(
        Path(recipe_output["directory"]) / recipe_output["rsds"]
    )
    # We need to make sure the coordinates line up. Floating point errors from
    #  ESMValTool mess with this:
    for ds in [ds_tas, ds_rsds]:
        for coord in ["lat", "lon"]:
            # 7 decimals is sufficient for "waldo" precision (https://xkcd.com/2170/)
            ds[coord] = np.round(ds[coord], decimals=7)  

    da_et = et_makkink(ds_tas["tas"], ds_rsds["rsds"])
    da_et.attrs = {
        "standard_name": "water_potential_evaporation_flux", 
        "units": "kg m-2 s-1", 
        "long_name": "Potential Evapotranspiration", 
    }
    et_fname = "evspsblpot.nc"
    da_et.to_netcdf(Path(recipe_output["directory"]) / et_fname)
    recipe_output["evspsblpot"] = et_fname

    return ("evspsblpot", )


class Makkink(DefaultForcing):
    @classmethod
    def generate(  # type: ignore[override]
        cls: type["Makkink"],
        dataset: str | Dataset | dict,
        start_time: str,
        end_time: str,
        shape: str,
        directory: str | None = None,
        **model_specific_options,
    ) -> "Makkink":
        return super().generate(
            dataset,
            start_time,
            end_time,
            shape,
            directory,
            variables=("pr", "tas", "rsds"),
            postprocessor=derive_e_pot,
            **model_specific_options,
        )


class LumpedMakkinkForcing(Makkink, LumpedUserForcing):  # type: ignore[misc]
    ...

class DistributedMakkinkForcing(Makkink, DistributedUserForcing):  # type: ignore[misc]
    ...


def et_makkink(tas: xr.DataArray, rsds: xr.DataArray) -> xr.DataArray:
    """Compute the Makkink reference evaporation.

    Args:
        tas: Air temperature (K).
        rsds: Incoming solar radiation (W m-2).

    Returns:
        Makkink ET (kg m-2 s-1).
    """
    c1 = 0.65
    c2 = 0.
    gamma = 0.66
    labda = 2.45e6

    s = vapor_pressure_slope(tas) 
    
    et = (c1 * s / (s + gamma) * rsds + c2)/labda
    et.name = "evspsblpot"
    et.attrs = {
        "long_name": "potential evaporation",
        "units": "kg m-2 s-1",
    }
    return et


def vapor_pressure_slope(tas):
    """Compute the slope of the vapor pressure curve.

    Args:
        tas: Air temperature (K)

    Returns:
        Slope of the vapor pressure curve.
    """
    t = tas - 273.15
    a = 6.1078
    b = 17.294
    c = 237.74
    return (a*b*c) / (c + t)**2 * np.exp(b*t/(c+t))
