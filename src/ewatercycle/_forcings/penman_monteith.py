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


def derive_pm_variables(recipe_output: dict) -> tuple[str, ...]:
    """Derive the required variables from the recipe output.

    ERA5 and CMIP available variables differ. By computing the net radiation (for
    both) and the surface wind (ERA5 only) the output data will be the same for each
    dataset.
    """
    return (
        derive_net_radiation(recipe_output)
        + derive_surface_wind(recipe_output)
        + derive_vpd(recipe_output)
    )


class PenmanMonteith(DefaultForcing):
    """Forcing object with variables for computing the Penman-Monteith equation.

    Contains the following variables:
        pr - precipitation
        tas - near-surface air temperature
        vpds - near-surface water vapor pressure deficit
        sfcWind - near-surface wind speed
        rn - net radiation

    Which together with the following local parameters is sufficient to solve the
    Penman-Monteith equation (ignoring ground heat flux, FAO 56).

    Do note that the "near-surface" height in weather and climate models is usually
    10 m. The exact surface height of each variable can be retrieved from the variable's
    attributes, if this information was present in the CMORized data.

    FAO 56: https://www.fao.org/3/x0490e/x0490e06.htm

    Note on derived variables:
        For ERA5 the net radiation is derived from:
            rss - near-surface net shortwave radiation
            rls - near-surface net longwave radiation

        For ERA5 the near-surface wind speed is derived from the horizontal components:
            uas - eastward near-surface wind
            vas - northward near-surface wind

        For ERA5 the vapor pressure deficit is derived from:
            tas - near-surface air temperature
            tdps - near-surface dewpoint temperature

        For CMIP6 the net radiation is derived from:
            rsds - near-surface downwelling shortwave radiation
            rsus - near-surface upwelling shortwave radiation
            rlds - near-surface downwelling longwave radiation
            rlus - near-surface upwelling longwave radiation

        For CMIP6 the vapor pressure deficit is derived from:
            tas - near-surface air temperature
            hurs - near-surface relative humidity
    """

    @classmethod
    def generate(  # type: ignore[override]
        cls: type["PenmanMonteith"],
        dataset: str | Dataset | dict,
        start_time: str,
        end_time: str,
        shape: str | Path,
        directory: str | None = None,
        **model_specific_options,
    ) -> "PenmanMonteith":
        variables: tuple[str, ...]
        if (
            (isinstance(dataset, str) and dataset == "ERA5")
            or (isinstance(dataset, dict) and dataset["project"] == "ERA5")
            or (isinstance(dataset, Dataset) and dataset.project == "ERA5")
        ):
            variables = ("pr", "tas", "tdps", "uas", "vas", "rss", "rls")

        elif (isinstance(dataset, dict) and dataset["project"] == "CMIP6") or (
            isinstance(dataset, Dataset) and dataset.project == "CMIP6"
        ):
            variables = ("pr", "tas", "hurs", "sfcWind", "rsds", "rlds", "rsus", "rlus")

        else:
            msg = (
                "The entered dataset is not supported for this forcing generator."
                "Only ERA5 and CMIP6 are supported."
            )
            raise ValueError(msg)

        return super().generate(
            dataset,
            start_time,
            end_time,
            shape,
            directory,
            variables=variables,
            postprocessor=derive_pm_variables,
            **model_specific_options,
        )


class LumpedPenmanMonteithForcing(PenmanMonteith, LumpedUserForcing):  # type: ignore[misc]
    ...


class DistributedPenmanMonteithForcing(PenmanMonteith, DistributedUserForcing):  # type: ignore[misc]
    ...


def derive_surface_wind(recipe_output: dict) -> tuple[str, ...]:
    """Derive the surface wind speed if missing (i.e. for ERA5 data)."""

    if "sfcWind" in recipe_output:
        # Already present, no need to compute
        return tuple()

    ds = merge_esvmaltool_datasets(
        [
            xr.open_dataset(Path(recipe_output["directory"]) / recipe_output["uas"]),
            xr.open_dataset(Path(recipe_output["directory"]) / recipe_output["vas"]),
        ]
    )
    da_sfcWind = (ds["uas"] ** 2 + ds["vas"] ** 2) ** 0.5

    fname = "derived_sfcWind.nc"

    da_sfcWind.attrs.update(
        {
            "standard_name": "wind_speed",
            "long_name": "Daily-Mean Near-Surface Wind Speed",
            "units": "m s-1",
            "cell_methods": "area: time: mean",
            "height": ds["uas"].attrs["height"],
        }
    )

    da_sfcWind.to_netcdf(Path(recipe_output["directory"]) / fname)
    recipe_output["sfcWind"] = fname
    return ("sfcWind",)


