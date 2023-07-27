"""Collection of models available in eWaterCycle.

Examples:

    To instantiate a model:

    >>> from ewatercycle.models import Wflow
    >>> model = Wflow()
    # Alternativly import it directly from plugin with
    >>> from ewaterycecle.plugins.wlow.model import Wflow

    To list all available models:

    >>> from ewatercycle.models
    >>> dir(lambaewatercycle.models)
    # List models + some private stuff

    To list all available models in an ipython shell

    >>> from ewatercycle.models import
    # Followed by pressing the TAB key and picking a model from the autocomplete list.

To get your own model to be listed here it needs to be
registered in the :py:data:`ewatercycle.models`
`entry point group <https://packaging.python.org/en/latest/specifications/entry-points/>`_.
"""
from importlib.metadata import entry_points

_model_entrypoints = entry_points(group="ewatercycle.models")  # /NOSONAR

# Expose as "from ewatercycle.models import Model" for backward compatibility
for _model in _model_entrypoints:
    globals()[_model.name] = _model.load()
