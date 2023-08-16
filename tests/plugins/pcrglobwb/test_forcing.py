from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd
import pytest
import xarray as xr
from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_output import DataFile

from ewatercycle.base.forcing import FORCING_YAML
from ewatercycle.forcing import sources
from ewatercycle.plugins.pcrglobwb.forcing import build_pcrglobwb_recipe
from ewatercycle.util import get_extents

PCRGlobWBForcing = sources["PCRGlobWBForcing"]


def create_netcdf(var_name, filename):
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
    return DataFile(filename)


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    data = {}

    class MockTaskOutput:
        data_files = (
            create_netcdf("pr", tmp_path / "pcrglobwb_pr.nc"),
            create_netcdf("tas", tmp_path / "pcrglobwb_tas.nc"),
        )

    def mock_run(self, session=None):
        """Store recipe for inspection and return dummy output."""
        nonlocal data
        data["data_during_run"] = self.data
        data["session"] = session
        return {"diagnostic_daily/script": MockTaskOutput()}

    monkeypatch.setattr(Recipe, "run", mock_run)
    return data


class TestGenerateWithExtractRegion:
    @pytest.fixture
    def forcing(self, mock_recipe_run, sample_shape):
        return PCRGlobWBForcing.generate(
            dataset="ERA5",
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=sample_shape,
            start_time_climatology="1979-01-02T00:00:00Z",
            end_time_climatology="1989-01-02T00:00:00Z",
            extract_region={
                "start_longitude": 10,
                "end_longitude": 16.75,
                "start_latitude": 7.25,
                "end_latitude": 2.5,
            },
        )

    def test_result(self, forcing, tmp_path, sample_shape):
        expected = PCRGlobWBForcing(
            directory=str(tmp_path),
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=str(sample_shape),
            precipitationNC="pcrglobwb_pr.nc",
            temperatureNC="pcrglobwb_tas.nc",
        )
        assert forcing == expected

    def test_str(self, forcing, tmp_path, sample_shape):
        result = str(forcing)
        expected = "".join(
            [
                "model='pcrglobwb' start_time='1989-01-02T00:00:00Z' end_time='1999-01-02T00:00:00Z' ",
                f"directory={repr(tmp_path)} shape={repr(Path(sample_shape))} ",
                "precipitationNC='pcrglobwb_pr.nc' temperatureNC='pcrglobwb_tas.nc'",
            ]
        )
        assert result == expected

    # TODO test if recipe was generated correctly

    def test_saved_yaml_content(self, forcing, tmp_path):
        saved_forcing = (tmp_path / FORCING_YAML).read_text()
        # shape should is not included in the yaml file
        expected = dedent(
            """\
        model: pcrglobwb
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        precipitationNC: pcrglobwb_pr.nc
        temperatureNC: pcrglobwb_tas.nc
        """
        )

        assert saved_forcing == expected

    def test_saved_yaml_by_loading(self, forcing, tmp_path):
        saved_forcing = PCRGlobWBForcing.load(tmp_path)
        # shape should is not included in the yaml file
        forcing.shape = None

        assert forcing == saved_forcing


def test_with_directory(mock_recipe_run, sample_shape, tmp_path):
    forcing_dir = tmp_path / "myforcing"
    PCRGlobWBForcing.generate(
        dataset="ERA5",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=str(sample_shape),
        directory=forcing_dir,
        start_time_climatology="1979-01-02T00:00:00Z",
        end_time_climatology="1989-01-02T00:00:00Z",
        extract_region={
            "start_longitude": 10,
            "end_longitude": 16.75,
            "start_latitude": 7.25,
            "end_latitude": 2.5,
        },
    )

    assert mock_recipe_run["session"].session_dir == forcing_dir


def test_load_legacy_forcing(tmp_path):
    (tmp_path / FORCING_YAML).write_text(
        """\
        !PCRGlobWBForcing
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        precipitationNC: pcrglobwb_pr.nc
        temperatureNC: pcrglobwb_tas.nc
    """
    )

    expected = PCRGlobWBForcing(
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        directory=tmp_path,
        precipitationNC="pcrglobwb_pr.nc",
        temperatureNC="pcrglobwb_tas.nc",
    )

    result = PCRGlobWBForcing.load(tmp_path)

    assert result == expected


