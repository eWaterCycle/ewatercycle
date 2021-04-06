from esmvalcore.experimental import get_recipe
import deepdiff
import copy
import pytest
from ewatercycle.forcing.preprocessors import update_marrmot, update_lisflood, update_hype, update_wflow, update_pcrglobwb

TEST_INPUT_MARRMOT = (
    {},
    {
        'startyear': 1990,
        'endyear': 2018,
        'dataset': 'ERA-Interim',
        'shapefile': 'Meuse/Meuse.shp',
    },
    {
        'startyear': 1234
    },
    {
        'endyear': 4321
    },
    {
        'dataset': 'ERA5'
    },
    {
        'shapefile': 'Rhine/Rhine.shp'
    },
)

TEST_INPUT_LISFLOOD = (
    {},
    {
        'startyear': 1990,
        'endyear': 1990,
        'dataset': 'ERA-Interim',
        'shapefile': 'Lorentz_Basin_Shapefiles/Meuse/Meuse.shp',
        'extract_region': {
            'start_longitude': 0,
            'end_longitude': 9,
            'start_latitude': 45,
            'end_latitude': 54,
        },
    },
    {
        'startyear': 1234
    },
    {
        'endyear': 4321
    },
    {
        'dataset': 'ERA5'
    },
    {
        'shapefile': 'Rhine/Rhine.shp'
    },
    {
        'extract_region': {
            'start_longitude': 12,
            'end_longitude': 34,
            'start_latitude': 56,
            'end_latitude': 78,
        }
    },
)

TEST_INPUT_HYPE = (
    {},
    {
        'startyear': 1990,
        'endyear': 2001,
        'dataset': 'ERA-Interim',
        'shapefile': 'Meuse_HYPE.shp',
    },
    {
        'startyear': 1234
    },
    {
        'endyear': 4321
    },
    {
        'dataset': 'ERA5'
    },
    {
        'shapefile': 'Rhine_HYPE.shp'
    },
)

TEST_INPUT_WFLOW = (
    {},
    {
        'startyear': 1990,
        'endyear': 2001,
        'dataset': 'ERA-Interim',
        'dem_file': 'wflow_parameterset/meuse/staticmaps/wflow_dem.map',
        'extract_region': {
            'start_longitude': 0,
            'end_longitude': 6.75,
            'start_latitude': 47.25,
            'end_latitude': 52.5,
        },
    },
    {
        'startyear': 1234
    },
    {
        'endyear': 4321
    },
    {
        'dataset': 'ERA5'
    },
    {
        'dem_file': 'wflow/wflow_dem_Rhine.nc'
    },
    {
        'extract_region': {
            'start_longitude': 12,
            'end_longitude': 34,
            'start_latitude': 56,
            'end_latitude': 78,
        }
    },
)

TEST_INPUT_PCRGLOBWB = (
    {},
    {
        'startyear': 2002,
        'endyear': 2016,
        'startyear_climatology': 1990,
        'endyear_climatology': 2002,
        'dataset': 'ERA-Interim',
        'basin': 'rhine',
        'extract_region': {
            'start_longitude': 3,
            'end_longitude': 13.5,
            'start_latitude': 45,
            'end_latitude': 54,
        },
    },
    {
        'startyear': 1234
    },
    {
        'endyear': 4321
    },
    {
        'startyear_climatology': 1234
    },
    {
        'endyear_climatology': 4321
    },
    {
        'dataset': 'ERA5'
    },
    {
        'basin': 'meuse'
    },
    {
        'extract_region': {
            'start_longitude': 12,
            'end_longitude': 34,
            'start_latitude': 56,
            'end_latitude': 78,
        }
    },
)

