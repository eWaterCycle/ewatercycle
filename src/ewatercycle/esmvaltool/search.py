"""Search ESGF for datasets with ESMValTool."""
import warnings
from itertools import compress
from typing import Literal

from esmvalcore.config import CFG
from esmvalcore.dataset import Dataset


def search_esgf(
    activity: str,
    experiment: str,
    frequency: Literal["hr", "3hr", "day"],
    variables: list[str],
    extended_mip_tables: bool = False,
    verbose: bool = False,
) -> dict[str, set[str]]:
    """Search through ESGF for datasets fitting your requirements.

    Examples:

    To find all model ensembles which have the "pr", "tas", "rsdt" and "orog" variables
    (the ones required for wflow), for the ssp585 scenario.

    .. code-block:: python
        from ewatercycle.esmvaltool.search import search esgf

        search_esgf(
            activity="ScenarioMIP",
            experiment="ssp585",
            frequency="day",
            variables=["pr", "tas", "rsdt", "orog"],
        )

    Gives something like:

    .. code-block:: python
        {
            'MPI-ESM1-2-HR': {'r1i1p1f1', 'r2i1p1f1'},
            'MPI-ESM1-2-LR': {'r10i1p1f1', 'r11i1p1f1', ...  'r9i1p1f1'},
            'INM-CM4-8': {'r1i1p1f1'},
            'MRI-ESM2-0': {'r1i1p1f1', 'r2i1p1f1', 'r3i1p1f1', 'r4i1p1f1', 'r5i1p1f1'},
            'IPSL-CM6A-LR': {'r1i1p1f1'},
            'GFDL-CM4': {'r1i1p1f1'},
        }

    Args:
        activity: Activity type, for example: 'ScenarioMIP'.
        experiment: Experiment within the activity. E.g.: 'ssp585'
        frequency: Which frequency of data are you interested in. Valid inputs are 'hr',
            '3hr', and 'day.
        variables: Which variables are you searching for. Use the short_name definition.
            For example: ['pr', 'tas'].
        extended_mip_tables (optional): If you want to use extended MIP tables.
            These tables are probably not relevant for most hydrology usecases and can
            make the search slower. Defaults to False.
        verbose (optional): If the results should be printed in a verbose way, to aid
            in your search experience. Defaults to False.

    Returns:
        A dictionary with the dataset name as key, and the valid ensemble member names
            in a set as items.
    """
    if CFG["search_esgf"] != "always":
        msg = (
            "The ESMValTool configuration option 'search_esgf' is not set to 'always'\n"
            "this can lead to retrieving only subsets of the data you are interested "
            "in.\n"
            "To set the configuration to always search on ESGF, do:\n"
            "    from esmvalcore.config import CFG\n"
            "    CFG['search_esgf'] = 'always'\n"
        )
        warnings.warn(msg, category=UserWarning)

    datasets = _query_esgf(
        activity=activity, experiment=experiment, variables=variables, verbose=verbose
    )

    mips = _get_mip_tables(freq=frequency, extended=extended_mip_tables)
    datasets = _filter_datasets(datasets, "mip", mips)

    dataset_names = set([dataset["dataset"] for dataset in datasets])
    unique_ensemble_members = set([dataset["ensemble"] for dataset in datasets])

    valid_datasets: list[Dataset] = []
    # Iterate through every dataset (i.e. model)
    for dataset_name in dataset_names:
        selected_dataset = _filter_datasets(datasets, "dataset", str(dataset_name))
        # Iterate through every ensemble of this dataset
        for ensemble in unique_ensemble_members:
            selected_ensemble = _filter_datasets(
                selected_dataset, "ensemble", str(ensemble)
            )
            output_short_names = _get_value(selected_ensemble, "short_name")

            # Check if this model ensemble has all required variables
            if all([var in output_short_names for var in variables]):
                valid_datasets.extend(selected_ensemble)

    valid_dataset_names = _get_value(valid_datasets, "dataset")
    valid_ensembles: dict[str, set[str]] = dict()
    for name in valid_dataset_names:
        ensembles = _get_value(
            _filter_datasets(valid_datasets, "dataset", str(name)),
            "ensemble",
        )
        valid_ensembles[str(name)] = set(str(ens) for ens in ensembles)
    return valid_ensembles


def _query_esgf(
    activity: str,
    experiment: str,
    variables: list[str],
    verbose: bool = False,
) -> list[Dataset]:
    """Return all datasets on ESGF that match the specified search query.

    Args:
        activity: Activity type, for example: 'ScenarioMIP'.
        experiment: Experiment within the activity. E.g.: 'ssp585'
        variables: Which variables are you searching for. Use the short_name definition.
            For example: ['pr', 'tas'].
        verbose (optional): If the results should be printed in a verbose way, to aid
            in your search experience. Defaults to False.

    Returns:
        List of ESMValTool 'Dataset' objects that match the search query.
    """
    datasets = list()

    for var in variables:
        dataset_query = Dataset(
            short_name=var,
            activity=activity,
            mip="*",
            project="CMIP6",
            exp=experiment,
            dataset="*",
            institute="*",
            ensemble="*",
            grid="*",
        )
        datasets_var = list(dataset_query.from_files())

        if len(datasets_var) > 0 and verbose:
            print(f"Found {len(datasets_var)} results for short name: {var}")
            print("\n showing the first one.")
            print(datasets_var[0])

        datasets.extend(datasets_var)

    return datasets


def _get_mip_tables(
    freq: Literal["hr", "3hr", "day"],
    extended: bool = False,
) -> tuple[str, ...]:
    """Return the MIP tables that fit a certain desired data frequency.

    Args:
        freq: Desired frequency. 'hr', '3hr' or 'day'.
        extended_mip_tables (optional): If you want to use extended MIP tables.
            These tables are probably not relevant for most hydrology usecases and can
            make the search slower. Defaults to False.

    Returns:
        The names of the MIP tables that match the desired frequency.
    """
    always_include: tuple[str, ...] = ("fx",)  # So orog is compatible with any freq.
    mip_tables = {
        "hr": ("E1hr",),
        "3hr": ("3hr", "CF3hr", "E3hr"),
        "day": ("day", "Eday", "CFday"),
    }

    extended_mip_tables = {
        "hr": ("AERhr",),
        "3hr": ("E3hrPt",),
        "day": ("AERday", "Oday", "SIday"),
    }
    if freq not in mip_tables:
        msg = (
            f"Frequency '{freq}' is not implemented or not a valid mip table frequency"
        )
        raise ValueError(msg)

    if extended:
        return mip_tables[freq] + always_include + extended_mip_tables[freq]  # type: ignore
    return mip_tables[freq] + always_include  # type: ignore


def _filter_datasets(
    datasets: list[Dataset],
    key: str,
    value: str | list[str] | tuple[str, ...],
) -> list[Dataset]:
    """Return only the datasets with certain values for a certain facet."""
    if isinstance(value, str):
        value = [value]
    valid_datasets = [dataset[key] in value for dataset in datasets]
    return list(compress(datasets, valid_datasets))


def _get_value(datasets: list[Dataset], key: str):
    """Return the values belonging to a certain facet from multiple datasets."""
    return [dataset[key] for dataset in datasets]
