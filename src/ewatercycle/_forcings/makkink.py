from typing import Callable, ClassVar
from ewatercycle.base.forcing import DefaultForcing, GenericLumpedForcing, GenericDistributedForcing
from pathlib import Path
import xarray as xr
import numpy as np


def derive(forcing_files: dict):
    ds_tas = xr.open_dataset(
        Path(forcing_files["directory"]) / forcing_files["tas"]
    )
    ds_rsds = xr.open_dataset(
        Path(forcing_files["directory"]) / forcing_files["rsds"]
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
    da_et.to_netcdf(Path(forcing_files["directory"]) / et_fname)
    forcing_files["evspsblpot"] = et_fname


class Makkink(DefaultForcing):
    _preprocessor: Callable | None = derive

    variables: ClassVar[tuple[str, ...]] = ("pr", "tas", "rsds")
    derived_variables: ClassVar[tuple[str, ...]] = ("evspsblpot",)


class LumpedMakkinkForcing(Makkink, GenericLumpedForcing):
    ...

class DistributedMakkinkForcing(Makkink, GenericDistributedForcing):
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