EXPECTED_DIFF_MARRMOT = (
    {},
    {},
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['variables']['tas']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['pr']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['psl']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['rsds']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['rsdt']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['variables']['tas']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2018
            },
            "root['diagnostics']['diagnostic_daily']['variables']['pr']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2018
            },
            "root['diagnostics']['diagnostic_daily']['variables']['psl']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2018
            },
            "root['diagnostics']['diagnostic_daily']['variables']['rsds']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2018
            },
            "root['diagnostics']['diagnostic_daily']['variables']['rsdt']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2018
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['additional_datasets'][0]['dataset']":
            {
                'new_value': 'ERA5',
                'old_value': 'ERA-Interim'
            }
        },
        'iterable_item_removed': {
            "root['diagnostics']['diagnostic_daily']['additional_datasets'][1]":
            {
                'dataset': 'ERA5',
                'project': 'OBS6',
                'tier': 3,
                'type': 'reanaly',
                'version': 1
            }
        }
    },
    {
        'values_changed': {
            "root['preprocessors']['daily']['extract_shape']['shapefile']": {
                'new_value': 'Rhine/Rhine.shp',
                'old_value': 'Meuse/Meuse.shp'
            },
            "root['diagnostics']['diagnostic_daily']['scripts']['script']['basin']":
            {
                'new_value': 'Rhine',
                'old_value': 'Meuse'
            }
        }
    },
)

EXPECTED_DIFF_LISFLOOD = (
    {},
    {},
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['variables']['pr']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tas']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tasmax']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tasmin']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tdps']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['uas']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['vas']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['rsds']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['variables']['pr']['end_year']":
            {
                'new_value': 4321,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tas']['end_year']":
            {
                'new_value': 4321,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tasmax']['end_year']":
            {
                'new_value': 4321,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tasmin']['end_year']":
            {
                'new_value': 4321,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tdps']['end_year']":
            {
                'new_value': 4321,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['uas']['end_year']":
            {
                'new_value': 4321,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['vas']['end_year']":
            {
                'new_value': 4321,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['rsds']['end_year']":
            {
                'new_value': 4321,
                'old_value': 1990
            }
        }
    },
    {
        'values_changed': {
            "root['datasets'][0]['dataset']": {
                'new_value': 'ERA5',
                'old_value': 'ERA-Interim'
            }
        },
        'iterable_item_removed': {
            "root['datasets'][1]": {
                'dataset': 'ERA5',
                'project': 'OBS6',
                'tier': 3,
                'type': 'reanaly',
                'version': 1
            }
        }
    },
    {
        'values_changed': {
            "root['preprocessors']['general']['extract_shape']['shapefile']": {
                'new_value': 'Rhine/Rhine.shp',
                'old_value': 'Lorentz_Basin_Shapefiles/Meuse/Meuse.shp'
            },
            "root['preprocessors']['daily_water']['extract_shape']['shapefile']":
            {
                'new_value': 'Rhine/Rhine.shp',
                'old_value': 'Lorentz_Basin_Shapefiles/Meuse/Meuse.shp'
            },
            "root['preprocessors']['daily_temperature']['extract_shape']['shapefile']":
            {
                'new_value': 'Rhine/Rhine.shp',
                'old_value': 'Lorentz_Basin_Shapefiles/Meuse/Meuse.shp'
            },
            "root['preprocessors']['daily_radiation']['extract_shape']['shapefile']":
            {
                'new_value': 'Rhine/Rhine.shp',
                'old_value': 'Lorentz_Basin_Shapefiles/Meuse/Meuse.shp'
            },
            "root['preprocessors']['daily_windspeed']['extract_shape']['shapefile']":
            {
                'new_value': 'Rhine/Rhine.shp',
                'old_value': 'Lorentz_Basin_Shapefiles/Meuse/Meuse.shp'
            },
            "root['diagnostics']['diagnostic_daily']['scripts']['script']['catchment']":
            {
                'new_value': 'Rhine',
                'old_value': 'Meuse'
            }
        }
    },
    {
        'values_changed': {
            "root['preprocessors']['general']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 0
            },
            "root['preprocessors']['general']['extract_region']['end_longitude']":
            {
                'new_value': 34,
                'old_value': 9
            },
            "root['preprocessors']['general']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['general']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            },
            "root['preprocessors']['daily_water']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 0
            },
            "root['preprocessors']['daily_water']['extract_region']['end_longitude']":
            {
                'new_value': 34,
                'old_value': 9
            },
            "root['preprocessors']['daily_water']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['daily_water']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            },
            "root['preprocessors']['daily_temperature']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 0
            },
            "root['preprocessors']['daily_temperature']['extract_region']['end_longitude']":
            {
                'new_value': 34,
                'old_value': 9
            },
            "root['preprocessors']['daily_temperature']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['daily_temperature']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            },
            "root['preprocessors']['daily_radiation']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 0
            },
            "root['preprocessors']['daily_radiation']['extract_region']['end_longitude']":
            {
                'new_value': 34,
                'old_value': 9
            },
            "root['preprocessors']['daily_radiation']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['daily_radiation']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            },
            "root['preprocessors']['daily_windspeed']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 0
            },
            "root['preprocessors']['daily_windspeed']['extract_region']['end_longitude']":
            {
                'new_value': 34,
                'old_value': 9
            },
            "root['preprocessors']['daily_windspeed']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['daily_windspeed']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            }
        }
    },
)

