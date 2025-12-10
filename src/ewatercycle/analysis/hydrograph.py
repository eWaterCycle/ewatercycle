"""Analysis methods for eWaterCycle."""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from HydroErr.HydroErr import function_list
from hydrostats import metrics  # noqa: F401
from matplotlib.axes import Axes
from matplotlib.dates import AutoDateLocator, DateFormatter
from matplotlib.figure import Figure

#metrics from https://hydroerr.readthedocs.io/en/stable/list_of_metrics.html callable

metric_map = {func.name: func for func in function_list}       # full names
metric_map.update({func.abbr: func for func in function_list}) # abbreviations
metric_map.update({func.__name__: func for func in function_list}) # attribute names
metric_map.update({k.lower(): v for k, v in metric_map.items()})  # lowercase

def _downsample(df, nrows=100, agg="mean"):
    """Resample dataframe with datetimeindex to a fixed number of rows."""
    if len(df) <= nrows:
        return df, df.index[1] - df.index[0]

    grouper = np.arange(len(df)) // (len(df) / nrows)
    new_df = df.groupby(grouper).agg(agg)
    new_df.index = pd.date_range(df.index[0], df.index[-1], periods=nrows)

    new_period = (df.index[-1] - df.index[0]) / nrows

    return new_df, new_period

def _to_pandas(data_in):
    """Convert input to pandas DataFrame if it is not already.

    Args:
        data_in : supported data types: pd.Dataframe, xr.Dataset

    Returns:
        pd.Dataframe

    Raises:
        Typerror if the input is not supported
    """
    # already a DataFrame
    if isinstance(data_in, pd.DataFrame):
        return data_in

    #Single series
    if isinstance(data_in, pd.Series):
        msg = "A panda series contains only a single timeseries, please provide a pandas DataFrame or xr.Dataset."  # noqa: E501
        raise TypeError(msg)

    # xarray Dataset
    if isinstance(data_in, xr.Dataset):
        return data_in.to_pandas()

    #xarray DataArray
    if isinstance(data_in, xr.DataArray):
        if data_in.ndim == 1:
            msg = "A DataArray with a single timeseries is not supported, please provide a DataFrame or xr.Dataset."  # noqa: E501
            raise TypeError(msg)
        else:  # noqa: RET506
            msg = "DataArray with more than one dimension is not supported, please provide a DataFrame or xr.Dataset."  # noqa: E501
            raise TypeError(msg)

    # unsupported type
    msg = f"Unsupported data type: {type(data_in)}, please provide a DataFrame or xr.Dataset"  # noqa: E501
    raise TypeError(msg)

def _prepare_discharge(discharge, reference: str, selected_year = None):
    """Prepare discharge data for hydrograph."""
    discharge = _to_pandas(discharge)

    # Slice by selected_year if provided
    if selected_year is not None:
        if not isinstance(discharge.index, pd.DatetimeIndex):
            msg = "Discharge index must be a DatetimeIndex to select a year."
            raise ValueError(msg)
        discharge = discharge[discharge.index.year == selected_year]
    y_obs = discharge[reference]
    y_sim = discharge.drop(columns=[reference])
    return y_obs, y_sim

def _prepare_precipitation(precipitation, nbars=None, selected_year = None):
    if precipitation is None:
        return None, None
    precipitation = _to_pandas(precipitation)
    if nbars is not None:
        precipitation, barwidth = _downsample(precipitation, nrows=nbars, agg="mean")
    else:
        barwidth = 0.8  # default value for matplotlib barplot

    if selected_year is not None:
        if not isinstance(precipitation.index, pd.DatetimeIndex):
            msg = "Precipitation index must be a DatetimeIndex to select a year."
            raise ValueError(msg)
        precipitation = precipitation[precipitation.index.year == selected_year]

    return precipitation, barwidth

def _plot_discharge(ax, y_obs, y_sim, **kwargs):
    if hasattr(y_sim, "shape") and y_sim.shape[1] > 1:
        y_obs.plot(ax=ax, linewidth=2.5, zorder=10, **kwargs)
        y_sim.plot(ax=ax, alpha=0.7, linewidth=1.25, **kwargs)
    else:
        y_obs.plot(ax=ax, **kwargs, zorder=10)
        y_sim.plot(ax=ax, **kwargs)
    ax.grid(True)
    return ax

def _plot_precipitation(ax, precipitation, barwidth, precipitation_units):
    ax_pr = ax.twinx()
    ax_pr.invert_yaxis()
    ax_pr.set_ylabel(f"Precipitation ({precipitation_units})")

    for pr_label, pr_timeseries in precipitation.items():
        ax_pr.bar(
            pr_timeseries.index.values,
            pr_timeseries.values,
            width=barwidth,
            alpha=0.4,
            label=pr_label
        )

    # adjust ylim
    ax_pr.set_ylim(ax_pr.get_ylim()[0] * (7/2), 0)
    ax.set_ylim(0, ax.get_ylim()[1] * (7/5))
    return ax_pr

