from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from ruamel.yaml import YAML


def reyamlify(value: str) -> str:
    """Convert value to yaml object and dump it again.

    recipy.to_yaml() can generate a slightly different yaml string
    than the expected string.
    Call this method on expected string to get consistent results.

    Args:
        value: yaml string

    Returns:
        yaml string
    """
    yaml = YAML(typ="rt")
    stream = StringIO()
    yaml.dump(yaml.load(value), stream=stream)
    return stream.getvalue()


def create_netcdf(var_name: str, filename: Path):
    """Create a netcdf file with random data.

    Args:
        var_name: Variable name
        filename: Path to file

    Returns:
        Path to file
    """
    var = 15 + 8 * np.random.randn(2, 2, 3)
    lon = [[-99.83, -99.32], [-99.79, -99.23]]
    lat = [[42.25, 42.21], [42.63, 42.59]]
    ds = xr.Dataset(
        {var_name: (["longitude", "latitude", "time"], var)},
        coords={
            "lon": (["longitude", "latitude"], lon),
            "lat": (["longitude", "latitude"], lat),
            "time": pd.date_range("2014-09-06", periods=3),
        },
    )
    ds.to_netcdf(filename)
    return filename
