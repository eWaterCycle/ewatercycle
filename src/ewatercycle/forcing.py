"""Forcing module of eWaterCycle. Contains the forcing sources."""
from importlib.metadata import entry_points
from typing import Any, Type

from ewatercycle import shared
from ewatercycle._forcings.caravan import CaravanForcing
from ewatercycle._forcings.makkink import (
    DistributedMakkinkForcing,
    LumpedMakkinkForcing,
)
from ewatercycle.base.forcing import (
    DefaultForcing,
    DistributedUserForcing,
    GenericDistributedForcing,
    GenericLumpedForcing,
    LumpedUserForcing,
)


class ForcingSources(shared.Sources):
    """Dictionary filled with available forcing sources.

    Examples:

        List all available forcing sources:

        >>> from ewatercycle.forcing import sources
        >>> sources.keys()
        ['DefaultForcing', 'MarrmotForcing', ...]

        Forcing can be generated for a specifc source by doing

        >>> from ewatercycle.forcing import sources
        >>> forcing = sources['MarrmotForcing'].generate(...)

        A forcing can be generated from files on disk with something like

        >>> from ewatercycle.forcing import sources
        >>> forcing = sources.DefauitForcing(
            directory="path/to/forcing/directory",
            start_time="2000-01-01",
            end_time="2001-12-31",
        )

        A previously saved forcing can be loaded with

        >>> from ewatercycle.forcing import sources
        >>> forcing = sources.DefaultForcing.load("path/to/forcing/directory")

    To get your own forcing source to be listed here it needs to be
    registered in the `ewatercycle.forcings`
    `entry point group <https://packaging.python.org/en/latest/specifications/entry-points/>`_
    .

    """

    def __getitem__(self, key) -> Type[DefaultForcing]:
        """Get the entry point, loads it, and returns the Forcing object."""
        return super().__getitem__(key)


_forcings: dict[str, Any] = {
    "GenericDistributedForcing": GenericDistributedForcing,
    "GenericLumpedForcing": GenericLumpedForcing,
    "DistributedUserForcing": DistributedUserForcing,
    "LumpedUserForcing": LumpedUserForcing,
    "DistributedMakkinkForcing": DistributedMakkinkForcing,
    "LumpedMakkinkForcing": LumpedMakkinkForcing,
    "CaravanForcing": CaravanForcing,
}
_forcings.update(
    {
        entry_point.name: entry_point
        for entry_point in entry_points(group="ewatercycle.forcings")  # /NOSONAR
    }
)

sources = ForcingSources(_forcings)
