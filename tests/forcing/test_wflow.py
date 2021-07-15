"""Test forcing data for WFLOW."""

import pytest
from esmvalcore.experimental.recipe import Recipe
from esmvalcore.experimental.recipe_output import DataFile

from ewatercycle.forcing import generate, load
from ewatercycle.forcing._wflow import WflowForcing


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    data = {}

    class MockTaskOutput:
        fake_forcing_path = str(tmp_path / 'wflow_forcing.nc')
        data_files = (
            DataFile(fake_forcing_path),
        )

    def mock_run(self):
        """Store recipe for inspection and return dummy output."""
        nonlocal data
        data['data_during_run'] = self.data
        return {'wflow_daily/script': MockTaskOutput()}

    monkeypatch.setattr(Recipe, "run", mock_run)
    return data


class TestGenerateWithExtractRegion:
    @pytest.fixture
    def reference_recipe(self):
        return {
            'diagnostics': {
                'wflow_daily': {
                    'additional_datasets': [{'dataset': 'ERA5',
                                             'project': 'OBS6',
                                             'tier': 3,
                                             'type': 'reanaly',
                                             'version': 1}],
                    'description': 'WFlow input preprocessor for '
                                   'daily data',
                    'scripts': {'script': {'basin': 'Rhine',
                                           'dem_file': 'wflow_parameterset/meuse/staticmaps/wflow_dem.map',
                                           'regrid': 'area_weighted',
                                           'script': 'hydrology/wflow.py'}},
                    'variables': {'orog': {'mip': 'fx',
                                           'preprocessor': 'rough_cutout'},
                                  'pr': {'end_year': 1999,
                                         'mip': 'day',
                                         'preprocessor': 'rough_cutout',
                                         'start_year': 1989},
                                  'psl': {'end_year': 1999,
                                          'mip': 'day',
                                          'preprocessor': 'rough_cutout',
                                          'start_year': 1989},
                                  'rsds': {'end_year': 1999,
                                           'mip': 'day',
                                           'preprocessor': 'rough_cutout',
                                           'start_year': 1989},
                                  'rsdt': {'end_year': 1999,
                                           'mip': 'CFday',
                                           'preprocessor': 'rough_cutout',
                                           'start_year': 1989},
                                  'tas': {'end_year': 1999,
                                          'mip': 'day',
                                          'preprocessor': 'rough_cutout',
                                          'start_year': 1989}}}},
            'documentation': {'authors': ['kalverla_peter',
                                          'camphuijsen_jaro',
                                          'alidoost_sarah',
                                          'aerts_jerom',
                                          'andela_bouwe'],
                              'description': 'Pre-processes climate data for the WFlow hydrological model.\n',
                              'projects': ['ewatercycle'],
                              'references': ['acknow_project']},
            'preprocessors': {'rough_cutout': {'extract_region': {'end_latitude': 2.5,
                                                                  'end_longitude': 16.75,
                                                                  'start_latitude': 7.25,
                                                                  'start_longitude': 10}
                                               }
                              }
        }

    @pytest.fixture
    def forcing(self, mock_recipe_run, sample_shape):
        return generate(
            target_model='wflow',
            dataset='ERA5',
            start_time='1989-01-02T00:00:00Z',
            end_time='1999-01-02T00:00:00Z',
            shape=sample_shape,
            model_specific_options=dict(
                dem_file='wflow_parameterset/meuse/staticmaps/wflow_dem.map',
                extract_region={
                    'start_longitude': 10,
                    'end_longitude': 16.75,
                    'start_latitude': 7.25,
                    'end_latitude': 2.5,
                }
            )
        )

    def test_result(self, forcing, tmp_path, sample_shape):
        expected = WflowForcing(
            directory=str(tmp_path),
            start_time='1989-01-02T00:00:00Z',
            end_time='1999-01-02T00:00:00Z',
            shape = str(sample_shape),
            netcdfinput='wflow_forcing.nc'
        )
        assert forcing == expected

    def test_recipe_configured(self, forcing, mock_recipe_run, reference_recipe):
        assert mock_recipe_run['data_during_run'] == reference_recipe

    def test_saved_yaml(self, forcing, tmp_path):
        saved_forcing = load(tmp_path)
        # shape should is not included in the yaml file
        forcing.shape = None

        assert forcing == saved_forcing
