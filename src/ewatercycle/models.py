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

from importlib.metadata import entry_points, packages_distributions
from typing import Type

from ewatercycle import shared
from ewatercycle.base.model import eWaterCycleModel

_model_entrypoints = entry_points(group="ewatercycle.models")  # /NOSONAR


def get_package_name(module_name: str) -> str:
    """Get the (pip) package name from a module name.

    Note: falls back to [unknown] if the lookup fails.
    """
    if module_name in packages_distributions():
        return packages_distributions()[module_name][0]
    return "[unknown]"


# Expose as "from ewatercycle.models import Model" for backward compatibility
for _model in _model_entrypoints:
    try:
        globals()[_model.name] = _model.load()
    except Exception as e:
        msg = (
            "An error was raised when trying to load the plugin of model "
            f"'{_model.name}'.\n"
            "You can report the issue on the model's github repository, "
            "or on https://github.com/eWaterCycle/ewatercycle/issues\n"
            "In the meantime, you can try uninstalling the plugin with:\n"
            f"    pip uninstall {get_package_name(_model.value.split('.')[0])}"
        )
        raise ImportError(msg) from e


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
