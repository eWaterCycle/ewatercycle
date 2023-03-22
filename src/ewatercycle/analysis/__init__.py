import os
from typing import Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from hydrostats import metrics
from matplotlib.dates import DateFormatter


def _downsample(df, nrows=100, agg="mean"):
    """Resample dataframe with datetimeindex to a fixed number of rows."""
    if len(df) <= nrows:
        return df, df.index[1] - df.index[0]

    grouper = np.arange(len(df)) // (len(df) / nrows)
    new_df = df.groupby(grouper).agg(agg)
    new_df.index = pd.date_range(df.index[0], df.index[-1], periods=nrows)

    new_period = (df.index[-1] - df.index[0]) / nrows

    return new_df, new_period


def hydrograph(
    discharge: pd.DataFrame,
    *,
    reference: str,
    precipitation: Optional[pd.DataFrame] = None,
    dpi: Optional[int] = None,
    title: str = "Hydrograph",
    discharge_units: str = "m$^3$ s$^{-1}$",
    precipitation_units: str = "mm day$^{-1}$",
    figsize: Tuple[float, float] = (10, 10),
    filename: Optional[Union[os.PathLike, str]] = None,
    nbars: Optional[int] = None,
    **kwargs,
) -> Tuple[plt.Figure, Tuple[plt.Axes, plt.Axes]]:
    """Plot a hydrograph.

    This utility function makes it convenient to create a hydrograph from
    a set of discharge data from a `pandas.DataFrame`. A column must be marked
    as the reference, so that the agreement metrics can be calculated.

    Optionally, the corresponding precipitation data can be plotted for
    comparison.

    Parameters
    ----------
    discharge : pd.DataFrame
        Dataframe containing time series of discharge data to be plotted.
    reference : str
        Name of the reference data, must correspond to a column in the discharge
        dataframe. Metrics are calculated between the reference column and each
        of the other columns.
    precipitation : pd.DataFrame, optional
        Optional dataframe containing time series of precipitation data to be
        plotted from the top of the hydrograph.
    dpi : int, optional
        DPI for the plot.
    title : str, optional
        Title of the hydrograph.
    discharge_units : str, optional
        Units for the discharge data.
    precipitation_units : str, optional
        Units for the precipitation data.
    figsize : (float, float), optional
        With, height of the plot in inches.
    filename : str or Path, optional
        If specified, a copy of the plot will be saved to this path.
    nbars : Int, optional
        Number of bars to use for downsampling precipitation.
    **kwargs:
        Options to pass to the matplotlib plotting function

    Returns
    -------
    fig : `matplotlib.figure.Figure`
    ax, ax_tbl : tuple of `matplotlib.axes.Axes`
    """
    discharge_cols = discharge.columns.drop(reference)
    y_obs = discharge[reference]
    y_sim = discharge[discharge_cols]

    fig, (ax, ax_tbl) = plt.subplots(
        nrows=2,
        ncols=1,
        dpi=dpi,
        figsize=figsize,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    ax.set_title(title)
    ax.set_ylabel(f"Discharge ({discharge_units})")

    y_sim.plot(ax=ax, **kwargs)
    y_obs.plot(ax=ax, **kwargs)

    handles, labels = ax.get_legend_handles_labels()

    # Add precipitation as bar plot to the top if specified
    if precipitation is not None:
        if nbars is not None:
            precipitation, barwidth = _downsample(
                precipitation, nrows=nbars, agg="mean"
            )
        else:
            barwidth = 0.8  # default value for matplotlib barplot

        ax_pr = ax.twinx()
        ax_pr.invert_yaxis()
        ax_pr.set_ylabel(f"Precipitation ({precipitation_units})")

        for pr_label, pr_timeseries in precipitation.items():
            ax_pr.bar(
                pr_timeseries.index.values,
                pr_timeseries.values,
                width=barwidth,
                alpha=0.4,
                label=pr_label,
            )

        # tweak ylim to make space at bottom and top
        ax_pr.set_ylim(ax_pr.get_ylim()[0] * (7 / 2), 0)
        ax.set_ylim(0, ax.get_ylim()[1] * (7 / 5))

        # prepend handles/labels so they appear at the top
        handles_pr, labels_pr = ax_pr.get_legend_handles_labels()
        handles = handles_pr + handles
        labels = labels_pr + labels

    # Put the legend outside the plot
    ax.legend(handles, labels, bbox_to_anchor=(1.10, 1), loc="upper left")

    # set formatting for xticks
    date_fmt = DateFormatter("%Y-%m")
    ax.xaxis.set_major_formatter(date_fmt)
    ax.tick_params(axis="x", rotation=30)

    # calculate metrics for data table underneath plot
    def calc_metric(metric) -> float:
        return y_sim.apply(metric, observed_array=y_obs)

    metrs = pd.DataFrame(
        {
            "nse": calc_metric(metrics.nse),
            "kge_2009": calc_metric(metrics.kge_2009),
            "sa": calc_metric(metrics.sa),
            "me": calc_metric(metrics.me),
        }
    )

    # convert data in dataframe to strings
    cell_text = [[f"{item:.2f}" for item in row[1]] for row in metrs.iterrows()]

    table = ax_tbl.table(
        cellText=cell_text,
        rowLabels=metrs.index,
        colLabels=metrs.columns,
        loc="center",
    )
    ax_tbl.set_axis_off()

    # give more vertical space in cells
    table.scale(1, 1.5)

    if filename is not None:
        fig.savefig(filename, bbox_inches="tight", dpi=dpi)

    return fig, (ax, ax_tbl)
