from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from ewatercycle.analysis.hydrograph import hydrograph, metric_map


def _create_data():
    """Create sample data for testing."""
    ntime = 3000

    dti = pd.date_range("2018-01-01", periods=ntime, freq="d")

    np.random.seed(20210416)
    t = np.arange(ntime)

    discharge_wave = {
        "discharge_a": pd.Series(
            1 + np.sin(2 * np.pi * (t - 60) / 365),  # sinus wave 0-2 centered at 1
            index=dti,
        ),
        "discharge_b": pd.Series(
            1.1 + np.sin(2 * np.pi * t / 365),  # sinus wave offset ~2 months
            index=dti,
        ),
        "discharge_c": pd.Series(
            1 + np.cos(2 * np.pi * t / 365),  # cosine wave
            index=dti,
        ),
        "reference": pd.Series(
            1
            + np.sin(2 * np.pi * t / 365)
            + 0.03 * np.random.randn(ntime),  # sinus + noise
            index=dti,
        ),
    }

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
    fig, (ax, ax_tbl) = hydrograph(
        df_q, reference="reference", precipitation=df_pr, nbars=100
    )

    _save_figure(fig, "hydrograph_DataFrame.png")

    #
    assert len(ax.lines) == 4  # 3 discharge + 1 reference
    assert ax_tbl.tables


def test_hydrograph_xarray():
    """Test hydrograph with xarray Dataset input."""
    df_q = _create_data()[0]
    ds_q = xr.Dataset.from_dataframe(df_q)

    fig, (ax, ax_tbl) = hydrograph(
        ds_q, reference="reference", metrics_list=["kge_2009", "nse_mod", "male"]
    )

    _save_figure(fig, "hydrograph_xarray.png")

    #
    assert len(ax.lines) == 4  # 3 discharge + 1 reference
    assert ax_tbl.tables


def test_hydrograph_xarray_single_year():
    """Test hydrograph with xarray Dataset input and selecting a single year."""
    df_q = _create_data()[0]
    ds_q = xr.Dataset.from_dataframe(df_q)

    fig, (ax, ax_tbl) = hydrograph(ds_q, reference="reference", selected_year=2020)

    _save_figure(fig, "hydrograph_xarray_single_year.png")

    #
    assert len(ax.lines) == 4  # 3 discharge + 1 reference
    assert ax_tbl.tables


def test_hydrograph_xarray_single_hydrograph():
    """Test hydrograph with xarray Dataset input and only one discharge to commpare."""
    df_q = _create_data()[0]
    ds_q = xr.Dataset.from_dataframe(df_q)
    ds_q = ds_q.drop_vars(["discharge_b", "discharge_c"])

    fig, (ax, ax_tbl) = hydrograph(ds_q, reference="reference")

    _save_figure(fig, "hydrograph_xarray_single_comparison.png")

    #
    assert len(ax.lines) == 2  # 3 discharge + 1 reference
    assert ax_tbl.tables


def test_hydrograph_series_error():
    """Test hydrograph raises error with pandas Series input."""
    df_q, df_pr = _create_data()
    ser_q = df_q["discharge_a"]

    try:
        hydrograph(ser_q, reference="discharge_a", precipitation=df_pr, nbars=100)
    except TypeError as e:
        assert (
            str(e)
            == "A panda series contains only a single timeseries, please provide a pandas DataFrame or xr.Dataset."
        )
    else:
        msg = "TypeError not raised"
        raise AssertionError(msg)


def test_hydrograph_dataarray_single_timeseries_error():
    """Test hydrograph raises error with a one dimensional xarray DataArray."""
    df_q = _create_data()[0]
    da_q = xr.DataArray.from_series(df_q["discharge_a"])

    with pytest.raises(TypeError, match="A DataArray with a single timeseries"):
        hydrograph(da_q, reference="discharge_a")


def test_hydrograph_dataarray_multidimensional_error():
    """Test hydrograph raises error with a multi dimensional xarray DataArray."""
    df_q = _create_data()[0]
    da_q = xr.DataArray(df_q, dims=("time", "run"))

    with pytest.raises(TypeError, match="DataArray with more than one dimension"):
        hydrograph(da_q, reference="reference")


def test_hydrograph_unsupported_type_error():
    """Test hydrograph raises error with an unsupported input type."""
    with pytest.raises(TypeError, match="Unsupported data type"):
        hydrograph([1.0, 2.0, 3.0], reference="reference")


def test_hydrograph_selected_year_without_datetimeindex_error():
    """Test selecting a year requires a DatetimeIndex on the discharge."""
    df_q = _create_data()[0].reset_index(drop=True)

    with pytest.raises(ValueError, match="Discharge index must be a DatetimeIndex"):
        hydrograph(df_q, reference="reference", selected_year=2020)


def test_hydrograph_precipitation_selected_year_without_datetimeindex_error():
    """Test selecting a year requires a DatetimeIndex on the precipitation."""
    df_q, df_pr = _create_data()
    df_pr = df_pr.reset_index(drop=True)

    with pytest.raises(ValueError, match="Precipitation index must be a DatetimeIndex"):
        hydrograph(
            df_q, reference="reference", precipitation=df_pr, selected_year=2020
        )


def test_hydrograph_precipitation_selected_year():
    """Test hydrograph slices both discharge and precipitation to a single year."""
    df_q, df_pr = _create_data()

    fig, (ax, ax_tbl) = hydrograph(
        df_q, reference="reference", precipitation=df_pr, selected_year=2020
    )

    ndays_2020 = 366
    assert len(ax.lines) == 4  # 3 discharge + 1 reference
    assert len(ax.lines[0].get_xdata()) == ndays_2020
    assert ax_tbl.tables
    plt.close(fig)


def test_hydrograph_nbars_larger_than_data():
    """Test precipitation is not downsampled when nbars exceeds the number of rows."""
    df_q, df_pr = _create_data()

    fig, (ax, ax_tbl) = hydrograph(
        df_q, reference="reference", precipitation=df_pr, nbars=len(df_pr) + 1
    )

    # both precipitation series are plotted with all their original values
    ax_pr = [child for child in fig.axes if child not in (ax, ax_tbl)][0]
    assert len(ax_pr.containers) == 2
    assert len(ax_pr.containers[0]) == len(df_pr)
    plt.close(fig)


def test_hydrograph_metric_name_other_case():
    """Test metric names are looked up case insensitively."""
    df_q = _create_data()[0]

    fig, (_, ax_tbl) = hydrograph(df_q, reference="reference", metrics_list=["Nse"])

    assert len(ax_tbl.tables[0].get_celld()) > 0
    plt.close(fig)


def test_hydrograph_metric_as_object():
    """Test a metric can be passed as a callable instead of a name."""
    df_q = _create_data()[0]

    fig, (_, ax_tbl) = hydrograph(
        df_q, reference="reference", metrics_list=[metric_map["nse"]]
    )

    assert len(ax_tbl.tables[0].get_celld()) > 0
    plt.close(fig)


def test_hydrograph_unknown_metric_error():
    """Test hydrograph raises error for an unknown metric name."""
    df_q = _create_data()[0]

    with pytest.raises(ValueError, match="Metric 'not_a_metric' not found"):
        hydrograph(df_q, reference="reference", metrics_list=["not_a_metric"])


def test_hydrograph_saves_file(tmp_path):
    """Test hydrograph writes a copy of the figure to the given filename."""
    df_q = _create_data()[0]
    filename = tmp_path / "hydrograph.png"

    fig, _ = hydrograph(df_q, reference="reference", filename=filename)

    assert filename.exists()
    assert filename.stat().st_size > 0
    plt.close(fig)