EXPECTED_DIFF_HYPE = (
    {},
    {},
    {
        'values_changed': {
            "root['diagnostics']['hype']['variables']['tas']['start_year']": {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['hype']['variables']['tasmin']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['hype']['variables']['tasmax']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['hype']['variables']['pr']['start_year']": {
                'new_value': 1234,
                'old_value': 1990
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['hype']['variables']['tas']['end_year']": {
                'new_value': 4321,
                'old_value': 2001
            },
            "root['diagnostics']['hype']['variables']['tasmin']['end_year']": {
                'new_value': 4321,
                'old_value': 2001
            },
            "root['diagnostics']['hype']['variables']['tasmax']['end_year']": {
                'new_value': 4321,
                'old_value': 2001
            },
            "root['diagnostics']['hype']['variables']['pr']['end_year']": {
                'new_value': 4321,
                'old_value': 2001
            }
        }
    },
    {
        'values_changed': {
            "root['datasets'][0]['dataset']": {
                'new_value': 'ERA5',
                'old_value': 'ERA-Interim'
            }
        },
        'iterable_item_removed': {
            "root['datasets'][1]": {
                'dataset': 'ERA5',
                'project': 'OBS6',
                'tier': 3,
                'type': 'reanaly',
                'version': 1
            }
        }
    },
    {
        'values_changed': {
            "root['preprocessors']['preprocessor']['extract_shape']['shapefile']":
            {
                'new_value': 'Rhine_HYPE.shp',
                'old_value': 'Meuse_HYPE.shp'
            },
            "root['preprocessors']['temperature']['extract_shape']['shapefile']":
            {
                'new_value': 'Rhine_HYPE.shp',
                'old_value': 'Meuse_HYPE.shp'
            },
            "root['preprocessors']['water']['extract_shape']['shapefile']": {
                'new_value': 'Rhine_HYPE.shp',
                'old_value': 'Meuse_HYPE.shp'
            }
        }
    },
)

EXPECTED_DIFF_WFLOW = (
    {},
    {
        'values_changed': {
            "root['diagnostics']['wflow_daily']['scripts']['script']['basin']":
            {
                'new_value': 'wflow_dem',
                'old_value': 'Meuse'
            }
        },
        'iterable_item_removed': {
            "root['diagnostics']['wflow_daily']['additional_datasets'][1]": {
                'dataset': 'ERA5',
                'project': 'OBS6',
                'tier': 3,
                'type': 'reanaly',
                'version': 1
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['wflow_daily']['variables']['tas']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['wflow_daily']['variables']['pr']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['wflow_daily']['variables']['psl']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['wflow_daily']['variables']['rsds']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['wflow_daily']['variables']['rsdt']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['wflow_daily']['variables']['tas']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2001
            },
            "root['diagnostics']['wflow_daily']['variables']['pr']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2001
            },
            "root['diagnostics']['wflow_daily']['variables']['psl']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2001
            },
            "root['diagnostics']['wflow_daily']['variables']['rsds']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2001
            },
            "root['diagnostics']['wflow_daily']['variables']['rsdt']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2001
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['wflow_daily']['additional_datasets'][0]['dataset']":
            {
                'new_value': 'ERA5',
                'old_value': 'ERA-Interim'
            }
        },
        'iterable_item_removed': {
            "root['diagnostics']['wflow_daily']['additional_datasets'][1]": {
                'dataset': 'ERA5',
                'project': 'OBS6',
                'tier': 3,
                'type': 'reanaly',
                'version': 1
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['wflow_daily']['scripts']['script']['basin']":
            {
                'new_value': 'wflow_dem_Rhine',
                'old_value': 'Meuse'
            },
            "root['diagnostics']['wflow_daily']['scripts']['script']['dem_file']":
            {
                'new_value': 'wflow/wflow_dem_Rhine.nc',
                'old_value':
                'wflow_parameterset/meuse/staticmaps/wflow_dem.map'
            }
        }
    },
    {
        'type_changes': {
            "root['preprocessors']['rough_cutout']['extract_region']['end_longitude']":
            {
                'old_type': float,
                'new_type': int,
                'old_value': 6.75,
                'new_value': 34
            },
            "root['preprocessors']['rough_cutout']['extract_region']['start_latitude']":
            {
                'old_type': float,
                'new_type': int,
                'old_value': 47.25,
                'new_value': 56
            },
            "root['preprocessors']['rough_cutout']['extract_region']['end_latitude']":
            {
                'old_type': float,
                'new_type': int,
                'old_value': 52.5,
                'new_value': 78
            }
        },
        'values_changed': {
            "root['preprocessors']['rough_cutout']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 0
            }
        }
    },
)

