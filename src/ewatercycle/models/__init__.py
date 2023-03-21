"""Collection of models available in eWaterCycle.

Models are added as plugins through the entrypoints mechanism. See
https://setuptools.pypa.io/en/latest/userguide/entry_point.html#advertising-behavior
"""
# some issues in pre-commit with entry_points
# mypy: ignore-errors

import sys

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


models = entry_points(group="ewatercycle.models")

# Expose as "from ewatercycle.models import Model"
for model in models:
    globals()[model.name] = model.load()


# # Alternative to the above
# def available_models():
#     return {model.name: model.load() for model in models}
