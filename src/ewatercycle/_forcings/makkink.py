from pathlib import Path

import numpy as np
import xarray as xr

from ewatercycle.base.forcing import (
    DefaultForcing,
    DistributedUserForcing,
    LumpedUserForcing,
)
from ewatercycle.esmvaltool.schema import Dataset
from ewatercycle.util import merge_esvmaltool_datasets


def derive_e_pot(recipe_output: dict) -> tuple[str, ...]:
    """Derive the Makkink PET from the ESMValTool recipe output."""
    ds_tas = xr.open_dataset(
        Path(recipe_output["directory"]) / recipe_output["tas"],
        chunks="auto",
    )
    ds_rsds = xr.open_dataset(
        Path(recipe_output["directory"]) / recipe_output["rsds"],
        chunks="auto",
    )
    # We need to make sure the coordinates line up. Floating point errors from
    #  ESMValTool mess with this:
    ds = merge_esvmaltool_datasets([ds_tas, ds_rsds])

    da_et = et_makkink(ds["tas"], ds["rsds"])
    et_fname = "Derived_Makkink_evspsblpot.nc"
    da_et.to_netcdf(Path(recipe_output["directory"]) / et_fname)
    recipe_output["evspsblpot"] = et_fname

    return ("evspsblpot",)


class Makkink(DefaultForcing):
    """Forcing object with derived potential evaporatin using the Makkink equation.

    Contains the following variables:
        pr - precipitation
        tas - near-surface air temperature
        rsds - near-surface downwelling shortwave radiation
        evspsblpot - potential evaporation flux
    """

    @classmethod
    def generate(  # type: ignore[override]
        cls: type["Makkink"],
        dataset: str | Dataset | dict,
        start_time: str,
        end_time: str,
        shape: str | Path,
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

    Reference:
        de Bruin, H., 1987. From penman to makkink. In: Hooghart, C. (Ed.),
            Evaporation and Weather: Proceedings and Information. Vol. 28. TNO committee
            on Hydrological Research: The Hague, pp. 5-30.
    """
    c1 = 0.65
    c2 = 0.0
    gamma = 0.66
    labda = 2.45e6

    s = vapor_pressure_slope(tas)

    et = (c1 * s / (s + gamma) * rsds + c2) / labda
    et.name = "evspsblpot"
    et.attrs = {
        "standard_name": "water_potential_evaporation_flux",
        "units": "kg m-2 s-1",
        "long_name": "potential evaporation",
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
    return (a * b * c) / (c + t) ** 2 * np.exp(b * t / (c + t))
