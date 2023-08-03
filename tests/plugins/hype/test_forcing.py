from pathlib import Path
from textwrap import dedent

import pytest
import xarray as xr
from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_output import OutputFile

from ewatercycle.base.forcing import FORCING_YAML
from ewatercycle.forcing import sources

HypeForcing = sources["HypeForcing"]


def test_plot():
    f = HypeForcing(
        directory=".",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
    )
    with pytest.raises(NotImplementedError):
        f.plot()


def create_txt(dir: Path, var_name: str) -> OutputFile:
    fn = dir / f"{var_name}.txt"
    # Some dummy data shaped as the model expects it
    lines = [
        "DATE 300730 300822",
        "1990-01-01 -0.943 -2.442",
        "1990-01-02 -0.308 -0.868",
    ]
    with open(fn, encoding="ascii", mode="w") as f:
        f.writelines(lines)
    return OutputFile(fn)


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    recorder = {}

    class MockTaskOutput:
        fake_forcing_path = str(tmp_path / "marrmot.mat")
        files = (
            create_txt(tmp_path, "Tobs"),
            create_txt(tmp_path, "TMINobs"),
            create_txt(tmp_path, "TMAXobs"),
            create_txt(tmp_path, "Pobs"),
        )

    def mock_run(self, session=None):
        """Store recipe for inspection and return dummy output."""
        nonlocal recorder
        recorder["data_during_run"] = self.data
        recorder["session"] = session
        return {"diagnostic_daily/script": MockTaskOutput()}

    monkeypatch.setattr(Recipe, "run", mock_run)
    return recorder


class TestGenerate:
    @pytest.fixture
    def forcing(self, mock_recipe_run, sample_shape):
        # The recipe needs a compose shapefile, but the sample shape is not composed.
        # That is OK because we mock the recipe run
        return HypeForcing.generate(
            dataset="ERA5",
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=sample_shape,
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
                "hype": {
                    "description": "HYPE input preprocessor for daily " "data",
                    "scripts": {"script": {"script": "hydrology/hype.py"}},
                    "variables": {
                        "pr": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "water",
                            "start_year": 1989,
                        },
                        "tas": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "temperature",
                            "start_year": 1989,
                        },
                        "tasmax": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "temperature",
                            "start_year": 1989,
                        },
                        "tasmin": {
                            "end_year": 1999,
                            "mip": "day",
                            "preprocessor": "temperature",
                            "start_year": 1989,
                        },
                    },
                }
            },
            "documentation": {
                "authors": ["pelupessy_inti", "kalverla_peter"],
                "maintainer": ["unmaintained"],
                "projects": ["ewatercycle"],
                "references": ["acknow_project"],
                "title": "Generate forcing for the Hype hydrological model",
            },
            "preprocessors": {
                "preprocessor": {
                    "area_statistics": {"operator": "mean"},
                    "extract_shape": {
                        "decomposed": True,
                        "method": "contains",
                    },
                },
                "temperature": {
                    "area_statistics": {"operator": "mean"},
                    "convert_units": {"units": "degC"},
                    "extract_shape": {
                        "decomposed": True,
                        "method": "contains",
                    },
                },
                "water": {
                    "area_statistics": {"operator": "mean"},
                    "convert_units": {"units": "kg m-2 d-1"},
                    "extract_shape": {
                        "decomposed": True,
                        "method": "contains",
                    },
                },
            },
        }

    def test_recipe_configured(
        self, forcing, mock_recipe_run, expected_recipe, sample_shape
    ):
        actual = mock_recipe_run["data_during_run"]
        # Remove absolute path so assert is easier
        ps = actual["preprocessors"]
        actual_shapefile = ps["preprocessor"]["extract_shape"]["shapefile"]
        del ps["preprocessor"]["extract_shape"]["shapefile"]
        # Remove long description and absolute path so assert is easier
        actual_desc = actual["documentation"]["description"]
        del actual["documentation"]["description"]

        assert actual == expected_recipe
        assert str(actual_shapefile) == sample_shape
        assert "Hype" in actual_desc

    def test_result(self, forcing, tmp_path, sample_shape):
        expected = HypeForcing(
            directory=str(tmp_path),
            start_time="1989-01-02T00:00:00Z",
            end_time="1999-01-02T00:00:00Z",
            shape=str(sample_shape),
            Pobs="Pobs.txt",
            TMAXobs="TMAXobs.txt",
            TMINobs="TMINobs.txt",
            Tobs="Tobs.txt",
        )
        assert forcing == expected

    def test_saved_yaml_content(self, forcing, tmp_path):
        saved_forcing = (tmp_path / FORCING_YAML).read_text()
        # shape should is not included in the yaml file
        expected = dedent(
            """\
        model: hype
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        Pobs: Pobs.txt
        TMAXobs: TMAXobs.txt
        TMINobs: TMINobs.txt
        Tobs: Tobs.txt
        """
        )

        assert saved_forcing == expected

    def test_saved_yaml_by_loading(self, forcing, tmp_path):
        saved_forcing = HypeForcing.load(tmp_path)
        # shape should is not included in the yaml file
        forcing.shape = None

        assert forcing == saved_forcing

    def test_to_xarray(self, forcing):
        ds = forcing.to_xarray()

        expected = xr.Dataset()

        xr.testing.assert_equal(ds, expected)


def test_with_directory(mock_recipe_run, sample_shape, tmp_path):
    forcing_dir = tmp_path / "myforcing"
    HypeForcing.generate(
        dataset="ERA5",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        shape=str(sample_shape),
        directory=forcing_dir,
    )

    assert mock_recipe_run["session"].session_dir == forcing_dir


def test_load_legacy_forcing(tmp_path):
    (tmp_path / FORCING_YAML).write_text(
        """\
        !HypeForcing
        start_time: '1989-01-02T00:00:00Z'
        end_time: '1999-01-02T00:00:00Z'
        Pobs: Pobs.txt
        TMAXobs: TMAXobs.txt
        TMINobs: TMINobs.txt
        Tobs: Tobs.txt
    """
    )

    expected = HypeForcing(
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
        directory=tmp_path,
    )

    result = HypeForcing.load(tmp_path)

    assert result == expected
