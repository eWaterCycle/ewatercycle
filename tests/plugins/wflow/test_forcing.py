"""Test forcing data for WFLOW."""

from pathlib import Path
from textwrap import dedent

import pytest
from esmvalcore.experimental.recipe import Recipe
from esmvalcore.experimental.recipe_output import DataFile

from ewatercycle.base.forcing import FORCING_YAML
from ewatercycle.forcing import sources

WflowForcing = sources["WflowForcing"]


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    data = {}

    class MockTaskOutput:
        fake_forcing_path = str(tmp_path / "wflow_forcing.nc")
        data_files = (DataFile(fake_forcing_path),)

    def mock_run(self, session=None):
        """Store recipe for inspection and return dummy output."""
        nonlocal data
        data["data_during_run"] = self.data
        data["session"] = session
        return {"wflow_daily/script": MockTaskOutput()}

    monkeypatch.setattr(Recipe, "run", mock_run)
    return data


class TestGenerateWithExtractRegion:
    @pytest.fixture
    def reference_recipe(self):
        return {
            "diagnostics": {
                "wflow_daily": {
                    "additional_datasets": [
                        {
                            "dataset": "ERA5",
                            "project": "OBS6",
                            "tier": 3,
                            "type": "reanaly",
                            "version": 1,
                        }
                    ],
                    "description": "WFlow input preprocessor for " "daily data",
                    "scripts": {
                        "script": {
                            "basin": "Rhine",
                            "dem_file": "wflow_parameterset/meuse/staticmaps/wflow_dem.map",  # noqa: E501
                            "regrid": "area_weighted",
                            "script": "hydrology/wflow.py",
                        }
                    },
                    "variables": {
                        "orog": {"mip": "fx", "preprocessor": "rough_cutout"},
                        "pr": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "rough_cutout",
                            "start_year": 1989,
                        },
                        "psl": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "rough_cutout",
                            "start_year": 1989,
                        },
                        "rsds": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "rough_cutout",
                            "start_year": 1989,
                        },
                        "rsdt": {
                            "end_year": 1999,
                            "mip": "CFday",
                            "preprocessor": "rough_cutout",
                            "start_year": 1989,
                        },
                        "tas": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "rough_cutout",
                            "start_year": 1989,
                        },
                    },
                }
            },
            "documentation": {
                "authors": [
                    "kalverla_peter",
                    "camphuijsen_jaro",
                    "alidoost_sarah",
                    "aerts_jerom",
                    "andela_bouwe",
                ],
                "maintainer": ["unmaintained"],
                "description": "Pre-processes climate data for the WFlow hydrological model.\n",  # noqa: E501
                "projects": ["ewatercycle"],
                "references": ["acknow_project"],
                "title": "Generate forcing for the WFlow hydrological model",
            },
            "preprocessors": {
                "rough_cutout": {
                    "extract_region": {
                        "end_latitude": 2.5,
                        "end_longitude": 16.75,
                        "start_latitude": 7.25,
                        "start_longitude": 10,
                    }
                }
            },
        }

    @pytest.fixture
    def forcing(self, mock_recipe_run, sample_shape):
        return WflowForcing.generate(
            dataset="ERA5",
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=sample_shape,
            dem_file="wflow_parameterset/meuse/staticmaps/wflow_dem.map",
            extract_region={
                "start_longitude": 10,
                "end_longitude": 16.75,
                "start_latitude": 7.25,
                "end_latitude": 2.5,
            },
        )

    def test_result(self, forcing, tmp_path, sample_shape):
        expected = WflowForcing(
            directory=str(tmp_path),
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=str(sample_shape),
            netcdfinput="wflow_forcing.nc",
        )
        assert forcing == expected

    def test_recipe_configured(self, forcing, mock_recipe_run, reference_recipe):
        assert mock_recipe_run["data_during_run"] == reference_recipe

    def test_saved_yaml_content(self, forcing, tmp_path):
        saved_forcing = (tmp_path / FORCING_YAML).read_text()
        # shape should is not included in the yaml file
        expected = dedent(
            """\
        model: wflow
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        netcdfinput: wflow_forcing.nc
        Precipitation: /pr
        EvapoTranspiration: /pet
        Temperature: /tas
        """
        )

        assert saved_forcing == expected

    def test_saved_yaml(self, forcing, tmp_path):
        saved_forcing = WflowForcing.load(tmp_path)
        # shape should is not included in the yaml file
        forcing.shape = None

        assert forcing == saved_forcing

    def test_str(self, forcing, tmp_path, sample_shape):
        result = str(forcing)
        expected = "".join(
            [
                "model='wflow' start_time='1989-01-02T00:00:00Z' end_time='1999-01-02T00:00:00Z' ",
                f"directory={repr(tmp_path)} shape={repr(Path(sample_shape))} ",
                "netcdfinput='wflow_forcing.nc' Precipitation='/pr' ",
                "EvapoTranspiration='/pet' Temperature='/tas' Inflow=None",
            ]
        )
        assert result == expected


def test_with_directory(mock_recipe_run, sample_shape, tmp_path):
    forcing_dir = tmp_path / "myforcing"
    WflowForcing.generate(
        dataset="ERA5",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        directory=forcing_dir,
        dem_file="wflow_parameterset/meuse/staticmaps/wflow_dem.map",
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
        !WflowForcing
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        netcdfinput: inmaps.nc
        Precipitation: /pr
        EvapoTranspiration: /pet
        Temperature: /tas
    """
    )

    expected = WflowForcing(
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        directory=tmp_path,
    )

    result = WflowForcing.load(tmp_path)

    assert result == expected
