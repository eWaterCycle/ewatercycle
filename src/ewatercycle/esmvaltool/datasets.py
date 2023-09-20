"""Forcing datasets."""

from ewatercycle.esmvaltool.schema import Dataset

DATASETS = {
    "ERA5": Dataset(
        dataset="ERA5",
        project="OBS6",
        tier=3,
        type="reanaly",
        version=1,
    ),
    "ERA-Interim": Dataset(
        dataset="ERA-Interim",
        project="OBS6",
        tier=3,
        type="reanaly",
        version=1,
    ),
}
"""Dictionary of predefined forcing datasets.

Where key is the name of the dataset and
value is an `ESMValTool dataset section
<https://docs.esmvaltool.org/projects/ESMValCore/en/latest/recipe/overview.html#datasets>`_.

.. code-block:: python

    >> from ewatercycle.forcing import DATASETS
    >> list(DATASETS.keys())
    ['ERA5', 'ERA-Interim']

"""

# TODO move predefined forcing datasets to ewatercycle.CFG
# would give more work for person setting up ewatercycle environment.
# but would make it easier for users to use the predefined datasets.
# during testing we must overwrite the predefined datasets in CFG
# with the datasets the tests need.
