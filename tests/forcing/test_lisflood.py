import numpy as np
import pandas as pd
import pytest
from esmvalcore.experimental import Recipe
from esmvalcore.experimental.recipe_output import DataFile
import xarray as xr

from ewatercycle.forcing import generate, load
from ewatercycle.forcing._lisflood import LisfloodForcing


def test_plot():
    f = LisfloodForcing(
        directory='.',
        start_time='1989-01-02T00:00:00Z',
        end_time='1999-01-02T00:00:00Z',
    )
    with pytest.raises(NotImplementedError):
        f.plot()


def create_netcdf(var_name, filename):
    var = 15 + 8 * np.random.randn(2, 2, 3)
    lon = [[-99.83, -99.32], [-99.79, -99.23]]
    lat = [[42.25, 42.21], [42.63, 42.59]]
    ds = xr.Dataset({var_name: (["longitude", "latitude", "time"], var)},
                    coords={
                        "lon": (["longitude", "latitude"], lon),
                        "lat": (["longitude", "latitude"], lat),
                        "time": pd.date_range("2014-09-06", periods=3),
                    })
    ds.to_netcdf(filename)
    return DataFile(filename)


@pytest.fixture
def mock_recipe_run(monkeypatch, tmp_path):
    """Overload the `run` method on esmvalcore Recipe's."""
    data = {}
    # TODO add lisvap input files once implemented, see issue #96
    class MockTaskOutput:
        data_files = (
            create_netcdf('pr', tmp_path / 'lisflood_pr.nc'),
            create_netcdf('tas', tmp_path / 'lisflood_tas.nc'),
        )

    def mock_run(self):
        """Store recipe for inspection and return dummy output."""
        nonlocal data
        data['data_during_run'] = self.data
        return {'diagnostic_daily/script': MockTaskOutput()}

    monkeypatch.setattr(Recipe, "run", mock_run)
    return data