EXPECTED_DIFF_PCRGLOBWB = (
    {},
    {},
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['variables']['pr']['start_year']":
            {
                'new_value': 1234,
                'old_value': 2002
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tas']['start_year']":
            {
                'new_value': 1234,
                'old_value': 2002
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['variables']['pr']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2016
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tas']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2016
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['variables']['pr_climatology']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tas_climatology']['start_year']":
            {
                'new_value': 1234,
                'old_value': 1990
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['variables']['pr_climatology']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2002
            },
            "root['diagnostics']['diagnostic_daily']['variables']['tas_climatology']['end_year']":
            {
                'new_value': 4321,
                'old_value': 2002
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['additional_datasets'][0]['dataset']":
            {
                'new_value': 'ERA5',
                'old_value': 'ERA-Interim'
            }
        },
        'iterable_item_removed': {
            "root['diagnostics']['diagnostic_daily']['additional_datasets'][1]":
            {
                'dataset': 'ERA5',
                'project': 'OBS6',
                'tier': 3,
                'type': 'reanaly',
                'version': 1
            }
        }
    },
    {
        'values_changed': {
            "root['diagnostics']['diagnostic_daily']['scripts']['script']['basin']":
            {
                'new_value': 'meuse',
                'old_value': 'rhine'
            }
        }
    },
    {
        'type_changes': {
            "root['preprocessors']['crop_basin']['extract_region']['end_longitude']":
            {
                'old_type': float,
                'new_type': int,
                'old_value': 13.5,
                'new_value': 34
            },
            "root['preprocessors']['preproc_pr']['extract_region']['end_longitude']":
            {
                'old_type': float,
                'new_type': int,
                'old_value': 13.5,
                'new_value': 34
            },
            "root['preprocessors']['preproc_tas']['extract_region']['end_longitude']":
            {
                'old_type': float,
                'new_type': int,
                'old_value': 13.5,
                'new_value': 34
            },
            "root['preprocessors']['preproc_pr_clim']['extract_region']['end_longitude']":
            {
                'old_type': float,
                'new_type': int,
                'old_value': 13.5,
                'new_value': 34
            },
            "root['preprocessors']['preproc_tas_clim']['extract_region']['end_longitude']":
            {
                'old_type': float,
                'new_type': int,
                'old_value': 13.5,
                'new_value': 34
            }
        },
        'values_changed': {
            "root['preprocessors']['crop_basin']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 3
            },
            "root['preprocessors']['crop_basin']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['crop_basin']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            },
            "root['preprocessors']['preproc_pr']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 3
            },
            "root['preprocessors']['preproc_pr']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['preproc_pr']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            },
            "root['preprocessors']['preproc_tas']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 3
            },
            "root['preprocessors']['preproc_tas']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['preproc_tas']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            },
            "root['preprocessors']['preproc_pr_clim']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 3
            },
            "root['preprocessors']['preproc_pr_clim']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['preproc_pr_clim']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            },
            "root['preprocessors']['preproc_tas_clim']['extract_region']['start_longitude']":
            {
                'new_value': 12,
                'old_value': 3
            },
            "root['preprocessors']['preproc_tas_clim']['extract_region']['start_latitude']":
            {
                'new_value': 56,
                'old_value': 45
            },
            "root['preprocessors']['preproc_tas_clim']['extract_region']['end_latitude']":
            {
                'new_value': 78,
                'old_value': 54
            }
        }
    },
)

