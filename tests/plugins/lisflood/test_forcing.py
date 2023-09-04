from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
import xarray as xr
from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_info import RecipeInfo
from esmvalcore.experimental.recipe_output import DataFile, RecipeOutput

from ewatercycle.base.forcing import FORCING_YAML
from ewatercycle.plugins.lisflood.forcing import LisfloodForcing, build_recipe
from ewatercycle.testing.helpers import reyamlify


def create_netcdf(var_name, filename):
    ds = xr.DataArray(
        data=[[1.0, 2.0], [3.0, 4.0]],
        coords={
            "longitude": [19.35, 19.45],
            "latitude": [-33.05, -33.15],
            "time": "2014-09-06",
        },
        dims=["longitude", "latitude"],
        name=var_name,
    )
    ds.to_netcdf(filename)
    return filename


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    data = {}

    dummy_recipe_output = RecipeOutput(
        {
            "diagnostic/script": {
                # TODO add lisvap input files once implemented, see issue #96
                create_netcdf("pr", tmp_path / "lisflood_pr.nc"): {},
                create_netcdf("tas", tmp_path / "lisflood_tas.nc"): {},
                create_netcdf("tasmax", tmp_path / "lisflood_tasmax.nc"): {},
                create_netcdf("tasmin", tmp_path / "lisflood_tasmin.nc"): {},
                create_netcdf("sfcWind", tmp_path / "lisflood_sfcWind.nc"): {},
                create_netcdf("rsds", tmp_path / "lisflood_rsds.nc"): {},
                create_netcdf("e", tmp_path / "lisflood_e.nc"): {},
            }
        },
        info=RecipeInfo({"diagnostics": {"diagnostic": {}}}, "script"),
    )

    def mock_run(self, session=None):
        """Store recipe for inspection and return dummy output."""
        nonlocal data
        data["session"] = session
        return dummy_recipe_output

    monkeypatch.setattr(Recipe, "run", mock_run)
    return data


@pytest.fixture
def sample_target_grid():
    # Based on extents of sample_shape and offset of mask
    return dict(
        start_longitude=4.05,
        end_longitude=11.95,
        step_longitude=0.1,
        start_latitude=46.25,
        end_latitude=52.25,
        step_latitude=0.1,
    )


class TestGenerateForcingWithoutLisvap:
    @pytest.fixture
    def forcing(self, mock_recipe_run, sample_shape, sample_target_grid):
        return LisfloodForcing.generate(
            dataset="ERA5",
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=sample_shape,
            target_grid=sample_target_grid,
        )

    def test_result(self, forcing, tmp_path, sample_shape):
        expected = LisfloodForcing(
            directory=str(tmp_path),
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=str(sample_shape),
            PrefixPrecipitation="lisflood_pr.nc",
            PrefixTavg="lisflood_tas.nc",
        )
        assert forcing == expected

    def test_saved_yaml_content(self, forcing, tmp_path):
        saved_forcing = (tmp_path / FORCING_YAML).read_text()
        # shape should is not included in the yaml file
        expected = dedent(
            """\
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        PrefixPrecipitation: lisflood_pr.nc
        PrefixTavg: lisflood_tas.nc
        PrefixE0: e0.nc
        PrefixES0: es0.nc
        PrefixET0: et0.nc
        """
        )

        assert saved_forcing == expected

    def test_saved_yaml(self, forcing, tmp_path):
        saved_forcing = LisfloodForcing.load(tmp_path)
        # shape should is not included in the yaml file
        forcing.shape = None

        assert forcing == saved_forcing


def create_mask_netcdf(filename):
    ds = xr.DataArray(
        data=[
            [False, True, True, True, True],
            [False, False, True, True, True],
            [False, False, True, False, True],
            [False, False, False, False, False],
            [False, False, False, False, False],
        ],
        coords={
            "longitude": [19.05, 19.15, 19.25, 19.35, 19.45],
            "latitude": [-33.05, -33.15, -33.25, -33.35, -33.45],
        },
        dims=["longitude", "latitude"],
    )
    ds.to_netcdf(filename)
    return DataFile(filename)


