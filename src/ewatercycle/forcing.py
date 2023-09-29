"""Forcing module of eWaterCycle. Contains the forcing sources."""
from collections.abc import Mapping
from importlib.metadata import entry_points
from typing import Any, Type

from importlib_metadata import EntryPoint

from ewatercycle.base.forcing import (
    DefaultForcing,
    GenericDistributedForcing,
    GenericLumpedForcing,
)


class ForcingSources(Mapping):
    """Lazy dictionary to hold the different forcing sources.

    Properties can be accessed as attributes (with dot) or as keys (with [name]).
    """

    def __init__(self, *args, **kw):
        self._raw_dict = dict(*args, **kw)

    def __getitem__(self, key) -> Type[DefaultForcing]:
        """Get the entry point, loads it, and returns the Forcing object."""
        if isinstance(self._raw_dict[key], EntryPoint):
            return self._raw_dict[key].load()
        else:
            return self._raw_dict[key]

    def __getattr__(self, attr):
        """Access the keys like attributes. E.g. sources.HypeForcing."""
        if attr in self._raw_dict.keys():
            return self.__getitem__(attr)
        else:
            return getattr(self._raw_dict, attr)

    def __iter__(self):
        return iter(self._raw_dict)

    def __len__(self):
        return len(self._raw_dict)

    def __repr__(self):
        return self.__class__.__name__ + str(list(self._raw_dict.keys()))


_forcings: dict[str, Any] = {
    "GenericDistributedForcing": GenericDistributedForcing,
    "GenericLumpedForcing": GenericLumpedForcing,
}
_forcings.update(
    {
        entry_point.name: entry_point
        for entry_point in entry_points(group="ewatercycle.forcings")  # /NOSONAR
    }
)

sources = ForcingSources(_forcings)
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
