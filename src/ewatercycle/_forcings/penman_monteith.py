from ewatercycle.base.forcing import (
    DefaultForcing,
    DistributedUserForcing,
    LumpedUserForcing,
)
from ewatercycle.esmvaltool.schema import Dataset


class PenmanMonteith(DefaultForcing):
    """Forcing object with variables for computing the Penman-Monteith equation.

    Contains the following variables:
        pr - precipitation
        tas - near-surface air temperature
        hurs - near-surface relative humidity
        sfcWind - near-surface wind speed
        rsds - near-surface downwelling shortwave radiation
        rsus - near-surface upwelling shortwave radiation
        rlds - near-surface downwelling longwave radiation
        rlus - near-surface upwelling longwave radiation

    Which together with the following local parameters is sufficient to solve the
    Penman-Monteith equation (ignoring ground heat flux, FAO 56).

    Do note that the "near-surface" height in weather and climate models is usually
    10 m. The exact surface height of each variable can be retrieved from the variable's
    attributes, if this information was present in the CMORized data.

    FAO 56: https://www.fao.org/3/x0490e/x0490e06.htm
    """

    @classmethod
    def generate(  # type: ignore[override]
        cls: type["PenmanMonteith"],
        dataset: str | Dataset | dict,
        start_time: str,
        end_time: str,
        shape: str,
        directory: str | None = None,
        **model_specific_options,
    ) -> "PenmanMonteith":
        return super().generate(
            dataset,
            start_time,
            end_time,
            shape,
            directory,
            variables=("pr", "tas", "hurs", "sfcWind", "rsds", "rlds", "rsus", "rlus"),
            postprocessor=None,
            **model_specific_options,
        )


class LumpedPenmanMonteithForcing(PenmanMonteith, LumpedUserForcing):  # type: ignore[misc]
    ...


class DistributedPenmanMonteithForcing(PenmanMonteith, DistributedUserForcing):  # type: ignore[misc]
    ...
