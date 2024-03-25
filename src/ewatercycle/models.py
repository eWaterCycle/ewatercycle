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
from typing import Type

from ewatercycle import shared
from ewatercycle.base.model import eWaterCycleModel

_model_entrypoints = entry_points(group="ewatercycle.models")  # /NOSONAR

# Expose as "from ewatercycle.models import Model" for backward compatibility
for _model in _model_entrypoints:
    globals()[_model.name] = _model.load()


class ModelSources(shared.Sources):
    """Dictionary filled with available models.

        Examples:

            Get a nice overview of the available models:

            >>> from ewatercycle.models import sources
            >>> print(sources)
            ...

            List the names of the available models:

            >>> from ewatercycle.models import sources
            >>> sources.keys()
            ['Wflow', 'LeakyBucket', ...]

            Access one of the models:

            >>> from ewatercycle.models import sources
            >>> sources["Wflow"]
            model = sources["Wflow"]()

    To get your own model to be listed here it needs to be
    registered in the `ewatercycle.models`
    `entry point group <https://packaging.python.org/en/latest/specifications/entry-points/>`_
    .

    """

    def __getitem__(self, key) -> Type[eWaterCycleModel]:
        """Get the entry point, loads it, and returns the model object."""
        return super().__getitem__(key)


_models = {entry_point.name: entry_point for entry_point in _model_entrypoints}


sources = ModelSources(_models)