def test_build_pcrglobwb_recipe(sample_shape: str):
    recipe = build_pcrglobwb_recipe(
        start_year=1990,
        end_year=2001,
        shape=Path(sample_shape),
        start_year_climatology=1980,
        end_year_climatology=1990,
        dataset="ERA5",
    )
    recipe_as_string = recipe.to_yaml()
    print(recipe_as_string)

    # Should look similar to
    # https://github.com/ESMValGroup/ESMValTool/blob/main/esmvaltool/recipes/hydrology/recipe_pcrglobwb.yml
    expected = dedent(
        """\
documentation:
  title: PCRGlobWB forcing recipe
  description: PCRGlobWB forcing recipe
  authors:
  - unmaintained
  projects:
  - ewatercycle
datasets:
- dataset: ERA5
  project: OBS6
  mip: day
  tier: 3
  type: reanaly
preprocessors:
  spatial:
    extract_region:
      start_longitude: 4.1
      end_longitude: 11.9
      start_latitude: 46.3
      end_latitude: 52.2
  pr:
    extract_region:
      start_longitude: 4.1
      end_longitude: 11.9
      start_latitude: 46.3
      end_latitude: 52.2
    convert_units:
      units: kg m-2 d-1
  tas:
    extract_region:
      start_longitude: 4.1
      end_longitude: 11.9
      start_latitude: 46.3
      end_latitude: 52.2
  pr_climatology:
    extract_region:
      start_longitude: 4.1
      end_longitude: 11.9
      start_latitude: 46.3
      end_latitude: 52.2
    convert_units:
      units: kg m-2 d-1
    climate_statistics:
      operator: mean
      period: day
  tas_climatology:
    extract_region:
      start_longitude: 4.1
      end_longitude: 11.9
      start_latitude: 46.3
      end_latitude: 52.2
    climate_statistics:
      operator: mean
      period: day
diagnostics:
  diagnostic:
    scripts:
      script:
        script: hydrology/pcrglobwb.py
        basin: Rhine
    variables:
      pr:
        start_year: 1990
        end_year: 2001
        preprocessor: pr
      tas:
        start_year: 1990
        end_year: 2001
        preprocessor: tas
      pr_climatology:
        start_year: 1980
        end_year: 1990
        preprocessor: pr_climatology
        short_name: pr
      tas_climatology:
        start_year: 1980
        end_year: 1990
        preprocessor: tas_climatology
        short_name: tas
        """
    )
    assert recipe_as_string == expected


def test_build_pcrglobwb_recipe_with_region(sample_shape: str):
    extents = get_extents(sample_shape, 2)
    recipe = build_pcrglobwb_recipe(
        start_year=1990,
        end_year=2001,
        shape=Path(sample_shape),
        start_year_climatology=1980,
        end_year_climatology=1990,
        dataset="ERA5",
        extract_region={
            "start_longitude": extents["start_longitude"],
            "end_longitude": extents["end_longitude"],
            "start_latitude": extents["start_latitude"],
            "end_latitude": extents["end_latitude"],
        },
    )
    recipe_as_string = recipe.to_yaml()
    print(recipe_as_string)

    expected = dedent(
        """\
documentation:
  title: PCRGlobWB forcing recipe
  description: PCRGlobWB forcing recipe
  authors:
  - unmaintained
  projects:
  - ewatercycle
datasets:
- dataset: ERA5
  project: OBS6
  mip: day
  tier: 3
  type: reanaly
preprocessors:
  spatial:
    extract_region:
      start_longitude: 2.1
      end_longitude: 13.9
      start_latitude: 44.3
      end_latitude: 54.2
  pr:
    extract_region:
      start_longitude: 2.1
      end_longitude: 13.9
      start_latitude: 44.3
      end_latitude: 54.2
    convert_units:
      units: kg m-2 d-1
  tas:
    extract_region:
      start_longitude: 2.1
      end_longitude: 13.9
      start_latitude: 44.3
      end_latitude: 54.2
  pr_climatology:
    extract_region:
      start_longitude: 2.1
      end_longitude: 13.9
      start_latitude: 44.3
      end_latitude: 54.2
    convert_units:
      units: kg m-2 d-1
    climate_statistics:
      operator: mean
      period: day
  tas_climatology:
    extract_region:
      start_longitude: 2.1
      end_longitude: 13.9
      start_latitude: 44.3
      end_latitude: 54.2
    climate_statistics:
      operator: mean
      period: day
diagnostics:
  diagnostic:
    scripts:
      script:
        script: hydrology/pcrglobwb.py
        basin: Rhine
    variables:
      pr:
        start_year: 1990
        end_year: 2001
        preprocessor: pr
      tas:
        start_year: 1990
        end_year: 2001
        preprocessor: tas
      pr_climatology:
        start_year: 1980
        end_year: 1990
        preprocessor: pr_climatology
        short_name: pr
      tas_climatology:
        start_year: 1980
        end_year: 1990
        preprocessor: tas_climatology
        short_name: tas
        """
    )
    assert recipe_as_string == expected