def _calculate_metrics(y_obs, y_sim, metrics_list=None):
    if metrics_list is None:
        metrics_list = ["NSE", "KGE (2009)", "SA", "ME"]

    metrics_objs = []
    for m in metrics_list:
        if isinstance(m, str):
            if m in metric_map:
                metrics_objs.append(metric_map[m])
            elif m.lower() in metric_map:
                metrics_objs.append(metric_map[m.lower()])
            else:
                msg = f"Metric '{m}' not found in hydroerr metrics."
                raise ValueError(msg)
        else:
            metrics_objs.append(m)

    def calc_metric(metric) -> float:
        return y_sim.apply(metric, observed_array=y_obs)

    df_metrics = pd.DataFrame(
        {metric.name: calc_metric(metric) for metric in metrics_objs}
        )
    return df_metrics, metrics_objs

def _create_metrics_table(ax_tbl, df_metrics, metrics_objs):
    col_labels = [f"{metric.name}\n({metric.abbr})" for metric in metrics_objs]
    metrs_rounded = df_metrics.round(2)
    cell_text = [[f"{item:.2f}" for item in row[1]] for row in metrs_rounded.iterrows()]
    table = ax_tbl.table(
        cellText=cell_text,
        rowLabels=metrs_rounded.index,
        colLabels=col_labels,
        loc="center",
        fontsize=15
    )
    ax_tbl.set_axis_off()
    for (i, j), cell in table.get_celld().items():
        if i == 0:                                  #headers
            cell.set_fontsize(12)
            cell.set_text_props(weight="bold")
            cell.set_height(0.15)
        elif j == -1:                               #row labels
            cell.set_fontsize(11)
            cell.set_text_props(weight="bold")
        else:                                       #table values
            cell.set_fontsize(10)
    table.scale(1, 1.5)
    return table

def hydrograph(
    discharge: pd.DataFrame | pd.Series | xr.DataArray | xr.Dataset,
    *,
    reference: str,
    precipitation: pd.DataFrame | pd.Series | xr.DataArray | xr.Dataset | None = None,
    dpi: int | None = None,
    title: str | None = None,
    discharge_units: str = "m$^3$ s$^{-1}$",
    precipitation_units: str = "mm day$^{-1}$",
    figsize: tuple[float, float] = (10, 10),
    filename: os.PathLike | str | None = None,
    nbars: int | None = None,
    metrics_list: list[object] | None = None,
    selected_year: int | None = None,
    **kwargs,
)-> tuple[Figure, tuple[Axes, Axes]]:
    """Plot a hydrograph.

    This utility function makes it convenient to create a hydrograph from
    a set of discharge data from a `pandas.DataFrame` or 'xarray.Dataset'. A column must
     be marked as the reference, so that the agreement metrics can be calculated.

    Optionally, the corresponding precipitation data can be plotted for
    comparison.

    Args:
        discharge: Data containing time series of discharge data to be plotted.
        reference: Name of the reference data, must correspond to a column
            in the discharge dataframe. Metrics are calculated between
            the reference column and each of the other columns.
        precipitation: Optional dataframe containing time series of precipitation data
            to be plotted from the top of the hydrograph.
        dpi: DPI for the plot.
        title: Title of the hydrograph.
        discharge_units: Units for the discharge data.
        precipitation_units: Units for the precipitation data.
        figsize: With, height of the plot in inches.
        filename: If specified, a copy of the plot will be saved to this path.
        nbars: Number of bars to use for downsampling precipitation.
        metrics_list: List of metrics to calculate and display in the table below
            the hydrograph. If not specified, a default set of metrics is used.
        selected_year: Slice a single year from the data
        **kwargs: Options to pass to the matplotlib plotting function

    Returns:
        First tuple member is a matplotlib figure, the second is a tuple of axes.
    """
    y_obs, y_sim = _prepare_discharge(discharge, reference, selected_year)
    precipitation, barwidth = _prepare_precipitation(precipitation, nbars, selected_year)  # noqa: E501

    fig, (ax, ax_tbl) = plt.subplots(nrows=2, ncols=1, dpi=dpi, figsize=figsize,
                                     gridspec_kw={"height_ratios": [3,1]})
    fig.subplots_adjust(bottom=0.05, top=0.95, hspace=0.3)

    ax.set_title(
        title or
        f"$\\mathbf{{Hydrograph\\ with\\ Metrics}}$\nReference: {reference}"
        )

    ax.set_ylabel(f"Discharge ({discharge_units})")

    _plot_discharge(ax, y_obs, y_sim, **kwargs)

    if precipitation is not None:
        ax_pr = _plot_precipitation(ax, precipitation, barwidth, precipitation_units)
        handles, labels = ax_pr.get_legend_handles_labels()
    else:
        handles, labels = ax.get_legend_handles_labels()

    ax.legend(handles, labels, bbox_to_anchor=(1.10,1), loc="upper left")

    locator = AutoDateLocator(minticks=5, maxticks=12)  # adjust min/max ticks
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
    ax.tick_params(axis="x", rotation=30)
    ax.set_xlabel(None)  # no xlabel, ticks make it clear


    df_metrics, metrics_objs = _calculate_metrics(y_obs, y_sim, metrics_list)
    _create_metrics_table(ax_tbl, df_metrics, metrics_objs)

    if filename:
        fig.savefig(filename, bbox_inches="tight", dpi=dpi)

    return fig, (ax, ax_tbl)
