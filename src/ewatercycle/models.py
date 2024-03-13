"""Collection of models available in eWaterCycle.

Examples:

    To instantiate a model:

    >>> from ewatercycle.models import Wflow
    >>> model = Wflow()
    # Alternativly import it directly from plugin with
    >>> from ewaterycecle.plugins.wlow.model import Wflow

    To list all available models:

    >>> from ewatercycle.models import sources
    >>> sources
    # Returns dictionary containing models

To get your own model to be listed here it needs to be
registered in the :py:data:`ewatercycle.models`
`entry point group <https://packaging.python.org/en/latest/specifications/entry-points/>`_.
"""

from importlib.metadata import entry_points
from typing import Mapping, Type

from importlib_metadata import EntryPoint

from ewatercycle.base.model import eWaterCycleModel

_model_entrypoints = entry_points(group="ewatercycle.models")  # /NOSONAR

# Expose as "from ewatercycle.models import Model" for backward compatibility
for _model in _model_entrypoints:
    globals()[_model.name] = _model.load()


class ModelSources(Mapping):
    """Lazy dictionary to hold the different models.

    Properties can be accessed as attributes (with dot) or as keys (with [name]).
    """

    def __init__(self, *args, **kw):
        self._raw_dict = dict(*args, **kw)

    def __getitem__(self, key) -> Type[eWaterCycleModel]:
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


_models = {entry_point.name: entry_point for entry_point in _model_entrypoints}


sources = ModelSources(_models)
"""Dictionary filled with available models.

    Examples:

        List all available models:

        >>> from ewatercycle.models import sources
        >>> models.keys()
        ['Wflow', 'LeakyBucket', ...]

To get your own model to be listed here it needs to be
registered in the `ewatercycle.models`
`entry point group <https://packaging.python.org/en/latest/specifications/entry-points/>`_
.

"""