class TestGenerateRegionFromShapeFile:
    @pytest.fixture
    def forcing(self, mock_recipe_run, sample_shape):
        return generate(
            target_model='lisflood',
            dataset='ERA5',
            start_time='1989-01-02T00:00:00Z',
            end_time='1999-01-02T00:00:00Z',
            shape=sample_shape,
        )

    @pytest.fixture
    def reference_recipe(self):
        return {
            'datasets': [{
                'dataset': 'ERA5',
                'project': 'OBS6',
                'tier': 3,
                'type': 'reanaly',
                'version': 1
            }],
            'diagnostics': {
                'diagnostic_daily': {
                    'description':
                    'LISFLOOD input '
                    'preprocessor for '
                    'ERA-Interim and ERA5 '
                    'data',
                    'scripts': {
                        'script': {
                            'catchment': 'Rhine',
                            'script': 'hydrology/lisflood.py'
                        }
                    },
                    'variables': {
                        'pr': {
                            'end_year': 1999,
                            'mip': 'day',
                            'preprocessor': 'daily_water',
                            'start_year': 1989
                        },
                        'rsds': {
                            'end_year': 1999,
                            'mip': 'day',
                            'preprocessor': 'daily_radiation',
                            'start_year': 1989
                        },
                        'tas': {
                            'end_year': 1999,
                            'mip': 'day',
                            'preprocessor': 'daily_temperature',
                            'start_year': 1989
                        },
                        'tasmax': {
                            'end_year': 1999,
                            'mip': 'day',
                            'preprocessor': 'daily_temperature',
                            'start_year': 1989
                        },
                        'tasmin': {
                            'end_year': 1999,
                            'mip': 'day',
                            'preprocessor': 'daily_temperature',
                            'start_year': 1989
                        },
                        'tdps': {
                            'end_year': 1999,
                            'mip': 'Eday',
                            'preprocessor': 'daily_temperature',
                            'start_year': 1989
                        },
                        'uas': {
                            'end_year': 1999,
                            'mip': 'day',
                            'preprocessor': 'daily_windspeed',
                            'start_year': 1989
                        },
                        'vas': {
                            'end_year': 1999,
                            'mip': 'day',
                            'preprocessor': 'daily_windspeed',
                            'start_year': 1989
                        }
                    }
                }
            },
            'documentation': {
                'authors':
                ['verhoeven_stefan', 'kalverla_peter', 'andela_bouwe'],
                'projects': ['ewatercycle'],
                'references': ['acknow_project']
            },
            'preprocessors': {
                'daily_radiation': {
                    'convert_units': {
                        'units': 'J m-2 '
                        'day-1'
                    },
                    'custom_order': True,
                    'extract_region': {
                        'end_latitude': 52.2,
                        'end_longitude': 11.9,
                        'start_latitude': 46.3,
                        'start_longitude': 4.1
                    },
                    'extract_shape': {
                        'crop': True,
                        'method': 'contains'
                    },
                    'regrid': {
                        'lat_offset': True,
                        'lon_offset': True,
                        'scheme': 'linear',
                        'target_grid': '0.1x0.1'
                    }
                },
                'daily_temperature': {
                    'convert_units': {
                        'units': 'degC'
                    },
                    'custom_order': True,
                    'extract_region': {
                        'end_latitude': 52.2,
                        'end_longitude': 11.9,
                        'start_latitude': 46.3,
                        'start_longitude': 4.1
                    },
                    'extract_shape': {
                        'crop': True,
                        'method': 'contains'
                    },
                    'regrid': {
                        'lat_offset': True,
                        'lon_offset': True,
                        'scheme': 'linear',
                        'target_grid': '0.1x0.1'
                    }
                },
                'daily_water': {
                    'convert_units': {
                        'units': 'kg m-2 d-1'
                    },
                    'custom_order': True,
                    'extract_region': {
                        'end_latitude': 52.2,
                        'end_longitude': 11.9,
                        'start_latitude': 46.3,
                        'start_longitude': 4.1
                    },
                    'extract_shape': {
                        'crop': True,
                        'method': 'contains'
                    },
                    'regrid': {
                        'lat_offset': True,
                        'lon_offset': True,
                        'scheme': 'linear',
                        'target_grid': '0.1x0.1'
                    }
                },
                'daily_windspeed': {
                    'custom_order': True,
                    'extract_region': {
                        'end_latitude': 52.2,
                        'end_longitude': 11.9,
                        'start_latitude': 46.3,
                        'start_longitude': 4.1
                    },
                    'extract_shape': {
                        'crop': True,
                        'method': 'contains'
                    },
                    'regrid': {
                        'lat_offset': True,
                        'lon_offset': True,
                        'scheme': 'linear',
                        'target_grid': '0.1x0.1'
                    }
                },
                'general': {
                    'custom_order': True,
                    'extract_region': {
                        'end_latitude': 52.2,
                        'end_longitude': 11.9,
                        'start_latitude': 46.3,
                        'start_longitude': 4.1
                    },
                    'extract_shape': {
                        'crop': True,
                        'method': 'contains'
                    },
                    'regrid': {
                        'lat_offset': True,
                        'lon_offset': True,
                        'scheme': 'linear',
                        'target_grid': '0.1x0.1'
                    }
                }
            }
        }

    def test_result(self, forcing, tmp_path, sample_shape):
        expected = LisfloodForcing(directory=str(tmp_path),
                                   start_time='1989-01-02T00:00:00Z',
                                   end_time='1999-01-02T00:00:00Z',
                                   shape=str(sample_shape),
                                   PrefixPrecipitation='lisflood_pr.nc',
                                   PrefixTavg='lisflood_tas.nc')
        assert forcing == expected

    def test_recipe_configured(self, forcing, mock_recipe_run,
                               reference_recipe, sample_shape):
        actual = mock_recipe_run['data_during_run']
        # Remove long description and absolute path so assert is easier
        actual_desc = actual['documentation']['description']
        del actual['documentation']['description']
        actual_shapefile = actual['preprocessors']['general']['extract_shape'][
            'shapefile']
        # Will also del other occurrences of shapefile due to extract shape object being shared between preprocessors
        del actual['preprocessors']['general']['extract_shape']['shapefile']

        assert actual == reference_recipe
        assert actual_shapefile == sample_shape
        assert 'LISFLOOD' in actual_desc

    def test_saved_yaml(self, forcing, tmp_path):
        saved_forcing = load(tmp_path)
        # shape should is not included in the yaml file
        forcing.shape = None

        assert forcing == saved_forcing
