"""Forcing module of eWaterCycle. Contains the model sources."""
from importlib.metadata import entry_points
from collections.abc import Mapping


class ForcingSources(Mapping):
    """Lazy dictionary to hold the different forcing sources.
    
    The `sources` object holds the forcing sources.
    Forcing can be generated for a specifc source by doing, for example:
        `from ewatercycle.forcing import sources`,
        `forcing = sources.MarrmotForcing.generate(...)`
    """
    def __init__(self, *args, **kw):
        self._raw_dict = dict(*args, **kw)

    def __getitem__(self, key):
        """Gets the entry point, loads it, and returns the Forcing object."""
        return self._raw_dict[key].load()

    def __getattr__(self, attr):
        """Accesses the keys like attributes. E.g. sources.HypeForcing."""
        if attr in self._raw_dict.keys():
            return self[attr]
        else:
            return getattr(self._raw_dict, attr)

    def __iter__(self):
        return iter(self._raw_dict)

    def __len__(self):
        return len(self._raw_dict)
    
    def __repr__(self):
        return self.__class__.__name__ + str(list(self._raw_dict.keys()))


sources = ForcingSources({
    entry_point.name: entry_point
    for entry_point in entry_points(group="ewatercycle.forcings")
})
