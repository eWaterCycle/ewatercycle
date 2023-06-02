"""Collection of models available in eWaterCycle.

Models are added as plugins through the entrypoints mechanism. See
https://setuptools.pypa.io/en/latest/userguide/entry_point.html#advertising-behavior
"""
from importlib.metadata import entry_points

model_entrypoints = entry_points(group="ewatercycle.models")  # /NOSONAR

# Expose as "from ewatercycle.models import Model" for backward compatibility
for model in model_entrypoints:
    globals()[model.name] = model.load()