class TestGenerateForcingWithLisvap:
    def test_result(
        self,
        tmp_path,
        sample_shape,
        sample_lisvap_config,
        sample_target_grid,
        mock_recipe_run,
        mocked_config,
    ):
        parameterset_dir = tmp_path / "myparameters"
        mask_map = tmp_path / "mymask.nc"
        create_mask_netcdf(mask_map)

        with patch("subprocess.Popen") as mocked_popen:

            def write_mocked_lisvap_output(*_args, **_kwargs):
                create_netcdf(
                    "e0", tmp_path / "reindexed" / "lisflood_ERA5_Rhine_e0_1989_1999.nc"
                )
                create_netcdf(
                    "es0",
                    tmp_path / "reindexed" / "lisflood_ERA5_Rhine_es0_1989_1999.nc",
                )
                create_netcdf(
                    "et0",
                    tmp_path / "reindexed" / "lisflood_ERA5_Rhine_et0_1989_1999.nc",
                )
                return 0

            mocked_popen.return_value.communicate.return_value = ("output", "error")
            mocked_popen.return_value.wait.side_effect = write_mocked_lisvap_output

            forcing = LisfloodForcing.generate(
                dataset="ERA5",
                start_time="1989-01-02T00:00:00Z",
                end_time="1999-01-02T00:00:00Z",
                shape=sample_shape,
                target_grid=sample_target_grid,
                run_lisvap={
                    "lisvap_config": sample_lisvap_config,
                    "mask_map": str(mask_map),
                    "version": "20.10",
                    "parameterset_dir": str(parameterset_dir),
                },
            )

        expected = LisfloodForcing(
            directory=str(tmp_path / "reindexed"),
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=str(sample_shape),
            PrefixPrecipitation="lisflood_pr.nc",
            PrefixTavg="lisflood_tas.nc",
            PrefixE0="lisflood_ERA5_Rhine_e0_1989_1999.nc",
            PrefixES0="lisflood_ERA5_Rhine_es0_1989_1999.nc",
            PrefixET0="lisflood_ERA5_Rhine_et0_1989_1999.nc",
        )
        assert forcing == expected


def test_generate_with_directory(
    mock_recipe_run, sample_shape, tmp_path, sample_target_grid
):
    forcing_dir = tmp_path / "myforcing"
    LisfloodForcing.generate(
        dataset="ERA5",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        target_grid=sample_target_grid,
        directory=forcing_dir,
    )

    assert mock_recipe_run["session"].session_dir == forcing_dir


def test_load_legacy_forcing(tmp_path):
    (tmp_path / FORCING_YAML).write_text(
        """\
        !LisfloodForcing
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        PrefixPrecipitation: pr.nc
        PrefixTavg: tas.nc
        PrefixE0: e0.nc
        PrefixES0: es0.nc
        PrefixET0: et0.nc
    """
    )

    expected = LisfloodForcing(
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        directory=tmp_path,
    )

    result = LisfloodForcing.load(tmp_path)

    assert result == expected


