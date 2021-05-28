"""Test forcing data for WFLOW."""
import pytest
from esmvalcore.experimental.recipe import Recipe
from ruamel.yaml import YAML
from esmvalcore.experimental import get_recipe
from ewatercycle.forcing.wflow import WflowForcing
from pathlib import Path
import json
import ewatercycle.forcing
from esmvalcore.experimental.recipe_output import DataFile

# This is what the recipe should look like after we update it
REFERENCE_RECIPE_YAML = """\
# ESMValTool
# recipe_wflow.yml
---
documentation:
  description: |
    Pre-processes climate data for the WFlow hydrological model.

  authors:
    - kalverla_peter
    - camphuijsen_jaro
    - alidoost_sarah
    - aerts_jerom
    - andela_bouwe

  projects:
    - ewatercycle

  references:
    - acknow_project

preprocessors:
  rough_cutout:
    extract_region:
      start_longitude: 10
      end_longitude: 16.75
      start_latitude: 7.25
      end_latitude: 2.5

diagnostics:
  wflow_daily:
    description: WFlow input preprocessor for daily data
    additional_datasets:
      - {dataset: ERA5, project: OBS6, tier: 3, type: reanaly, version: 1}
    variables:
      orog:
        mip: fx
        preprocessor: rough_cutout
      tas: &daily_var
        mip: day
        preprocessor: rough_cutout
        start_year: 1990
        end_year: 2001
      pr: *daily_var
      psl: *daily_var
      rsds: *daily_var
      rsdt:
        <<: *daily_var
        mip: CFday
    scripts:
      script:
        script: hydrology/wflow.py
        basin: Meuse
        dem_file: 'wflow_parameterset/meuse/staticmaps/wflow_dem.map'
        regrid: area_weighted
"""


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    class MockTaskOutput:
        fake_forcing_path = str(tmp_path / 'wflow_forcing.nc')
        data_files = (
            DataFile(fake_forcing_path),
        )


    def mock_run(self):
        """Store recipe for inspection and return dummy output."""
        recipe_path = tmp_path / 'recipe_wflow.yml'
        with open(recipe_path, 'w') as f:
            json.dump(self.data, f)

        return {'wflow_daily/script': MockTaskOutput}

    monkeypatch.setattr(Recipe, "run", mock_run)


def test_fixture(mock_recipe_run):
    """For development purposes only; can be deleted when other tests work."""
    recipe = get_recipe('hydrology/recipe_wflow.yml')
    output = recipe.run()

    forcing_data = output['wflow_daily/script'].data_files[0]
    forcing_file = forcing_data.filename
    directory = str(forcing_file.parent)
    forcing = WflowForcing(directory, '2021', '2022')
    assert isinstance(forcing, WflowForcing)


def test_generate(mock_recipe_run):
    forcing = ewatercycle.forcing.generate(
        target_model = 'wflow',
        dataset = 'ERA5',
        startyear = 1990,
        endyear = 2001,
        dem_file = 'wflow_parameterset/meuse/staticmaps/wflow_dem.map',
        extract_region = {
            'start_longitude': 10,
            'end_longitude': 16.75,
            'start_latitude': 7.25,
            'end_latitude': 2.5,
        }
    )

    assert isinstance(forcing, WflowForcing)

    result_recipe_location = Path(forcing.directory) / 'recipe_wflow.yml'
    result_recipe = json.load(stored_recipe)
    reference_recipe = YAML().load(REFERENCE_RECIPE_YAML)

    # NOT THE SAME YET
    aseert result_recipe == reference_recipe


    # forcing.directory
    # --> check if the forcing object looks okay
    # --> check if the dumped recipe is the same as the reference recipe
    # --> check if there is a ewatercycle-forcing.yaml file