TEST_CASES_MARRMOT = list(zip(TEST_INPUT_MARRMOT, EXPECTED_DIFF_MARRMOT))
TEST_CASES_LISFLOOD = list(zip(TEST_INPUT_LISFLOOD, EXPECTED_DIFF_LISFLOOD))
TEST_CASES_HYPE = list(zip(TEST_INPUT_HYPE, EXPECTED_DIFF_HYPE))
TEST_CASES_WFLOW = list(zip(TEST_INPUT_WFLOW, EXPECTED_DIFF_WFLOW))
TEST_CASES_PCRGLOBWB = list(zip(TEST_INPUT_PCRGLOBWB, EXPECTED_DIFF_PCRGLOBWB))


def _test_forcing(recipe, update_func, params, expected_diff):
    expected_recipe_dict = recipe.data
    recipe_dict = copy.deepcopy(expected_recipe_dict)
    update_func(recipe_dict, **params)
    diff = deepdiff.DeepDiff(expected_recipe_dict, recipe_dict)

    if not diff == expected_diff:
        raise AssertionError(
            f'Expected: {expected_diff}\nActual: {diff.pretty()}')


@pytest.mark.parametrize('params, expected_diff', TEST_CASES_MARRMOT)
def test_forcing_marrmot(params, expected_diff):
    recipe = get_recipe('hydrology/recipe_marrmot.yml')
    update_func = update_marrmot

    _test_forcing(recipe, update_func, params, expected_diff)


@pytest.mark.parametrize('params, expected_diff', TEST_CASES_LISFLOOD)
def test_forcing_lisflood(params, expected_diff):
    recipe = get_recipe('hydrology/recipe_lisflood.yml')
    update_func = update_lisflood

    _test_forcing(recipe, update_func, params, expected_diff)


@pytest.mark.parametrize('params, expected_diff', TEST_CASES_HYPE)
def test_forcing_hype(params, expected_diff):
    recipe = get_recipe('hydrology/recipe_hype.yml')
    update_func = update_hype

    _test_forcing(recipe, update_func, params, expected_diff)


@pytest.mark.parametrize('params, expected_diff', TEST_CASES_WFLOW)
def test_forcing_wflow(params, expected_diff):
    recipe = get_recipe('hydrology/recipe_wflow.yml')
    update_func = update_wflow

    _test_forcing(recipe, update_func, params, expected_diff)


@pytest.mark.parametrize('params, expected_diff', TEST_CASES_PCRGLOBWB)
def test_forcing_pcrglobwb(params, expected_diff):
    recipe = get_recipe('hydrology/recipe_pcrglobwb.yml')
    update_func = update_pcrglobwb

    _test_forcing(recipe, update_func, params, expected_diff)


if __name__ == '__main__':
    model = 'wflow'

    func_list = {
        'marrmot': update_marrmot,
        'lisflood': update_lisflood,
        'hype': update_hype,
        'wflow': update_wflow,
        'pcrglobwb': update_pcrglobwb,
    }

    test_input_list = {
        'marrmot': TEST_INPUT_MARRMOT,
        'lisflood': TEST_INPUT_LISFLOOD,
        'hype': TEST_INPUT_HYPE,
        'wflow': TEST_INPUT_WFLOW,
        'pcrglobwb': TEST_INPUT_PCRGLOBWB,
    }

    recipe = get_recipe(f'hydrology/recipe_{model}.yml')
    update_func = func_list[model]
    params_list = test_input_list[model]

    NEW_TEST_CASES = []

    for params in params_list:
        # generate differences
        expected_data = recipe.data
        data = copy.deepcopy(expected_data)
        update_func(data, **params)
        diff = deepdiff.DeepDiff(recipe.data, data)

        NEW_TEST_CASES.append(diff)

    NEW_TEST_CASES = tuple(NEW_TEST_CASES)
