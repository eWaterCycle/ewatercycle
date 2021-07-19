import numpy as np
import pandas as pd
import pytest
from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_output import DataFile
import xarray as xr

from ewatercycle.forcing import generate
from ewatercycle.forcing._pcrglobwb import PCRGlobWBForcing


def create_netcdf(var_name, filename):
    var = 15 + 8 * np.random.randn(2, 2, 3)
    lon = [[-99.83, -99.32], [-99.79, -99.23]]
    lat = [[42.25, 42.21], [42.63, 42.59]]
    ds = xr.Dataset(
        {
            var_name: (["longitude", "latitude", "time"], var)
        },
        coords={
            "lon": (["longitude", "latitude"], lon),
            "lat": (["longitude", "latitude"], lat),
            "time": pd.date_range("2014-09-06", periods=3),
        }
    )
    ds.to_netcdf(filename)
    return DataFile(filename)


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    data = {}

    class MockTaskOutput:
        data_files = (
            create_netcdf('pr', tmp_path / 'pcrglobwb_pr.nc'),
            create_netcdf('tas', tmp_path / 'pcrglobwb_tas.nc'),
        )

    def mock_run(self):
        """Store recipe for inspection and return dummy output."""
        nonlocal data
        data['data_during_run'] = self.data
        return {'diagnostic_daily/script': MockTaskOutput()}

    monkeypatch.setattr(Recipe, "run", mock_run)
    return data


class TestGenerateWithExtractRegion:
    @pytest.fixture
    def forcing(self, mock_recipe_run, sample_shape):
        return generate(
            target_model='pcrglobwb',
            dataset='ERA5',
            start_time='1989-01-02T00:00:00Z',
            end_time='1999-01-02T00:00:00Z',
            shape=sample_shape,
            model_specific_options=dict(
                start_time_climatology='1979-01-02T00:00:00Z',
                end_time_climatology='1989-01-02T00:00:00Z',
                extract_region={
                    'start_longitude': 10,
                    'end_longitude': 16.75,
                    'start_latitude': 7.25,
                    'end_latitude': 2.5,
                }
            )
        )

    def test_result(self, forcing, tmp_path, sample_shape):
        expected = PCRGlobWBForcing(
            directory=str(tmp_path),
            start_time='1989-01-02T00:00:00Z',
            end_time='1999-01-02T00:00:00Z',
            shape=str(sample_shape),
            precipitationNC='pcrglobwb_pr.nc',
            temperatureNC='pcrglobwb_tas.nc'
        )
        assert forcing == expected

# TODO test if recipe was generated correctlu
# TODO test if yaml was written
