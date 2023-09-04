from pathlib import Path
from textwrap import dedent

import numpy as np
import pytest
from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_info import RecipeInfo
from esmvalcore.experimental.recipe_output import RecipeOutput

from ewatercycle.base.forcing import FORCING_YAML
from ewatercycle.plugins.marrmot.forcing import MarrmotForcing, build_recipe
from ewatercycle.testing.helpers import reyamlify


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    recorder = {}

    dummy_recipe_output = RecipeOutput(
        {
            "diagnostic/script": {
                str(tmp_path / "marrmot.mat"): {},
            }
        },
        info=RecipeInfo({"diagnostics": {"diagnostic": {}}}, "script"),
    )

    def mock_run(self, session=None):
        """Store recipe for inspection and return dummy output."""
        nonlocal recorder
        recorder["session"] = session
        return dummy_recipe_output

    monkeypatch.setattr(Recipe, "run", mock_run)
    return recorder  # noqa: R504


class TestGenerate:
    @pytest.fixture
    def forcing(self, mock_recipe_run, sample_shape):
        return MarrmotForcing.generate(
            dataset="ERA5",
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=sample_shape,
        )

    @pytest.fixture
    def reference_recipe(self):
        return {
            "diagnostics": {
                "diagnostic_daily": {
                    "additional_datasets": [
                        {
                            "dataset": "ERA5",
                            "project": "OBS6",
                            "tier": 3,
                            "type": "reanaly",
                            "version": 1,
                        }
                    ],
                    "description": "marrmot input preprocessor for daily data",
                    "scripts": {
                        "script": {"basin": "Rhine", "script": "hydrology/marrmot.py"}
                    },
                    "variables": {
                        "pr": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily",
                            "start_year": 1989,
                        },
                        "psl": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily",
                            "start_year": 1989,
                        },
                        "rsds": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily",
                            "start_year": 1989,
                        },
                        "rsdt": {
                            "end_year": 1999,
                            "mip": "CFday",
                            "preprocessor": "daily",
                            "start_year": 1989,
                        },
                        "tas": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "daily",
                            "start_year": 1989,
                        },
                    },
                }
            },
            "documentation": {
                "authors": ["kalverla_peter", "camphuijsen_jaro", "alidoost_sarah"],
                "projects": ["ewatercycle"],
                "references": ["acknow_project"],
                "title": "Generate forcing for the Marrmot hydrological model",
                "maintainer": ["unmaintained"],
            },
            "preprocessors": {
                "daily": {
                    "extract_shape": {
                        "crop": True,
                        "method": "contains",
                    }
                }
            },
        }

    def test_result(self, forcing, tmp_path, sample_shape):
        expected = MarrmotForcing(
            directory=str(tmp_path),
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=str(sample_shape),
            forcing_file="marrmot.mat",
        )
        assert forcing == expected

    def test_saved_yaml_content(self, forcing, tmp_path):
        saved_forcing = (tmp_path / FORCING_YAML).read_text()
        # shape should is not included in the yaml file
        expected = dedent(
            """\
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        forcing_file: marrmot.mat
        """
        )

        assert saved_forcing == expected

    def test_saved_yaml(self, forcing, tmp_path):
        saved_forcing = MarrmotForcing.load(tmp_path)
        # shape should is not included in the yaml file
        forcing.shape = None

        assert forcing == saved_forcing


def test_load_foreign(sample_shape, sample_marrmot_forcing_file):
    forcing_file = Path(sample_marrmot_forcing_file)
    actual = MarrmotForcing(
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        directory=str(forcing_file.parent),
        forcing_file=str(forcing_file.name),
    )

    expected = MarrmotForcing(
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        directory=str(forcing_file.parent),
        forcing_file=str(forcing_file.name),
    )
    assert actual == expected


def test_load_foreign_without_forcing_info(sample_shape):
    actual = MarrmotForcing(
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        directory="/data",
    )

    expected = MarrmotForcing(
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        directory="/data",
        forcing_file="marrmot.mat",
    )
    assert actual == expected


def test_generate_with_directory(mock_recipe_run, sample_shape, tmp_path):
    forcing_dir = tmp_path / "myforcing"
    MarrmotForcing.generate(
        dataset="ERA5",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        directory=forcing_dir,
    )

    assert mock_recipe_run["session"].session_dir == forcing_dir


def test_generate_no_output_raises(monkeypatch, sample_shape):
    """Should raise when there is no .mat file in output."""

    dummy_recipe_output = RecipeOutput(
        {"diagnostic/script": {}},
        info=RecipeInfo({"diagnostics": {"diagnostic": {}}}, "script"),
    )

    def failing_recipe_run(self, session):
        return dummy_recipe_output

    monkeypatch.setattr(Recipe, "run", failing_recipe_run)

    with pytest.raises(ValueError):
        MarrmotForcing.generate(
            dataset="ERA5",
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=sample_shape,
        )


def test_load_legacy_forcing(tmp_path):
    (tmp_path / FORCING_YAML).write_text(
        """\
        !MarrmotForcing
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        forcing_file: marrmot.mat
    """
    )

    expected = MarrmotForcing(
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        directory=tmp_path,
    )

    result = MarrmotForcing.load(tmp_path)

    assert result == expected


def test_build_recipe(sample_shape: str):
    recipe = build_recipe(
        dataset="ERA5",
        start_year=1990,
        end_year=2001,
        shape=Path(sample_shape),
    )
    recipe_as_string = recipe.to_yaml()

    expected = dedent(
        f"""\
documentation:
  title: Generate forcing for the MARRMoT hydrological model
  description: Generate forcing for the MARRMoT hydrological model
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
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  tas:
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  pr:
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  psl:
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  rsds:
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
  rsdt:
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: false
diagnostics:
  diagnostic:
    scripts:
      script:
        script: hydrology/marrmot.py
        basin: Rhine
    variables:
      tas:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: tas
      pr:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: pr
      psl:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: psl
      rsds:
        start_year: 1990
        end_year: 2001
        mip: day
        preprocessor: rsds
      rsdt:
        start_year: 1990
        end_year: 2001
        mip: CFday
        preprocessor: rsdt
                      """
    )

    assert recipe_as_string == reyamlify(expected)


def test_to_xarray(sample_marrmot_forcing_file: str):
    directory = Path(sample_marrmot_forcing_file).parent
    forcing_file = Path(sample_marrmot_forcing_file).name
    forcing = MarrmotForcing(
        start_time="1989-01-01T00:00:00Z",
        end_time="1992-12-31T00:00:00Z",
        directory=str(directory),
        forcing_file=forcing_file,
    )

    ds = forcing.to_xarray()

    assert ds.attrs["title"] == "MARRMoT forcing data"
    assert ds.precipitation.shape == (1, 1, 1461)
    assert ds.temperature.shape == (1, 1, 1461)
    assert ds.evspsblpot.shape == (1, 1, 1461)
    assert ds.time.values[0] == np.datetime64("1989-01-01T00:00:00.000000000")
    assert ds.time.values[-1] == np.datetime64("1992-12-31T00:00:00.000000000")
    assert ds.lon.values == [87.49]
    assert ds.lat.values == [35.29]
