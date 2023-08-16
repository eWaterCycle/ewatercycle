from pathlib import Path
from textwrap import dedent

from ewatercycle.esmvaltool.builder import (
    DEFAULT_DIAGNOSTIC_SCRIPT,
    RecipeBuilder,
    build_generic_distributed_forcing_recipe,
)
from ewatercycle.esmvaltool.models import Dataset


def test_build_esmvaltool_recipe():
    era5 = Dataset(dataset="ERA5", project="OBS6", tier=3, type="reanaly", version=1)
    recipe = (
        RecipeBuilder()
        .description(
            "Recipe to generate forcing for a generic distributed hydrogeological model"
        )
        .title("Generic distributed hydrogeological model forcing")
        .dataset(era5)
        .start(2020)
        .end(2021)
        .shape(Path("myshape.shp"))
        .region(
            start_longitude=40,
            end_longitude=65,
            start_latitude=25,
            end_latitude=40,
        )
        .add_variable("tas", mip="day", units="degC")
        .build()
    )
    recipe_as_string = recipe.to_yaml()
    print(recipe_as_string)

    expected = dedent(
        f"""\
documentation:
  title: Generic distributed hydrogeological model forcing
  description: Recipe to generate forcing for a generic distributed hydrogeological
    model
  authors:
  - unmaintained
  projects:
  - ewatercycle
datasets:
- dataset: ERA5
  project: OBS6
  tier: 3
  type: reanaly
preprocessors:
  spatial:
    extract_region:
      start_longitude: 40
      end_longitude: 65
      start_latitude: 25
      end_latitude: 40
  tas:
    extract_region:
      start_longitude: 40
      end_longitude: 65
      start_latitude: 25
      end_latitude: 40
    convert_units:
      units: degC
diagnostics:
  diagnostic:
    scripts:
      script:
        script: {DEFAULT_DIAGNOSTIC_SCRIPT}
    variables:
      tas:
        start_year: 2020
        end_year: 2021
        mip: day
        preprocessor: tas
        """
    )
    assert recipe_as_string == expected


def test_build_generic_distributed_forcing_recipe():
    recipe = build_generic_distributed_forcing_recipe(
        start_year=1990,
        end_year=2001,
        shape=Path("myshape.shp"),
    )
    recipe_as_string = recipe.to_yaml()
    print(recipe_as_string)

    expected = dedent(
        f"""\
documentation:
  title: Generic distributed forcing recipe
  description: Generic distributed forcing recipe
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
      shapefile: myshape.shp
      crop: true
      decomposed: false
  pr:
    extract_shape:
      shapefile: myshape.shp
      crop: true
      decomposed: false
  tas:
    extract_shape:
      shapefile: myshape.shp
      crop: true
      decomposed: false
  tasmin:
    extract_shape:
      shapefile: myshape.shp
      crop: true
      decomposed: false
  tasmax:
    extract_shape:
      shapefile: myshape.shp
      crop: true
      decomposed: false
diagnostics:
  diagnostic:
    scripts:
      script:
        script: {DEFAULT_DIAGNOSTIC_SCRIPT}
    variables:
      pr:
        start_year: 1990
        end_year: 2001
        preprocessor: pr
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
        """
    )
    assert recipe_as_string == expected
