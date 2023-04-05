from pathlib import Path
from textwrap import dedent

import pytest
from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_output import OutputFile

from ewatercycle.forcing import generate, load, load_foreign
from ewatercycle.forcing._default import FORCING_YAML
from ewatercycle.forcing._marrmot import MarrmotForcing


def test_plot():
    forcing = MarrmotForcing(
        directory=".",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        forcing_file="marrmot.mat",
    )
    with pytest.raises(NotImplementedError):
        forcing.plot()


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    recorder = {}

    class MockTaskOutput:
        fake_forcing_path = str(tmp_path / "marrmot.mat")
        files = (OutputFile(fake_forcing_path),)

    def mock_run(self, session=None):
        """Store recipe for inspection and return dummy output."""
        nonlocal recorder
        recorder["data_during_run"] = self.data
        recorder["session"] = session
        return {"diagnostic_daily/script": MockTaskOutput()}

    monkeypatch.setattr(Recipe, "run", mock_run)
    return recorder  # noqa: R504


class TestGenerate:
    @pytest.fixture
    def forcing(self, mock_recipe_run, sample_shape):
        return generate(
            target_model="marrmot",
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

    def test_recipe_configured(
        self, forcing, mock_recipe_run, reference_recipe, sample_shape
    ):
        actual = mock_recipe_run["data_during_run"]
        # Remove long description and absolute path so assert is easier
        actual_desc = actual["documentation"]["description"]
        del actual["documentation"]["description"]
        actual_shapefile = actual["preprocessors"]["daily"]["extract_shape"][
            "shapefile"
        ]
        del actual["preprocessors"]["daily"]["extract_shape"]["shapefile"]

        assert actual == reference_recipe
        assert actual_shapefile == sample_shape
        assert "MARRMoT" in actual_desc

    def test_saved_yaml_content(self, forcing, tmp_path):
        saved_forcing = (tmp_path / FORCING_YAML).read_text()
        # shape should is not included in the yaml file
        expected = dedent(
            """\
        model: marrmot
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        forcing_file: marrmot.mat
        """
        )

        assert saved_forcing == expected

    def test_saved_yaml(self, forcing, tmp_path):
        saved_forcing = load(tmp_path)
        # shape should is not included in the yaml file
        forcing.shape = None

        assert forcing == saved_forcing


def test_load_foreign(sample_shape, sample_marrmot_forcing_file):
    forcing_file = Path(sample_marrmot_forcing_file)
    actual = load_foreign(
        target_model="marrmot",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        directory=str(forcing_file.parent),
        forcing_info={"forcing_file": str(forcing_file.name)},
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
    actual = load_foreign(
        target_model="marrmot",
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
    generate(
        target_model="marrmot",
        dataset="ERA5",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=sample_shape,
        directory=forcing_dir,
    )

    assert mock_recipe_run["session"].session_dir == forcing_dir


def test_generate_no_output_raises(monkeypatch, sample_shape):
    """Should raise when there is no .mat file in output."""

    class MockTaskOutput:
        files = ()

    def failing_recipe_run(self, session):
        return {"diagnostic_daily/script": MockTaskOutput}

    monkeypatch.setattr(Recipe, "run", failing_recipe_run)

    with pytest.raises(FileNotFoundError):
        generate(
            target_model="marrmot",
            dataset="ERA5",
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=sample_shape,
        )


def test_generate_wrong_output_raises(monkeypatch, sample_shape, tmp_path):
    """Should raise when there are more than one .mat files in output."""

    class MockTaskOutput:
        fake_forcing_path1 = str(tmp_path / "marrmot.mat")
        fake_forcing_path2 = str(tmp_path / "marrmot.mat")
        files = (
            OutputFile(fake_forcing_path1),
            OutputFile(fake_forcing_path2),
        )

    def failing_recipe_run(self, session):
        return {"diagnostic_daily/script": MockTaskOutput}

    monkeypatch.setattr(Recipe, "run", failing_recipe_run)

    with pytest.raises(FileNotFoundError):
        generate(
            target_model="marrmot",
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

    result = load(tmp_path)

    assert result == expected
