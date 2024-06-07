"""Test search module."""
import gzip
import json
from pathlib import Path
from unittest import mock

import pytest
from esmvalcore.config import CFG
from esmvalcore.dataset import Dataset

from ewatercycle.esmvaltool import search

DATASET_TEMPLATE = {
    "short_name": "pr",
    "activity": "ScenarioMIP",
    "mip": "E1hr",
    "project": "CMIP6",
    "exp": "ssp585",
    "dataset": "CNRM-CM6-1-HR",
    "institute": "CNRM-CERFACS",
    "ensemble": "r1i1p1f2",
    "grid": "gr",
}
CFG["search_esgf"] = "always"

STORED_RESULTS = Path(__file__).parent / "files" / "query_result.txt.gz"


@pytest.fixture(scope="session")
def mock_esgf_query():
    """Mocks the ESGF query to allow for testing without accessing their servers.

    Returns the result of running the following code:

    .. code-block:: python

        from ewatercycle.esmvaltool.search import _query_esgf
        query_result = _query_esgf(
            activity="ScenarioMIP",
            experiment="ssp585",
            variables=["pr", "tas", "rsds"],
        )

    You should be able to recreate this file with:

    .. code-block:: python

        import gzip
        import json
        out = json.dumps([d.facets for d in query_result])
        with gzip.open('query_result.txt.gz', 'wb') as f:
            f.write(out.encode())

    """
    with mock.patch("ewatercycle.esmvaltool.search._query_esgf") as mock_query:
        with gzip.open(STORED_RESULTS, "rb") as f:
            content = json.loads(f.readline())
        result = [Dataset(**entry) for entry in content]
        mock_query.return_value = result
        yield mock_query


def test_esgf_search(mock_esgf_query: mock.MagicMock):
    """Integration test with mocked query."""
    result = search.search_esgf(
        project="CMIP6",
        experiment="ssp585",
        variables=["pr", "tas", "rsds"],
        frequency="day",
    )
    assert "ACCESS-CM2" in result
    assert len(result["ACCESS-CM2"]) == 3  # 3 ensembles for this model
    assert len(result) == 41  # 41 different models

    mock_esgf_query.assert_called_once_with(
        project="CMIP6",
        experiment="ssp585",
        variables=["pr", "tas", "rsds"],
        verbose=False,
    )


def test_cfg_warning(mock_esgf_query: mock.MagicMock):
    """Integration test with mocked query."""
    CFG["search_esgf"] = "when_missing"
    with pytest.warns(UserWarning, match="'search_esgf' is not set to 'always'"):
        search.search_esgf(
            project="CMIP6",
            experiment="ssp585",
            variables=["pr", "tas", "rsds"],
            frequency="day",
        )
    CFG["search_esgf"] = "always"


@pytest.fixture
def mock_different_freqs():
    test_cases = ["day", "CFday", "fx", "E1hr", "E3hr", "AERhr", "E3hrPt", "AERday"]

    result = [Dataset(**DATASET_TEMPLATE) for _ in range(len(test_cases))]
    for test_case, dataset in zip(test_cases, result):
        dataset["mip"] = test_case

    with mock.patch("ewatercycle.esmvaltool.search._query_esgf") as mock_query:
        mock_query.return_value = result
        yield mock_query


@pytest.mark.parametrize(
    "freq, extended, n_results, keys",
    [
        ("day", False, 3, ("day", "CFday", "fx")),
        ("day", True, 4, ("day", "CFday", "fx", "AERday")),
        ("hr", False, 2, ("E1hr", "fx")),
        ("hr", True, 3, ("E1hr", "fx", "AERhr")),
        ("3hr", False, 2, ("E3hr", "fx")),
        ("3hr", True, 3, ("E3hr", "fx", "E3hrPt")),
    ],
)
def test_frequencies(mock_different_freqs, freq, extended, n_results, keys):
    """Tests both the MIP tables and the dataset filtering."""
    datasets = search._query_esgf(
        project="CMIP6",
        experiment="ssp585",
        variables=[
            "pr",
        ],
    )

    mips = search._get_mip_tables(freq=freq, extended=extended)
    datasets = search._filter_datasets(datasets, "mip", mips)

    freqs = [dataset["mip"] for dataset in datasets]

    assert len(freqs) == n_results
    assert all(key in freqs for key in keys)
