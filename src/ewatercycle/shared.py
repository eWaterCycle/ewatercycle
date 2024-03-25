from abc import abstractmethod
from collections.abc import Mapping

from importlib_metadata import EntryPoint


class Sources(Mapping):
    """Lazy dictionary to hold the different models/forcings/parametersets.

    Properties can be accessed as attributes (with dot) or as keys (with [name]).
    """

    def __init__(self, *args, **kw):
        self._raw_dict = dict(*args, **kw)

    def __getitem__(self, key):
        """Get the entry point, loads it, and returns the object."""
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
        return (
            f"{self.__class__.__name__}[\n"
            '    "' + '",\n    "'.join(sorted(self._raw_dict.keys())) + '"\n]'
        )

    def __rich__(self):
        """Pretty print using rich."""
        return (
            f"[blue]{self.__class__.__name__}[\n[green]"
            '    "' + '",\n    "'.join(sorted(self._raw_dict.keys())) + '",\n[blue]]'
        )