def derive_net_radiation(recipe_output: dict) -> tuple[str, ...]:
    """Derive the surface net radiation from its components.

    CMIP models generally have 4 components (longwave, shortwave, each up & down).
    ERA5 has 2 components (net longwave, net shortwave).

    For Penman-Monteith only net radiation is required.
    """
    if "rss" in recipe_output:  # ERA output
        ds = merge_esvmaltool_datasets(
            [
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["rss"]
                ),
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["rls"]
                ),
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["uas"]
                ),
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["vas"]
                ),
            ]
        )
        da_rn = ds["rss"] + ds["rls"]

    else:  # CMIP output
        ds = merge_esvmaltool_datasets(
            [
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["rsds"]
                ),
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["rsus"]
                ),
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["rlds"]
                ),
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["rlus"]
                ),
            ]
        )
        da_rn = ds["rsds"] + ds["rlds"] - ds["rsus"] - ds["rlus"]

    fname = "derived_rn.nc"

    da_rn.name = "rn"
    da_rn.attrs.update(
        {
            "standard_name": "surface_net_downward_radiative_flux",
            "long_name": "Net surface radiation",
            "units": "W m-2",
            "positive": "down",
        }
    )

    da_rn.to_netcdf(Path(recipe_output["directory"]) / fname)
    recipe_output["rn"] = fname
    return ("rn",)


def derive_vpd(recipe_output: dict) -> tuple[str, ...]:
    # Work around for misaligned bounds.
    # I think the diagnostic script incorrectly puts this on Eday...
    if "tdps" in recipe_output:
        fpath = Path(recipe_output["directory"]) / recipe_output["tdps"]
        ds = xr.open_dataset(fpath).drop("time_bnds").compute()
        ds.close()
        ds.to_netcdf(fpath)

    if "rss" in recipe_output:  # ERA output
        ds = merge_esvmaltool_datasets(
            [
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["tas"]
                ),
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["tdps"]
                ),
            ]
        )
        da_vpd = vpd_from_tdp(ds["tas"], ds["tdps"])

    else:  # CMIP output
        ds = merge_esvmaltool_datasets(
            [
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["tas"]
                ),
                xr.open_dataset(
                    Path(recipe_output["directory"]) / recipe_output["hurs"]
                ),
            ]
        )
        da_vpd = vpd_from_hur(ds["tas"], ds["hurs"])

    fname = "derived_vpd.nc"

    da_vpd.name = "vpds"
    da_vpd.attrs.update(
        {
            "standard_name": "water_vapor_saturation_deficit_in_air",
            "long_name": "Vapor pressure deficit at the surface",
            "units": "Pa",
        }
    )

    da_vpd.to_netcdf(Path(recipe_output["directory"]) / fname)
    recipe_output["vpds"] = fname
    return ("vpds",)


def vpd_from_tdp(tas: xr.DataArray, tdps: xr.DataArray):
    """Derive the vapor pressure deficit from air temperature and dew point temperature.

    vpd = e_s - e_a

    where e_s is the saturation vapor pressure and e_a is the actual vapor pressure.
    """
    return vapor_pressure(tas) - vapor_pressure(tdps)


def vpd_from_hur(tas: xr.DataArray, hurs: xr.DataArray) -> xr.DataArray:
    """Derive the vapor pressure deficit from air temperature and relative humidity.


    vpd = e_s - e_a
    and: e_a = h * e_s / 100
    thus: vpd = e_s * (1 - h/100)

    where e_s is the saturation vapor pressure, e_a the actual vapor pressure, h the
    relative humidity (%).
    """
    return vapor_pressure(tas) * (1 - hurs / 100)


def vapor_pressure(temperature: xr.DataArray) -> xr.DataArray:
    """Compute the vapor pressure at a certain temperature. Uses the Tetens equation.

    Note: output is in Pa, input temperature in Kelvin.

    Reference:
        Monteith, J.L., and Unsworth, M.H. 2008. Principles of Environmental Physics.
         Third Ed. AP, Amsterdam.
    """
    temperature_C = temperature + 273.15
    vpd_kpa = 0.61078 * np.exp(17.27 * temperature_C) / (temperature_C + 237.3)
    return vpd_kpa * 1000  # type: ignore
