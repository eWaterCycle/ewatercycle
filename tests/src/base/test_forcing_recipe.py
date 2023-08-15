from pathlib import Path
from textwrap import dedent

import pytest

from ewatercycle.base.esmvaltool_wrapper import Dataset, Recipe
from ewatercycle.base.forcing_recipe import (
    RecipeBuilder,
    build_generic_distributed_forcing_recipe,
    build_pcrglobwb_recipe,
    recipe_to_string,
)


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
    recipe_as_string = recipe_to_string(recipe)
    print(recipe_as_string)

    expected = dedent(
        """\
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
    recipe_as_string = recipe_to_string(recipe)
    print(recipe_as_string)

    expected = dedent(
        """\
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


def test_build_pcrglobwb_recipe():
    recipe = build_pcrglobwb_recipe(
        start_year=1990,
        end_year=2001,
        shape=Path("myshape.shp"),
        start_year_climatology=1980,
        end_year_climatology=1990,
    )
    recipe_as_string = recipe_to_string(recipe)
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
    extract_shape:
      shapefile: myshape.shp
      crop: true
      decomposed: false
  pr:
    extract_shape:
      shapefile: myshape.shp
      crop: true
      decomposed: false
    convert_units:
      units: kg m-2 d-1
  tas:
    extract_shape:
      shapefile: myshape.shp
      crop: true
      decomposed: false
  pr_climatology:
    extract_shape:
      shapefile: myshape.shp
      crop: true
      decomposed: false
    convert_units:
      units: kg m-2 d-1
    climate_statistics:
      operator: mean
      period: day
  tas_climatology:
    extract_shape:
      shapefile: myshape.shp
      crop: true
      decomposed: false
    climate_statistics:
      operator: mean
      period: day
diagnostics:
  diagnostic:
    scripts:
      script:
        script: hydrology/pcrglobwb.py
        basin: myshape
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


@pytest.skip("Only run when ESMValTool is configured")
def test_run_recipe():
    recipe = build_generic_distributed_forcing_recipe(
        start_year=2000,
        end_year=2001,
        shape=Path("./src/ewatercycle/testing/data/Rhine/Rhine.shp"),
    )
    output = run_recipe(recipe)
    print(output)
