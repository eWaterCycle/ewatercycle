from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from ewatercycle.analysis import hydrograph


def _create_data():
    """Create sample data for testing."""
    ntime = 3000

    dti = pd.date_range("2018-01-01", periods=ntime, freq="d")

    np.random.seed(20210416)

    discharge = {
        "discharge_a": pd.Series(np.linspace(0, 2, ntime), index=dti),
        "discharge_b": pd.Series(3 * np.random.random(ntime) ** 2, index=dti),
        "discharge_c": pd.Series(2 * np.random.random(ntime) ** 2, index=dti),
        "reference": pd.Series(np.random.random(ntime) ** 2, index=dti),
    }

    df_q = pd.DataFrame(discharge)

    precipitation = {
        "precipitation_a": pd.Series(np.random.random(ntime) / 20, index=dti),
        "precipitation_b": pd.Series(np.random.random(ntime) / 30, index=dti),
    }

    df_pr = pd.DataFrame(precipitation)
    return df_q, df_pr


def _save_figure(fig, fname):
    """Save figure to baseline directory."""
    baseline_dir = "tests/src/baseline_images/test_analysis"
    fig_path = Path(baseline_dir) / fname
    fig.savefig(fig_path, bbox_inches="tight")

def test_hydrograph():
    """Test hydrograph with pandas DataFrame input."""
    df_q, df_pr = _create_data()
    fig, (ax, ax_tbl) = hydrograph(df_q, reference="reference", precipitation=df_pr, nbars=100)

    _save_figure(fig, "hydrograph_DataFrame.png")

    #
    assert len(ax.lines) == 4  # 3 discharge + 1 reference
    assert ax_tbl.tables

def test_hydrograph_xarray():
    """Test hydrograph with xarray Dataset input."""
    df_q, df_pr = _create_data()
    ds_q = xr.Dataset.from_dataframe(df_q)
    ds_pr = xr.Dataset.from_dataframe(df_pr)

    fig, (ax, ax_tbl) = hydrograph(ds_q, reference="reference", precipitation=ds_pr, nbars=100)

    _save_figure(fig, "hydrograph_xarray.png")

    #
    assert len(ax.lines) == 4  # 3 discharge + 1 reference
    assert ax_tbl.tables

def test_hydrograph_series_error():
    """Test hydrograph raises error with pandas Series input."""
    df_q, df_pr = _create_data()
    ser_q = df_q["discharge_a"]

    try:
        hydrograph(ser_q, reference="discharge_a", precipitation=df_pr, nbars=100)
    except TypeError as e:
        assert str(e) == "A panda series contains only a single timeseries, please provide a pandas DataFrame or xr.Dataset."
    else:
        msg = "TypeError not raised"
        raise AssertionError(msg)