def test_build_recipe_with_targetgrid(sample_shape: str):
    recipe = build_recipe(
        dataset="ERA5",
        start_year=1990,
        end_year=2001,
        shape=Path(sample_shape),
        target_grid={
            "start_longitude": 3,
            "start_latitude": 46,
            "end_longitude": 12,
            "end_latitude": 55,
            "step_longitude": 0.1,
            "step_latitude": 0.1,
        },
    )
    recipe_as_string = recipe.to_yaml()

    # Should look similar to
    # https://github.com/ESMValGroup/ESMValTool/blob/main/esmvaltool/recipes/hydrology/recipe_lisflood.yml
    expected = dedent(
        f"""\
documentation:
  title: Lisflood forcing recipe
  description: Lisflood forcing recipe
  authors:
  - unmaintained
  projects:
  - ewatercycle
datasets:
- dataset: ERA5
  project: OBS6
  tier: 3
  type: reanaly
  version: 1
preprocessors:
  spatial:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 3
        start_latitude: 46
        end_longitude: 12
        end_latitude: 55
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  pr:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 3
        start_latitude: 46
        end_longitude: 12
        end_latitude: 55
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: kg m-2 d-1
  tas:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 3
        start_latitude: 46
        end_longitude: 12
        end_latitude: 55
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: degC
  tasmin:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 3
        start_latitude: 46
        end_longitude: 12
        end_latitude: 55
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: degC
  tasmax:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 3
        start_latitude: 46
        end_longitude: 12
        end_latitude: 55
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: degC
  tdps:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 3
        start_latitude: 46
        end_longitude: 12
        end_latitude: 55
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: degC
  uas:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 3
        start_latitude: 46
        end_longitude: 12
        end_latitude: 55
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  vas:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 3
        start_latitude: 46
        end_longitude: 12
        end_latitude: 55
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  rsds:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 3
        start_latitude: 46
        end_longitude: 12
        end_latitude: 55
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: J m-2 day-1
diagnostics:
  diagnostic:
    scripts:
      script:
        script: hydrology/lisflood.py
        catchment: Rhine
    variables:
      pr:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: pr
      tas:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: tas
      tasmin:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: tasmin
      tasmax:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: tasmax
      tdps:
        start_year: 1990
        end_year: 2001
        mip: Eday
        preprocessor: tdps
      uas:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: uas
      vas:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: vas
      rsds:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: rsds
        """
    )
    assert recipe_as_string == reyamlify(expected)


def test_build_recipe_without_targetgrid(sample_shape: str):
    recipe = build_recipe(
        dataset="ERA5",
        start_year=1990,
        end_year=2001,
        shape=Path(sample_shape),
    )
    recipe_as_string = recipe.to_yaml()

    # Should look similar to
    # https://github.com/ESMValGroup/ESMValTool/blob/main/esmvaltool/recipes/hydrology/recipe_lisflood.yml
    expected = dedent(
        f"""\
documentation:
  title: Lisflood forcing recipe
  description: Lisflood forcing recipe
  authors:
  - unmaintained
  projects:
  - ewatercycle
datasets:
- dataset: ERA5
  project: OBS6
  tier: 3
  type: reanaly
  version: 1
preprocessors:
  spatial:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 4.05
        start_latitude: 46.25
        end_longitude: 11.95
        end_latitude: 52.25
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  pr:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 4.05
        start_latitude: 46.25
        end_longitude: 11.95
        end_latitude: 52.25
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: kg m-2 d-1
  tas:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 4.05
        start_latitude: 46.25
        end_longitude: 11.95
        end_latitude: 52.25
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: degC
  tasmin:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 4.05
        start_latitude: 46.25
        end_longitude: 11.95
        end_latitude: 52.25
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: degC
  tasmax:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 4.05
        start_latitude: 46.25
        end_longitude: 11.95
        end_latitude: 52.25
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: degC
  tdps:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 4.05
        start_latitude: 46.25
        end_longitude: 11.95
        end_latitude: 52.25
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: degC
  uas:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 4.05
        start_latitude: 46.25
        end_longitude: 11.95
        end_latitude: 52.25
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  vas:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 4.05
        start_latitude: 46.25
        end_longitude: 11.95
        end_latitude: 52.25
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  rsds:
    regrid:
      scheme: linear
      target_grid:
        start_longitude: 4.05
        start_latitude: 46.25
        end_longitude: 11.95
        end_latitude: 52.25
        step_longitude: 0.1
        step_latitude: 0.1
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
    convert_units:
      units: J m-2 day-1
diagnostics:
  diagnostic:
    scripts:
      script:
        script: hydrology/lisflood.py
        catchment: Rhine
    variables:
      pr:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: pr
      tas:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: tas
      tasmin:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: tasmin
      tasmax:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: tasmax
      tdps:
        start_year: 1990
        end_year: 2001
        mip: Eday
        preprocessor: tdps
      uas:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: uas
      vas:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: vas
      rsds:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: rsds
        """
    )
    assert recipe_as_string == reyamlify(expected)
