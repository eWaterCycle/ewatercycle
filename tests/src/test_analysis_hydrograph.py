from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from ewatercycle.analysis.hydrograph import hydrograph


def _create_data():
    """Create sample data for testing."""
    ntime = 3000

    dti = pd.date_range("2018-01-01", periods=ntime, freq="d")

    np.random.seed(20210416)
    t = np.arange(ntime)



    discharge = {
        "discharge_a": pd.Series(np.linspace(0, 2, ntime), index=dti),
        "discharge_b": pd.Series(3 * np.random.random(ntime) ** 2, index=dti),
        "discharge_c": pd.Series(2 * np.random.random(ntime) ** 2, index=dti),
        "reference": pd.Series(np.random.random(ntime) ** 2, index=dti),
    }

    discharge_wave = {
        "discharge_a": pd.Series(
            1 + np.sin(2 * np.pi * (t-60) / 365),  # sinus wave 0-2 centered at 1
            index=dti
        ),
        "discharge_b": pd.Series(
            1.1 + np.sin(2 * np.pi * t /365),  # sinus wave offset ~2 months
            index=dti
        ),
        "discharge_c": pd.Series(
            1 + np.cos(2 * np.pi * t / 365),  # cosine wave
            index=dti
        ),
        "reference": pd.Series(
            1 + np.sin(2 * np.pi * t / 365) + 0.03 * np.random.randn(ntime),  # sinus + noise
            index=dti
        ),
    }

    df_q = pd.DataFrame(discharge)
    df_q_wave = pd.DataFrame(discharge_wave)

    precipitation = {
        "precipitation_a": pd.Series(np.random.random(ntime) / 20, index=dti),
        "precipitation_b": pd.Series(np.random.random(ntime) / 30, index=dti),
    }

    df_pr = pd.DataFrame(precipitation)
    return df_q_wave, df_pr


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

    fig, (ax, ax_tbl) = hydrograph(ds_q, reference="reference", metrics_list = ["kge_2009","nse_mod","male"])

    _save_figure(fig, "hydrograph_xarray.png")

    #
    assert len(ax.lines) == 4  # 3 discharge + 1 reference
    assert ax_tbl.tables

def test_hydrograph_xarray_single_year():
    """Test hydrograph with xarray Dataset input and selecting a single year."""
    df_q, df_pr = _create_data()
    ds_q = xr.Dataset.from_dataframe(df_q)
    ds_pr = xr.Dataset.from_dataframe(df_pr)

    fig, (ax, ax_tbl) = hydrograph(ds_q, reference="reference", selected_year=2020)

    _save_figure(fig, "hydrograph_xarray_single_year.png")

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
