"""Utilities for testing eWaterCycle functionality."""

from pathlib import Path


def rhine_shape() -> Path:
    """Return the path to the Rhine shapefile.

    The shapefile covers the Rhine basin and is bundled with ewatercycle for
    use in tests, examples and documentation notebooks.

    Returns:
        Path to ``Rhine.shp``. The accompanying ``.dbf``, ``.prj`` and ``.shx``
        files sit alongside it, so the parent directory must be kept intact.

    Example:
        >>> from ewatercycle.testing import rhine_shape
        >>> shape = rhine_shape()
        >>> shape.name
        'Rhine.shp'
    """
    return Path(__file__).parent / "data" / "Rhine" / "Rhine.shp"
