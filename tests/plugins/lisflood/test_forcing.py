from textwrap import dedent
from unittest.mock import patch

import pytest
import xarray as xr
from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_output import DataFile

from ewatercycle.forcing import generate, load
from ewatercycle.base.forcing import FORCING_YAML
from ewatercycle.plugins.lisflood.forcing import LisfloodForcing


def test_plot():
    f = LisfloodForcing(
        directory=".",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
    )
    with pytest.raises(NotImplementedError):
        f.plot()


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
    return DataFile(filename)


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    data = {}

    # TODO add lisvap input files once implemented, see issue #96
    class MockTaskOutput:
        data_files = (
            create_netcdf("pr", tmp_path / "lisflood_pr.nc"),
            create_netcdf("tas", tmp_path / "lisflood_tas.nc"),
            create_netcdf("tasmax", tmp_path / "lisflood_tasmax.nc"),
            create_netcdf("tasmin", tmp_path / "lisflood_tasmin.nc"),
            create_netcdf("sfcWind", tmp_path / "lisflood_sfcWind.nc"),
            create_netcdf("rsds", tmp_path / "lisflood_rsds.nc"),
            create_netcdf("e", tmp_path / "lisflood_e.nc"),
        )

    def mock_run(self, session=None):
        """Store recipe for inspection and return dummy output."""
        nonlocal data
        data["data_during_run"] = self.data
        data["session"] = session
        return {"diagnostic_daily/script": MockTaskOutput()}

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
        return generate(
            target_model="lisflood",
            dataset="ERA5",
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=sample_shape,
            model_specific_options=dict(target_grid=sample_target_grid),
        )

    @pytest.fixture
    def expected_recipe(self):
        return {
            "datasets": [
                {
                    "dataset": "ERA5",
                    "project": "OBS6",
                    "tier": 3,
                    "type": "reanaly",
                    "version": 1,
                }
            ],
            "diagnostics": {
                "diagnostic_daily": {
                    "description": "LISFLOOD input "
                    "preprocessor for "
                    "ERA-Interim and ERA5 "
                    "data",
                    "scripts": {
                        "script": {
                            "catchment": "Rhine",
                            "script": "hydrology/lisflood.py",
                        }
                    },
                    "variables": {
                        "pr": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily_water",
                            "start_year": 1989,
                        },
                        "rsds": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily_radiation",
                            "start_year": 1989,
                        },
                        "tas": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily_temperature",
                            "start_year": 1989,
                        },
                        "tasmax": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily_temperature",
                            "start_year": 1989,
                        },
                        "tasmin": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily_temperature",
                            "start_year": 1989,
                        },
                        "tdps": {
                            "end_year": 1999,
                            "mip": "Eday",
                            "preprocessor": "daily_temperature",
                            "start_year": 1989,
                        },
                        "uas": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily_windspeed",
                            "start_year": 1989,
                        },
                        "vas": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily_windspeed",
                            "start_year": 1989,
                        },
                    },
                }
            },
            "documentation": {
                "authors": ["verhoeven_stefan", "kalverla_peter", "andela_bouwe"],
                "maintainer": ["unmaintained"],
                "projects": ["ewatercycle"],
                "references": ["acknow_project"],
                "description": "Recipe pre-process files for use in the "
                "LISFLOOD hydrological model.\n",
                "title": "Generate forcing for the Lisflood hydrological " "model",
            },
            "preprocessors": {
                "daily_radiation": {
                    "convert_units": {"units": "J m-2 " "day-1"},
                    "extract_shape": {"crop": True, "method": "contains"},
                    "regrid": {
                        "scheme": "linear",
                        "target_grid": {
                            "end_latitude": 52.25,
                            "end_longitude": 11.95,
                            "start_latitude": 46.25,
                            "start_longitude": 4.05,
                            "step_latitude": 0.1,
                            "step_longitude": 0.1,
                        },
                    },
                },
                "daily_temperature": {
                    "convert_units": {"units": "degC"},
                    "extract_shape": {"crop": True, "method": "contains"},
                    "regrid": {
                        "scheme": "linear",
                        "target_grid": {
                            "end_latitude": 52.25,
                            "end_longitude": 11.95,
                            "start_latitude": 46.25,
                            "start_longitude": 4.05,
                            "step_latitude": 0.1,
                            "step_longitude": 0.1,
                        },
                    },
                },
                "daily_water": {
                    "convert_units": {"units": "kg m-2 d-1"},
                    "extract_shape": {"crop": True, "method": "contains"},
                    "regrid": {
                        "scheme": "linear",
                        "target_grid": {
                            "end_latitude": 52.25,
                            "end_longitude": 11.95,
                            "start_latitude": 46.25,
                            "start_longitude": 4.05,
                            "step_latitude": 0.1,
                            "step_longitude": 0.1,
                        },
                    },
                },
                "daily_windspeed": {
                    "extract_shape": {"crop": True, "method": "contains"},
                    "regrid": {
                        "scheme": "linear",
                        "target_grid": {
                            "end_latitude": 52.25,
                            "end_longitude": 11.95,
                            "start_latitude": 46.25,
                            "start_longitude": 4.05,
                            "step_latitude": 0.1,
                            "step_longitude": 0.1,
                        },
                    },
                },
                "general": {
                    "extract_shape": {"crop": True, "method": "contains"},
                    "regrid": {
                        "scheme": "linear",
                        "target_grid": {
                            "end_latitude": 52.25,
                            "end_longitude": 11.95,
                            "start_latitude": 46.25,
                            "start_longitude": 4.05,
                            "step_latitude": 0.1,
                            "step_longitude": 0.1,
                        },
                    },
                },
            },
        }

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

    def test_recipe_configured(
        self, forcing, mock_recipe_run, expected_recipe, sample_shape
    ):
        actual = mock_recipe_run["data_during_run"]
        # Remove absolute path so assert is easier
        actual_shapefile = actual["preprocessors"]["general"]["extract_shape"][
            "shapefile"
        ]
        # Will also del other occurrences of shapefile due to extract shape object
        # being shared between preprocessors
        del actual["preprocessors"]["general"]["extract_shape"]["shapefile"]

        assert actual == expected_recipe
        assert actual_shapefile == sample_shape

    def test_saved_yaml_content(self, forcing, tmp_path):
        saved_forcing = (tmp_path / FORCING_YAML).read_text()
        # shape should is not included in the yaml file
        expected = dedent(
            """\
        model: lisflood
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
        saved_forcing = load(tmp_path)
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

            forcing = generate(
                target_model="lisflood",
                dataset="ERA5",
                start_time="1989-01-02T00:00:00Z",
                end_time="1999-01-02T00:00:00Z",
                shape=sample_shape,
                model_specific_options={
                    "target_grid": sample_target_grid,
                    "run_lisvap": {
                        "lisvap_config": sample_lisvap_config,
                        "mask_map": str(mask_map),
                        "version": "20.10",
                        "parameterset_dir": str(parameterset_dir),
                    },
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


class TestGenerateForcingWithoutTargetGrid:
    def test_recipe_configured(self, mock_recipe_run, sample_shape):
        generate(
            target_model="lisflood",
            dataset="ERA5",
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=sample_shape,
        )

        actual = mock_recipe_run["data_during_run"]

        # Extent of sample_shape fitted to 0.1x0.1 grid with 0.05 offset
        expected_target_grid = {
            "end_latitude": 52.25,
            "end_longitude": 11.95,
            "start_latitude": 46.25,
            "start_longitude": 4.05,
            "step_latitude": 0.1,
            "step_longitude": 0.1,
        }
        assert (
            actual["preprocessors"]["general"]["regrid"]["target_grid"]
            == expected_target_grid
        )
        assert (
            actual["preprocessors"]["daily_water"]["regrid"]["target_grid"]
            == expected_target_grid
        )
        assert (
            actual["preprocessors"]["daily_temperature"]["regrid"]["target_grid"]
            == expected_target_grid
        )
        assert (
            actual["preprocessors"]["daily_radiation"]["regrid"]["target_grid"]
            == expected_target_grid
        )
        assert (
            actual["preprocessors"]["daily_windspeed"]["regrid"]["target_grid"]
            == expected_target_grid
        )


def test_generate_with_directory(
    mock_recipe_run, sample_shape, tmp_path, sample_target_grid
):
    forcing_dir = tmp_path / "myforcing"
    generate(
        target_model="lisflood",
        dataset="ERA5",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        model_specific_options=dict(target_grid=sample_target_grid),
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

    result = load(tmp_path)

    assert result == expected
