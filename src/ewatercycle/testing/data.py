# src/ewatercycle/testing/data.py  (new, no pytest import)
from pathlib import Path

def rhine_shape() -> Path:
    """Return the path to the Rhine shapefile."""
    return Path(__file__).parent / "data" / "Rhine" / "Rhine.shp"
