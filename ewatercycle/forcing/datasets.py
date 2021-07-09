"""Supported datasets for ESMValTool recipes.

Currently supported: ERA5 and ERA-Interim.
"""

DATASETS = {
    'ERA5': {
        'dataset': 'ERA5',
        'project': 'OBS6',
        'tier': 3,
        'type': 'reanaly',
        'version': 1
    },
    'ERA-Interim': {
        'dataset': 'ERA-Interim',
        'project': 'OBS6',
        'tier': 3,
        'type': 'reanaly',
        'version': 1
    },
}
