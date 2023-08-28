import datetime
from pathlib import Path
from textwrap import dedent

import pytest
import xarray as xr
from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_info import RecipeInfo
from esmvalcore.experimental.recipe_output import RecipeOutput

from ewatercycle.base.forcing import FORCING_YAML
from ewatercycle.plugins.hype.forcing import HypeForcing, build_recipe
from ewatercycle.testing.helpers import reyamlify


def test_plot():
    f = HypeForcing(
        directory=".",
        start_time="1989-01-02T00:00:00Z",
        end_time="1999-01-02T00:00:00Z",
    )
    with pytest.raises(NotImplementedError):
        f.plot()


def create_txt(dir: Path, var_name: str) -> Path:
    fn = dir / f"{var_name}.txt"
    # Some dummy data shaped as the model expects it
    lines = [
        "DATE 300730 300822",
        "1990-01-01 -0.943 -2.442",
        "1990-01-02 -0.308 -0.868",
    ]
    fn.write_text("\n".join(lines))
    return fn


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Mock the `run` method on esmvalcore Recipe's."""
    recorder = {}

    dummy_recipe_output = RecipeOutput(
        {
            "diagnostic/script": {
                create_txt(tmp_path, "Tobs"): {},
                create_txt(tmp_path, "TMINobs"): {},
                create_txt(tmp_path, "TMAXobs"): {},
                create_txt(tmp_path, "Pobs"): {},
            }
        },
        info=RecipeInfo({"diagnostics": {"diagnostic": {}}}, "script"),
    )

    def mock_run(self, session=None):
        """Record run arguments for inspection and return dummy output."""
        nonlocal recorder
        recorder["session"] = session
        return dummy_recipe_output

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

        expected = xr.Dataset(
            data_vars={
                "Pobs": (
                    ("time", "subbasin"),
                    [[-0.943, -2.442], [-0.308, -0.868]],
                ),
                "TMAXobs": (
                    ("time", "subbasin"),
                    [[-0.943, -2.442], [-0.308, -0.868]],
                ),
                "TMINobs": (
                    ("time", "subbasin"),
                    [[-0.943, -2.442], [-0.308, -0.868]],
                ),
                "Tobs": (
                    ("time", "subbasin"),
                    [[-0.943, -2.442], [-0.308, -0.868]],
                ),
            },
            coords={
                "time": (
                    ("time",),
                    [
                        datetime.datetime(1990, 1, 1, 0, 0),
                        datetime.datetime(1990, 1, 2, 0, 0),
                    ],
                ),
                "subbasin": (("subbasin",), [300730, 300822]),
            },
            attrs={
                "title": "Hype forcing data",
                "history": "Created by ewatercycle.plugins.hype.forcing.HypeForcing.to_xarray()",
            },
        )

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


def test_build_recipe(sample_shape: str):
    recipe = build_recipe(
        dataset="ERA5",
        start_year=1990,
        end_year=2001,
        shape=Path(sample_shape),
    )
    recipe_as_string = recipe.to_yaml()
    print(recipe_as_string)

    # Should look similar to
    # https://github.com/ESMValGroup/ESMValTool/blob/main/esmvaltool/recipes/hydrology/recipe_hype.yml
    expected = dedent(
        f"""\
documentation:
  title: Hype forcing data
  description: ''
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
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: true
    area_statistics:
      operator: mean
  tas:
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: true
    area_statistics:
      operator: mean
    convert_units:
      units: degC
  tasmin:
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: true
    area_statistics:
      operator: mean
    convert_units:
      units: degC
  tasmax:
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: true
    area_statistics:
      operator: mean
    convert_units:
      units: degC
  pr:
    extract_shape:
      shapefile: {sample_shape}
      crop: true
      decomposed: true
    area_statistics:
      operator: mean
    convert_units:
      units: kg m-2 d-1
diagnostics:
  diagnostic:
    scripts:
      script:
        script: hydrology/hype.py
    variables:
      tas:
        start_year: 1990
        end_year: 2001
        preprocessor: tas
      tasmin:
        start_year: 1990
        end_year: 2001
        preprocessor: tasmin
      tasmax:
        start_year: 1990
        end_year: 2001
        preprocessor: tasmax
      pr:
        start_year: 1990
        end_year: 2001
        preprocessor: pr
        """
    )
    assert recipe_as_string == reyamlify(expected)
